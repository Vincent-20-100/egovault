"""
scripts/migrate_rename.py
Migration T2 : supprime les préfixes YYYY-MM-DD des noms de fichiers/dossiers.

Actions :
  - notes/YYYY-MM-DD-slug.md       → notes/slug.md
  - sources/YYYY-MM-DD-slug/       → sources/slug/
  - wikilinks dans le contenu      → mis à jour en conséquence
  - source.md : note_creee mis à jour

Options :
  --dry-run (défaut) : affiche les changements sans les appliquer
  --apply            : applique réellement les changements

Usage :
  python scripts/migrate_rename.py [--vault PATH]
  python scripts/migrate_rename.py [--vault PATH] --apply
"""
import re
import sys
import shutil
import argparse
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML requis : pip install pyyaml")

from scripts._config import get_vault_path, get_sources_path

DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-(.+)$")


def strip_date(name: str) -> str | None:
    """Retourne le nom sans préfixe date, ou None si pas de préfixe."""
    m = DATE_PREFIX.match(name)
    return m.group(1) if m else None


def unique_name(target: Path) -> Path:
    """Ajoute un suffixe -2, -3... si la cible existe déjà."""
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    i = 2
    while True:
        candidate = parent / f"{stem}-{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def build_rename_map(vault_path: Path, sources_path: Path | None = None) -> tuple[dict, dict]:
    """
    Construit deux dicts de renommage :
      notes_map  : {ancien_nom_stem: nouveau_nom_stem}  (sans .md)
      sources_map: {ancien_dossier: nouveau_dossier}
    """
    notes_map = {}
    notes_dir = vault_path / "notes"
    if notes_dir.exists():
        for f in sorted(notes_dir.glob("*.md")):
            if f.name.startswith("_"):
                continue
            new_stem = strip_date(f.stem)
            if new_stem and new_stem != f.stem:
                notes_map[f.stem] = new_stem

    sources_map = {}
    sources_dir = sources_path if sources_path is not None else vault_path / "sources"
    if sources_dir.exists():
        for d in sorted(sources_dir.iterdir()):
            if not d.is_dir() or d.name.startswith("_") or d.name == "raw-sources":
                continue
            new_name = strip_date(d.name)
            if new_name and new_name != d.name:
                sources_map[d.name] = new_name

    return notes_map, sources_map


def update_content(text: str, notes_map: dict, sources_map: dict) -> str:
    """
    Remplace dans le contenu toutes les références datées :
    - [[notes/YYYY-MM-DD-slug.md]] → [[notes/slug.md]]
    - [[notes/YYYY-MM-DD-slug]]    → [[notes/slug]]
    - [[syntheses/YYYY-MM-DD-slug]]→ [[notes/slug]]  (ancienne convention)
    - [[sources/YYYY-MM-DD-slug/source.md]] → [[sources/slug/source.md]]
    - note_creee: "[[notes/YYYY-MM-DD-slug.md]]"
    """
    # notes avec .md
    for old, new in notes_map.items():
        text = text.replace(f"[[notes/{old}.md]]", f"[[notes/{new}.md]]")
        text = text.replace(f"[[notes/{old}]]", f"[[notes/{new}]]")
        # ancienne convention syntheses/
        text = text.replace(f"[[syntheses/{old}]]", f"[[notes/{new}]]")
        # note_creee dans source.md
        text = text.replace(f"[[notes/{old}.md]]", f"[[notes/{new}.md]]")

    # dossiers sources
    for old, new in sources_map.items():
        text = text.replace(f"[[sources/{old}/", f"[[sources/{new}/")

    return text


def migrate(vault_path: Path, sources_path: Path, apply: bool):
    notes_map, sources_map = build_rename_map(vault_path, sources_path)

    if not notes_map and not sources_map:
        print("Aucun préfixe date trouvé — vault déjà migré.")
        return

    print(f"{'[DRY-RUN] ' if not apply else ''}Migrations détectées :\n")

    # --- Notes ---
    notes_dir = vault_path / "notes"
    renamed_notes: list[tuple[Path, Path]] = []
    for old_stem, new_stem in notes_map.items():
        old_path = notes_dir / f"{old_stem}.md"
        new_path = unique_name(notes_dir / f"{new_stem}.md")
        print(f"  notes/{old_stem}.md -> notes/{new_path.name}")
        renamed_notes.append((old_path, new_path))

    # --- Sources ---
    sources_dir = sources_path
    renamed_sources: list[tuple[Path, Path]] = []
    for old_name, new_name in sources_map.items():
        old_path = sources_dir / old_name
        new_path = unique_name(sources_dir / new_name)
        if new_path.name != new_name:
            print(f"  sources/{old_name}/ -> sources/{new_path.name}/  (conflit -> numerote)")
        else:
            print(f"  sources/{old_name}/ -> sources/{new_path.name}/")
        renamed_sources.append((old_path, new_path))

    # --- Content updates ---
    md_files = list(notes_dir.glob("*.md")) if notes_dir.exists() else []
    # source.md files
    for d in (sources_dir.iterdir() if sources_dir.exists() else []):
        if d.is_dir():
            sm = d / "source.md"
            if sm.exists():
                md_files.append(sm)

    content_changes = []
    for f in md_files:
        original = f.read_text(encoding="utf-8")
        updated = update_content(original, notes_map, sources_map)
        if updated != original:
            content_changes.append((f, updated))

    if content_changes:
        print(f"\n  Contenu mis à jour dans {len(content_changes)} fichier(s) :")
        for f, _ in content_changes:
            rel = f.relative_to(vault_path)
            print(f"    {rel}")

    if not apply:
        print("\n  -> Dry-run. Utilisez --apply pour appliquer.")
        return

    # Apply content changes BEFORE renaming (paths still valid)
    for f, new_content in content_changes:
        f.write_text(new_content, encoding="utf-8")

    # Rename notes
    for old_path, new_path in renamed_notes:
        old_path.rename(new_path)

    # Rename source folders
    for old_path, new_path in renamed_sources:
        old_path.rename(new_path)

    print(f"\n  Migration appliquee : {len(renamed_notes)} note(s), {len(renamed_sources)} dossier(s) source.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Supprime les préfixes YYYY-MM-DD des fichiers vault.")
    parser.add_argument("--vault", default=None, help="Chemin racine du vault (défaut: config.yaml)")
    parser.add_argument("--apply", action="store_true", help="Appliquer les changements (défaut: dry-run)")
    args = parser.parse_args()

    vault = Path(args.vault).resolve() if args.vault else get_vault_path()
    if not vault.exists():
        sys.exit(f"Vault introuvable : {vault}")

    migrate(vault, sources_path=get_sources_path(), apply=args.apply)
