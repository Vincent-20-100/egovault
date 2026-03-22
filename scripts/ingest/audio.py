"""
ingest/audio.py
Handler audio local : fichier → drop-off dans sources/raw-sources/.

Deux différences clés vs l'ancien transcribe_audio.py :
1. Ne copie JAMAIS le fichier audio dans le vault (réf. chemin original dans source.md)
2. Checkpointing : écrit transcript.tmp au fil de l'eau → renommé en transcript.txt à la fin.
   Si interruption, transcript.tmp contient ce qui a déjà été transcrit.
"""
import sys
from pathlib import Path
from datetime import datetime

from scripts.ingest._core import slug, make_drop_off, set_status
from scripts.ingest._core import STATUS_READY, STATUS_FAILED

PROFILES = {
    "default": {"model_size": "medium", "beam_size": 5, "cpu_threads": 4},
    "fast":    {"model_size": "small",  "beam_size": 1, "cpu_threads": 8},
}


def transcribe_with_checkpoint(audio_path: Path, lang: str, fast: bool,
                                checkpoint: Path) -> str:
    """
    Transcrit avec faster-whisper et écrit dans checkpoint au fil de l'eau.
    En cas d'interruption, checkpoint contient les segments déjà produits.
    Retourne le texte complet à la fin.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper requis : pip install faster-whisper")

    profile = PROFILES["fast"] if fast else PROFILES["default"]
    print(f"Transcription ({audio_path.name}) "
          f"[model={profile['model_size']}, beam_size={profile['beam_size']}]...")

    model = WhisperModel(
        profile["model_size"],
        device="cpu",
        compute_type="int8",
        cpu_threads=profile["cpu_threads"],
    )
    segments, _ = model.transcribe(
        str(audio_path), language=lang, beam_size=profile["beam_size"]
    )

    parts = []
    with open(checkpoint, "w", encoding="utf-8") as f:
        for seg in segments:
            text = seg.text.strip()
            parts.append(text)
            f.write(text + " ")
            f.flush()

    return " ".join(parts)


def process(audio_path: Path, title: str | None = None, lang: str = "fr",
            fast: bool = False) -> None:
    """Point d'entrée principal. Appelé par capture.py."""
    if not audio_path.exists():
        sys.exit(f"Fichier introuvable : {audio_path}")

    display_title = title or audio_path.stem

    folder = make_drop_off(
        display_title,
        "audio",
        extra_fields={
            "chemin_original": str(audio_path),
            "fichier_audio": audio_path.name,
        }
    )

    checkpoint = folder / "transcript.tmp"
    transcript_path = folder / "transcript.txt"

    try:
        text = transcribe_with_checkpoint(audio_path, lang, fast, checkpoint)
        transcript_path.write_text(text, encoding="utf-8")
        if checkpoint.exists():
            checkpoint.unlink()
        set_status(folder, STATUS_READY)
        print(f"Drop-off créé : sources/raw-sources/{folder.name}/")
        print(f"  - transcript.txt ({len(text)} caractères)")
        print(f"  - chemin_original : {audio_path} (non copié dans le vault)")
    except Exception as e:
        set_status(folder, STATUS_FAILED)
        print(f"Erreur : {e}", file=sys.stderr)
        if checkpoint.exists():
            print("  transcript.tmp conservé pour reprise manuelle")
        raise
