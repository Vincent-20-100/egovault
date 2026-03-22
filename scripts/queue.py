"""
scripts/queue.py
Gestion de la queue d'ingestion.

Accumule des sources à traiter puis les ingère séquentiellement.
Le fichier queue.yaml est stocké dans {data_path}/sources/queue.yaml.

Usage via capture.py :
  capture.py queue add "https://youtube.com/..."
  capture.py queue add fichier.mp4 --title "Mon titre" --lang fr
  capture.py queue run [--lang fr] [--fast]
  capture.py queue status
  capture.py queue clear-done
"""
import sys
import argparse
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML requis : pip install pyyaml")

from scripts._config import get_sources_path
from scripts.ingest._core import YOUTUBE_PATTERN, AUDIO_EXTENSIONS, VIDEO_EXTENSIONS


def _detect_type(source: str) -> str:
    if YOUTUBE_PATTERN.search(source):
        return "youtube"
    suffix = Path(source).suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    return "unknown"


def _queue_path() -> Path:
    return get_sources_path() / "queue.yaml"


def _load() -> dict:
    p = _queue_path()
    if not p.exists():
        return {"pending": [], "done": [], "failed": []}
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {"pending": [], "done": [], "failed": []}


def _save(data: dict):
    p = _queue_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def cmd_add(args):
    source_type = _detect_type(args.source)
    if source_type == "unknown":
        sys.exit(
            f"Type non reconnu : {args.source}\n"
            f"Supportés : URL YouTube, audio {sorted(AUDIO_EXTENSIONS)}, "
            f"vidéo {sorted(VIDEO_EXTENSIONS)}"
        )

    data = _load()
    entry = {
        "type": source_type,
        "source": args.source,
        "added": datetime.now().strftime("%Y-%m-%d"),
    }
    if args.title:
        entry["title"] = args.title
    if args.lang != "fr":
        entry["lang"] = args.lang
    if args.fast:
        entry["fast"] = True

    data["pending"].append(entry)
    _save(data)
    print(f"Ajouté à la queue [{source_type}] : {args.source}")
    print(f"  {len(data['pending'])} source(s) en attente")


def cmd_run(args):
    data = _load()
    pending = data.get("pending", [])

    if not pending:
        print("Queue vide — rien à traiter.")
        return

    print(f"{len(pending)} source(s) à traiter...\n")
    ok, fail = 0, 0

    for entry in pending:
        source = entry["source"]
        source_type = entry["type"]
        lang = entry.get("lang", args.lang)
        fast = entry.get("fast", args.fast)
        print(f"--- [{source_type}] {source[:80]} ---")

        try:
            if source_type == "youtube":
                from scripts.ingest.youtube import process
                process(source)
            elif source_type == "audio":
                from scripts.ingest.audio import process
                process(Path(source), title=entry.get("title"), lang=lang, fast=fast)
            elif source_type == "video":
                from scripts.ingest.video import process
                process(Path(source), title=entry.get("title"), lang=lang, fast=fast)

            data["done"].append({**entry, "ingested": datetime.now().strftime("%Y-%m-%d")})
            ok += 1

        except Exception as e:
            print(f"  Erreur : {e}")
            data["failed"].append({**entry, "error": str(e)})
            fail += 1

        print()

    data["pending"] = []
    _save(data)
    print(f"Terminé : {ok} ok, {fail} échouée(s).")
    if fail:
        print("  Voir 'capture.py queue status' pour les erreurs.")


def cmd_status(_args):
    data = _load()
    pending = data.get("pending", [])
    done = data.get("done", [])
    failed = data.get("failed", [])

    print(f"Queue : {_queue_path()}\n")
    print(f"En attente ({len(pending)}) :")
    for e in pending:
        title = e.get("title", "")
        suffix = f' — "{title}"' if title else ""
        print(f"  [{e['type']}] {e['source'][:70]}{suffix}")

    if failed:
        print(f"\nÉchouées ({len(failed)}) :")
        for e in failed:
            print(f"  [{e['type']}] {e['source'][:60]} → {e.get('error', '?')[:50]}")

    print(f"\nTraitées : {len(done)}")


def cmd_clear_done(_args):
    data = _load()
    n = len(data.get("done", []))
    data["done"] = []
    _save(data)
    print(f"{n} entrée(s) 'done' supprimées.")


def handle_queue_command(argv: list[str]):
    parser = argparse.ArgumentParser(prog="capture.py queue")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Ajouter une source à la queue")
    p_add.add_argument("source", help="URL YouTube ou chemin fichier")
    p_add.add_argument("--title", default=None, help="Titre (optionnel)")
    p_add.add_argument("--lang", default="fr", help="Langue Whisper")
    p_add.add_argument("--fast", action="store_true", help="Mode rapide Whisper")

    p_run = sub.add_parser("run", help="Traiter toutes les sources en attente")
    p_run.add_argument("--lang", default="fr", help="Langue Whisper (défaut si non spécifié par entrée)")
    p_run.add_argument("--fast", action="store_true", help="Mode rapide Whisper")

    sub.add_parser("status", help="Afficher l'état de la queue")
    sub.add_parser("clear-done", help="Vider l'historique des traitées")

    args = parser.parse_args(argv)

    dispatch = {
        "add": cmd_add,
        "run": cmd_run,
        "status": cmd_status,
        "clear-done": cmd_clear_done,
    }
    dispatch[args.cmd](args)
