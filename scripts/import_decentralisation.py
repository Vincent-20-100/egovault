"""
import_decentralisation.py
Migration one-shot des notes de l'ancien vault Décentralisation.
Crée un drop-off dans sources/raw-sources/ par note source.
Usage: python scripts/import_decentralisation.py [--dry-run]
"""
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

VAULT_ROOT = Path(__file__).parent.parent
SOURCE_DIR = Path(r"C:\Users\Vincent\GitHub\Vincent-20-100\Decentralisation\ObsidianNotes\notes")
RAW_SOURCES = VAULT_ROOT / "sources" / "raw-sources"

ACCENT_MAP = str.maketrans(
    "àâäéèêëîïôöùûüç",
    "aaaeeeeiioouuuc"
)


def extract_inline_tags(content: str) -> list:
    return re.findall(r"#([\w\-éèêëàâäîïôöùûüç]+)", content)


def normalize_tag(tag: str) -> str:
    return tag.lower().translate(ACCENT_MAP)


def pascal_to_kebab(name: str) -> str:
    return name.lower()


def extract_creation_date(content: str) -> str:
    match = re.search(r"Créé le.*?(\d{4}-\d{2}-\d{2})", content)
    if match:
        return match.group(1)
    return "2025-07-14"


def convert_note(source_path: Path, dry_run: bool):
    content = source_path.read_text(encoding="utf-8")
    tags_raw = extract_inline_tags(content)
    tags_normalized = sorted(set(normalize_tag(t) for t in tags_raw))
    creation_date = extract_creation_date(content)
    kebab_name = pascal_to_kebab(source_path.stem)
    folder_name = f"{creation_date}-{kebab_name}"
    folder_path = RAW_SOURCES / folder_name

    source_md = f"""---
date_ajout: {datetime.now().strftime("%Y-%m-%d")}
type_source: note-vault-decentralisation
titre: "{source_path.stem.replace('-', ' ')}"
fichier_original: "{source_path.name}"
date_source: {creation_date}
tags_originaux: {tags_normalized}
note_creee: ""
---

Note importée depuis le vault Décentralisation (juillet 2025).
Tags normalisés depuis le format inline #tag original.
À traiter via Workflow A — enrichissement + réflexion personnelle à ajouter.
"""

    if dry_run:
        print(f"[DRY-RUN] {folder_name}/")
        print(f"  tags: {tags_normalized}")
        return

    folder_path.mkdir(parents=True, exist_ok=True)
    (folder_path / "source.md").write_text(source_md, encoding="utf-8")
    (folder_path / "note_originale.md").write_text(content, encoding="utf-8")
    print(f"Importé : sources/raw-sources/{folder_name}/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Affiche ce qui serait fait sans créer de fichiers")
    args = parser.parse_args()

    if not SOURCE_DIR.exists():
        sys.exit(f"Dossier source introuvable : {SOURCE_DIR}")

    notes = [f for f in SOURCE_DIR.glob("*.md") if f.stem != "Note-sans-titre"]
    print(f"{'[DRY-RUN] ' if args.dry_run else ''}{len(notes)} notes à importer")

    for note in sorted(notes):
        convert_note(note, args.dry_run)


if __name__ == "__main__":
    main()
