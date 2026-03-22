"""
clean_sources.py
Identifie sources non référencées. Vide _archive/ sur confirmation.
Usage:
  python scripts/clean_sources.py [--vault PATH]           <- rapport seul
  python scripts/clean_sources.py [--vault PATH] --delete  <- vide _archive/ après confirmation
"""
import re
import shutil
import argparse
from pathlib import Path

NOTE_FOLDERS = ["notes"]


def get_referenced_sources(vault_path: Path) -> set:
    """Retourne les slugs de sources référencés dans les notes."""
    referenced = set()
    for folder in NOTE_FOLDERS:
        folder_path = vault_path / folder
        if not folder_path.exists():
            continue
        for note in folder_path.glob("*.md"):
            text = note.read_text(encoding="utf-8")
            for match in re.findall(r"source:\s*[\"']?\[\[sources/([^/\]]+)/", text):
                referenced.add(match)
    return referenced


def find_unreferenced_sources(vault_path: Path) -> list:
    """Retourne les sous-dossiers de sources/ non référencés par aucune note."""
    referenced = get_referenced_sources(vault_path)
    sources_path = vault_path / "sources"
    unreferenced = []
    if sources_path.exists():
        for item in sources_path.iterdir():
            if item.is_dir() and item.name != "raw-sources":
                if item.name not in referenced:
                    unreferenced.append(item.name)
    return unreferenced


def list_archive(vault_path: Path) -> list:
    archive = vault_path / "sources" / "raw-sources" / "_archive"
    if not archive.exists():
        return []
    return [item.name for item in archive.iterdir()
            if item.is_dir() and item.name != ".gitkeep"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", default=".", help="Chemin racine du vault")
    parser.add_argument("--delete", action="store_true",
                        help="Vide _archive/ après confirmation")
    args = parser.parse_args()
    vault = Path(args.vault)

    unreferenced = find_unreferenced_sources(vault)
    archive_items = list_archive(vault)

    print("\n=== RAPPORT CLEAN SOURCES ===")
    print(f"\n[Sources permanentes non référencées] ({len(unreferenced)})")
    for s in unreferenced:
        print(f"  - sources/{s}/")

    print(f"\n[Archive à vider] ({len(archive_items)})")
    for s in archive_items:
        print(f"  - raw-sources/_archive/{s}/")

    if args.delete and archive_items:
        confirm = input("\nVider _archive/ ? (oui/non) : ").strip().lower()
        if confirm == "oui":
            archive = vault / "sources" / "raw-sources" / "_archive"
            for item in archive.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                    print(f"  Supprimé : {item.name}")
        else:
            print("Annulé.")
