"""
scripts/setup/init_user_dir.py

Creates the egovault-user/ directory structure for a fresh installation.
Does NOT touch any existing directory — fails if target already exists.

Usage:
  .venv/Scripts/python scripts/setup/init_user_dir.py
  .venv/Scripts/python scripts/setup/init_user_dir.py --target ../egovault-user
  .venv/Scripts/python scripts/setup/init_user_dir.py --force   # overwrite .obsidian config only
"""

import argparse
import json
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent.parent

# Default target: sibling of the repo root
DEFAULT_TARGET = REPO_ROOT.parent / "egovault-user"

# Obsidian: files/folders matching these patterns are excluded from search + graph
OBSIDIAN_IGNORE_FILTERS = [
    "_*",       # _index.md, _status.md, etc.
    "**/_*",    # nested _* files
]

OBSIDIAN_APP = {
    "userIgnoreFilters": OBSIDIAN_IGNORE_FILTERS
}

OBSIDIAN_CORE_PLUGINS = {
    "file-explorer": True,
    "global-search": True,
    "switcher": True,
    "graph": True,
    "backlink": True,
    "canvas": True,
    "outgoing-link": True,
    "tag-pane": True,
    "footnotes": False,
    "properties": True,
    "page-preview": True,
    "daily-notes": True,
    "templates": True,
    "note-composer": True,
    "command-palette": True,
    "slash-command": False,
    "editor-status": True,
    "bookmarks": True,
    "markdown-importer": False,
    "zk-prefixer": False,
    "random-note": False,
    "outline": True,
    "word-count": True,
    "slides": False,
    "audio-recorder": False,
    "workspaces": False,
    "file-recovery": True,
    "publish": False,
    "sync": True,
    "bases": True,
    "webviewer": False,
}


def create_dir(path: Path, label: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    print(f"  [ok] {label}: {path}")


def write_json(path: Path, data: dict, label: str) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  [ok] {label}: {path.name}")


def copy_config(src: Path, dst: Path, label: str) -> None:
    shutil.copy2(src, dst)
    print(f"  [ok] {label}: {dst}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize egovault-user/ directory structure.")
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help=f"Target directory (default: {DEFAULT_TARGET})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Do not fail if target exists — only write missing files",
    )
    args = parser.parse_args()

    target: Path = args.target.resolve()

    if target.exists() and not args.force:
        print(f"[error] Directory already exists: {target}")
        print("        Use --force to write missing files into an existing directory.")
        sys.exit(1)

    print(f"\nInitializing egovault-user at: {target}\n")

    # --- Directory structure ---
    print("Creating directories...")
    create_dir(target / "data" / "media", "data/media/")
    create_dir(target / "vault" / "notes", "vault/notes/")
    create_dir(target / "vault" / ".obsidian", "vault/.obsidian/")

    # --- Obsidian config ---
    print("\nWriting Obsidian config...")
    obsidian_dir = target / "vault" / ".obsidian"
    write_json(obsidian_dir / "app.json", OBSIDIAN_APP, "app.json")
    write_json(obsidian_dir / "core-plugins.json", OBSIDIAN_CORE_PLUGINS, "core-plugins.json")

    # --- EgoVault config files ---
    config_src = REPO_ROOT / "config"
    config_dst_user = config_src / "user.yaml"
    config_dst_install = config_src / "install.yaml"

    print("\nSetting up config files...")

    if not config_dst_user.exists():
        copy_config(config_src / "user.yaml.example", config_dst_user, "config/user.yaml")
    else:
        print(f"  [skip] config/user.yaml already exists")

    if not config_dst_install.exists():
        copy_config(config_src / "install.yaml.example", config_dst_install, "config/install.yaml")
        # Patch install.yaml with the resolved target path
        text = config_dst_install.read_text(encoding="utf-8")
        text = text.replace('"../egovault-user"', f'"{target.as_posix()}"')
        config_dst_install.write_text(text, encoding="utf-8")
        print(f"       patched user_dir -> {target}")
    else:
        print(f"  [skip] config/install.yaml already exists")

    print(f"\nDone. Open {target / 'vault'} as an Obsidian vault (Add vault in Obsidian).")
    print("Then run: .venv/Scripts/python -m pytest tests/  to verify the installation.\n")


if __name__ == "__main__":
    main()
