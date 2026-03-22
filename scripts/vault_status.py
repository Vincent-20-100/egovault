"""
vault_status.py
Produit un snapshot de l'état du vault dans _status.md.
Usage: python scripts/vault_status.py [--vault PATH]
"""
import re
import sys
import argparse
from pathlib import Path
from datetime import date
from collections import defaultdict

# Permet l'exécution directe (python scripts/vault_status.py) et via -m
if __package__ is None:
    sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts._config import get_vault_path

try:
    import yaml
except ImportError:
    yaml = None

NOTE_FOLDERS = ["notes"]


def _parse_frontmatter(path: Path) -> dict:
    """Extrait le frontmatter YAML d'une note. Retourne {} si absent ou yaml non disponible."""
    if yaml is None:
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not match:
            return {}
        return yaml.safe_load(match.group(1)) or {}
    except Exception:
        return {}


def _read_status_field(source_md: Path) -> str:
    """Lit le champ status dans source.md. Retourne 'unknown' si absent."""
    try:
        text = source_md.read_text(encoding="utf-8")
        match = re.search(r"^status:\s*(\S+)", text, re.MULTILINE)
        return match.group(1) if match else "unknown"
    except Exception:
        return "unknown"


def get_status(vault_path: Path) -> dict:
    notes = {}
    for folder in NOTE_FOLDERS:
        p = vault_path / folder
        notes[folder] = len(list(p.glob("*.md"))) if p.exists() else 0

    # Comptage par note_type dans notes/
    by_type = defaultdict(int)
    notes_folder = vault_path / "notes"
    if notes_folder.exists():
        for note in notes_folder.glob("*.md"):
            if note.name == "_context.md":
                continue
            fm = _parse_frontmatter(note)
            note_type = fm.get("note_type", "inconnu")
            by_type[note_type] += 1

    raw_root = vault_path / "sources" / "raw-sources"
    raw_pending = []
    if raw_root.exists():
        for item in raw_root.iterdir():
            if item.is_dir() and item.name != "_archive":
                source_md = item / "source.md"
                status = _read_status_field(source_md) if source_md.exists() else "unknown"
                raw_pending.append({"name": item.name, "status": status})

    sources_path = vault_path / "sources"
    permanent_sources = []
    if sources_path.exists():
        for item in sources_path.iterdir():
            if item.is_dir() and item.name != "raw-sources":
                permanent_sources.append(item.name)

    return {
        "notes": notes,
        "by_type": dict(by_type),
        "raw_pending": raw_pending,
        "permanent_sources": permanent_sources,
    }


def write_status(vault_path: Path):
    s = get_status(vault_path)
    today = date.today().isoformat()
    lines = [
        f"# VAULT STATUS — {today}",
        "",
        "## Notes",
    ]
    for folder, count in s["notes"].items():
        lines.append(f"  {folder:<14}: {count}")

    lines += ["", "## Notes par type", ""]
    for ntype, count in sorted(s["by_type"].items()):
        lines.append(f"  {ntype:<14}: {count}")

    lines += ["", "## Sources en attente (raw-sources/)"]
    if s["raw_pending"]:
        for item in sorted(s["raw_pending"], key=lambda x: x["name"]):
            flag = ""
            if item["status"] == "failed":
                flag = "  ← ECHEC TRANSCRIPTION"
            elif item["status"] == "pending":
                flag = "  ← transcription en cours"
            lines.append(f"  - {item['name']} [{item['status']}]{flag}")
    else:
        lines.append("  aucune")

    lines += ["", "## Sources permanentes"]
    lines.append(f"  {len(s['permanent_sources'])} dossier(s)")

    out = vault_path / "_status.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"_status.md écrit ({today})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", default=".", help="Chemin racine du vault")
    args = parser.parse_args()
    vault_path = get_vault_path() if args.vault == "." else Path(args.vault)
    write_status(vault_path)
