"""
update_index.py
Reconstruit _index.md depuis les frontmatters YAML de toutes les notes du vault.
Usage: python scripts/update_index.py [--vault PATH]
"""
import re
import sys
import argparse
from pathlib import Path
from datetime import date
from collections import defaultdict

# Permet l'exécution directe (python scripts/update_index.py) et via -m
if __package__ is None:
    sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts._config import get_vault_path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML requis : pip install pyyaml")

NOTE_FOLDERS = ["notes"]

# Seuil de détection des candidats à une note-concept (voir LLM.md et AMELIORATIONS.md)
CONCEPT_CANDIDATE_THRESHOLD = 4


def parse_frontmatter(path: Path) -> dict:
    """Extrait le frontmatter YAML d'une note."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def has_links(path: Path) -> bool:
    """Vérifie si une note contient des liens [[...]]."""
    text = path.read_text(encoding="utf-8")
    return bool(re.search(r"\[\[.+?\]\]", text))


def build_index(vault_path: Path) -> dict:
    """Construit la structure de l'index depuis les notes du vault."""
    tags = defaultdict(list)
    orphelines = []
    by_type = defaultdict(list)

    for folder in NOTE_FOLDERS:
        folder_path = vault_path / folder
        if not folder_path.exists():
            continue
        for note in sorted(folder_path.glob("*.md")):
            fm = parse_frontmatter(note)
            note_tags = fm.get("tags", [])
            if isinstance(note_tags, str):
                note_tags = [note_tags]
            rel = f"{folder}/{note.name}"
            for tag in note_tags:
                tags[tag].append(rel)
            if not has_links(note):
                orphelines.append(note.name)
            note_type = fm.get("note_type", "inconnu")
            by_type[note_type].append(rel)

    return {"tags": dict(tags), "orphelines": orphelines, "by_type": by_type}


def write_index(vault_path: Path):
    """Écrit _index.md à la racine du vault."""
    data = build_index(vault_path)
    today = date.today().isoformat()
    lines = [
        "# Index du vault",
        "",
        f"_Dernière mise à jour : {today}_",
        "",
        "## Tags",
        "",
    ]
    for tag, notes in sorted(data["tags"].items()):
        refs = ", ".join(f"[[{n}]]" for n in notes)
        lines.append(f"- `{tag}` → {refs}")

    # Candidats à une note-concept (tags avec suffisamment de notes)
    candidates = [
        tag for tag, notes in data["tags"].items()
        if len(notes) >= CONCEPT_CANDIDATE_THRESHOLD
        and not any(n.startswith("notes/concept-") or "concept" in n for n in notes)
    ]
    if candidates:
        lines += ["", "## Candidats note-concept (à créer manuellement)", ""]
        lines.append(f"_Tags avec {CONCEPT_CANDIDATE_THRESHOLD}+ notes — potentiellement mûrs pour une note-concept hub :_")
        lines.append("")
        for tag in sorted(candidates):
            count = len(data["tags"][tag])
            lines.append(f"- `{tag}` ({count} notes)")

    lines += ["", "## Par type", ""]
    for ntype, notes_list in sorted(data["by_type"].items()):
        refs = ", ".join(f"[[{n}]]" for n in notes_list)
        lines.append(f"- `{ntype}` → {refs}")

    lines += ["", "## Notes orphelines (sans liens)", ""]
    if data["orphelines"]:
        for note in data["orphelines"]:
            lines.append(f"- [[{note}]]")
    else:
        lines.append("<!-- aucune -->")

    (vault_path / "_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"_index.md mis à jour ({today})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", default=".", help="Chemin racine du vault")
    args = parser.parse_args()
    vault_path = get_vault_path() if args.vault == "." else Path(args.vault)
    write_index(vault_path)
