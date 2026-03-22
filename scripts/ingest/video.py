"""
ingest/video.py
Handler vidéo local : fichier MP4 → extraction audio → transcript → drop-off.
Pipeline : video → ffmpeg (audio) → Whisper (transcript) → raw-sources/

Dépendance : ffmpeg doit être installé et accessible dans le PATH.
"""
import sys
import subprocess
import tempfile
from pathlib import Path

from scripts.ingest._core import make_drop_off, set_status
from scripts.ingest._core import STATUS_READY, STATUS_FAILED
from scripts.ingest.audio import transcribe_with_checkpoint


def extract_audio(video_path: Path, output_path: Path):
    """Extrait l'audio d'un fichier vidéo en WAV mono 16kHz via ffmpeg."""
    result = subprocess.run(
        [
            "ffmpeg", "-i", str(video_path),
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(output_path), "-y", "-loglevel", "error",
        ],
        capture_output=True,
        text=True,
        timeout=3600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg échoué :\n{result.stderr.strip()}")


def process(video_path: Path, title: str = None, lang: str = "fr", fast: bool = False):
    """Point d'entrée principal. Appelé par capture.py."""
    if not video_path.exists():
        sys.exit(f"Fichier introuvable : {video_path}")

    display_title = title or video_path.stem

    folder = make_drop_off(
        display_title,
        "video",
        extra_fields={
            "chemin_original": str(video_path),
            "fichier_video": video_path.name,
        },
    )

    checkpoint = folder / "transcript.tmp"
    transcript_path = folder / "transcript.txt"

    try:
        with tempfile.TemporaryDirectory() as tmp:
            audio_path = Path(tmp) / "audio.wav"
            print(f"Extraction audio ({video_path.name})...")
            extract_audio(video_path, audio_path)
            text = transcribe_with_checkpoint(audio_path, lang, fast, checkpoint)

        transcript_path.write_text(text, encoding="utf-8")
        if checkpoint.exists():
            checkpoint.unlink()
        set_status(folder, STATUS_READY)
        print(f"Drop-off créé : sources/raw-sources/{folder.name}/")
        print(f"  - transcript.txt ({len(text)} caractères)")
        print(f"  - chemin_original : {video_path} (non copié dans le vault)")
    except Exception as e:
        set_status(folder, STATUS_FAILED)
        print(f"Erreur : {e}")
        if checkpoint.exists():
            print("  transcript.tmp conservé pour reprise manuelle")
        raise
