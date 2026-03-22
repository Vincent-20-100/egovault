"""
capture.py
Point d'entrée unique pour l'ingestion de sources dans le vault.

Usage direct :
  .venv/Scripts/python capture.py "https://youtube.com/watch?v=..."
  .venv/Scripts/python capture.py video.mp4 [--title "Titre"] [--lang fr] [--fast]
  .venv/Scripts/python capture.py audio.mp3 [--title "Titre"] [--lang fr] [--fast]

Queue d'ingestion :
  .venv/Scripts/python capture.py queue add "https://youtube.com/..."
  .venv/Scripts/python capture.py queue add video.mp4 --title "Titre"
  .venv/Scripts/python capture.py queue run [--lang fr] [--fast]
  .venv/Scripts/python capture.py queue status
  .venv/Scripts/python capture.py queue clear-done
"""
import sys
import argparse
from pathlib import Path

from scripts.ingest._core import YOUTUBE_PATTERN, AUDIO_EXTENSIONS, VIDEO_EXTENSIONS


def detect_type(source: str) -> str:
    """Détecte le type de source depuis l'URL ou l'extension du fichier."""
    if YOUTUBE_PATTERN.search(source):
        return "youtube"
    suffix = Path(source).suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix == ".pdf":
        return "pdf"
    return "unknown"


def main():
    # Sous-commande queue — dispatch avant argparse classique
    if len(sys.argv) > 1 and sys.argv[1] == "queue":
        from scripts.queue import handle_queue_command
        handle_queue_command(sys.argv[2:])
        return

    parser = argparse.ArgumentParser(
        description="Capturer une source dans le vault PKM."
    )
    parser.add_argument("source", help="URL YouTube ou chemin vers fichier vidéo/audio/PDF")
    parser.add_argument("--title", default=None, help="Titre (vidéo/audio uniquement)")
    parser.add_argument("--lang", default="fr", help="Langue Whisper (défaut: fr)")
    parser.add_argument("--fast", action="store_true",
                        help="Mode rapide Whisper : model=small, beam_size=1 (~6-8x plus vite)")
    args = parser.parse_args()

    source_type = detect_type(args.source)

    if source_type == "youtube":
        from scripts.ingest.youtube import process
        process(args.source)

    elif source_type == "video":
        from scripts.ingest.video import process
        process(Path(args.source), title=args.title, lang=args.lang, fast=args.fast)

    elif source_type == "audio":
        from scripts.ingest.audio import process
        process(Path(args.source), title=args.title, lang=args.lang, fast=args.fast)

    elif source_type == "pdf":
        sys.exit(
            "PDF : handler non encore implémenté.\n"
            "Déposez manuellement dans sources/raw-sources/YYYY-MM-DD-titre/ avec un source.md."
        )

    else:
        sys.exit(
            f"Type de source non reconnu : {args.source}\n"
            f"Supportés : URL YouTube, vidéo {sorted(VIDEO_EXTENSIONS)}, "
            f"audio {sorted(AUDIO_EXTENSIONS)}"
        )


if __name__ == "__main__":
    main()
