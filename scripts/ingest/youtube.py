"""
ingest/youtube.py
Handler YouTube : URL → drop-off dans sources/raw-sources/.
Utilise youtube-transcript-api (rapide). Fallback Whisper si pas de sous-titres.
"""
import re
import sys
import glob as glob_module
import tempfile
import os
from pathlib import Path

from scripts.ingest._core import make_drop_off, set_status, find_duplicate
from scripts.ingest._core import STATUS_READY, STATUS_FAILED


def extract_video_id(url: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    if not match:
        raise ValueError(f"ID vidéo introuvable dans : {url}")
    return match.group(1)


def get_metadata(video_id: str) -> dict:
    """Retourne les métadonnées de la vidéo via yt_dlp."""
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )
            raw_desc = info.get("description") or ""
            description = " ".join(raw_desc.splitlines())[:400].strip()
            return {
                "title": info.get("title", video_id),
                "chaine": info.get("channel") or info.get("uploader", ""),
                "description": description,
                "duree": info.get("duration", 0),
            }
    except Exception as e:
        print(f"Avertissement : métadonnées indisponibles pour {video_id} ({e})")
        return {"title": video_id, "chaine": "", "description": "", "duree": 0}


def fetch_via_api(video_id: str) -> str:
    """Retourne le texte du transcript. Lève une exception si indisponible."""
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id, languages=["fr", "en", "fr-FR", "en-US"])
    return " ".join(entry.text for entry in transcript)


def fetch_via_whisper(video_id: str) -> str:
    """Fallback Whisper : télécharge l'audio et transcrit."""
    import yt_dlp
    from faster_whisper import WhisperModel

    with tempfile.TemporaryDirectory() as tmp:
        audio_base = os.path.join(tmp, "audio")
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
            "outtmpl": audio_base,
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

        matches = glob_module.glob(f"{audio_base}.*")
        if not matches:
            raise FileNotFoundError("Fichier audio introuvable après téléchargement")
        audio_path = matches[0]

        print(f"Transcription Whisper ({os.path.basename(audio_path)})...")
        model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=8)
        segments, _ = model.transcribe(audio_path, language="fr", beam_size=1)
        return " ".join(seg.text.strip() for seg in segments)


def process(url: str):
    """Point d'entrée principal. Appelé par capture.py."""
    video_id = extract_video_id(url)

    existing = find_duplicate(url)
    if existing:
        print(f"Doublon détecté : {existing.name} — annulé.")
        return

    meta = get_metadata(video_id)
    title = meta["title"]

    print("Tentative via youtube-transcript-api...")
    try:
        text = fetch_via_api(video_id)
        via = "youtube-transcript-api"
    except Exception as e:
        print(f"Pas de sous-titres ({e}). Fallback Whisper...")
        text = fetch_via_whisper(video_id)
        via = "faster-whisper"

    extra = {
        "chaine": meta["chaine"],
        "description": meta["description"],
        "duree": meta["duree"],
        "via": via,
    }
    folder = make_drop_off(title, "video", url=url, extra_fields=extra)
    try:
        (folder / "transcript.txt").write_text(text, encoding="utf-8")
        set_status(folder, STATUS_READY)
        print(f"Drop-off créé : sources/raw-sources/{folder.name}/")
        print(f"  - transcript.txt ({len(text)} caractères, via {via})")
    except Exception as e:
        set_status(folder, STATUS_FAILED)
        raise
