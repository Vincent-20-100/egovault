"""
scripts/init_vault.py
Initialise la structure du vault data si elle n'existe pas.

Crée :
  {sources_path}/                   ← hors vault Obsidian
  ├── raw-sources/
  │   └── _archive/
  └── queue.yaml                    ← géré à l'exécution

  {vault_path}/                     ← racine Obsidian (ex: egovault-data/egovault/)
  ├── .git/               ← git init (si absent)
  ├── .gitignore
  ├── .obsidian/
  │   ├── app.json        ← _* exclus du graph
  │   └── graph.json      ← hideUnresolved + filtre -path:sources
  ├── notes/
  ├── _index.md           ← vide (sera rempli par update_index.py)
  └── _status.md          ← vide (sera rempli par vault_status.py)

Usage :
  uv run python scripts/init_vault.py
  uv run python scripts/init_vault.py --force   ← recrée les fichiers manquants même si le dossier existe
"""
import sys
import json
import argparse
import subprocess
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts._config import get_vault_path, get_sources_path

GITIGNORE_CONTENT = """\
# Fichiers audio/vidéo — jamais dans git
*.mp3
*.MP3
*.wav
*.WAV
*.m4a
*.M4A
*.mp4
*.MP4
*.mkv
*.avi
*.mov
*.webm
*.ogg
*.flac
*.aac

# Transcriptions temporaires
sources/raw-sources/*/transcript.tmp
sources/raw-sources/**/transcript.tmp

# Runtime — état local, pas versionné
sources/queue.yaml

# Obsidian — fichiers locaux machine-specific
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/cache
"""

OBSIDIAN_APP_JSON = {
    "userIgnoreFilters": ["sources/", "**/_*"]
}

OBSIDIAN_GRAPH_JSON = {
    "collapse-filter": True,
    "search": "-path:sources",
    "showTags": False,
    "showAttachments": False,
    "hideUnresolved": True,
    "showOrphans": True,
    "collapse-color-groups": True,
    "colorGroups": [],
    "collapse-display": True,
    "showArrow": False,
    "textFadeMultiplier": 0,
    "nodeSizeMultiplier": 1,
    "lineSizeMultiplier": 1,
    "collapse-forces": True,
    "centerStrength": 0.518713248970312,
    "repelStrength": 10,
    "linkStrength": 1,
    "linkDistance": 250,
    "scale": 1,
    "close": False
}


def create_dir(path: Path, label: str) -> bool:
    if path.exists():
        return False
    path.mkdir(parents=True)
    print(f"  + {label}")
    return True


def create_file(path: Path, content: str, label: str, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    path.write_text(content, encoding="utf-8")
    print(f"  + {label}")
    return True


def init_git(vault_path: Path):
    git_dir = vault_path / ".git"
    if git_dir.exists():
        print("  ~ git déjà initialisé")
        return
    subprocess.run(["git", "init", str(vault_path)], capture_output=True)
    print("  + git init")


def main():
    parser = argparse.ArgumentParser(description="Initialise la structure du vault data.")
    parser.add_argument("--force", action="store_true",
                        help="Recrée les fichiers manquants même si le dossier existe déjà")
    args = parser.parse_args()

    try:
        vault_path = get_vault_path()
    except SystemExit:
        # config.yaml absent ou data_path introuvable — on laisse passer
        # car on est peut-être en train de créer le vault pour la première fois
        import yaml
        config_path = Path(__file__).parent.parent / "config.yaml"
        if not config_path.exists():
            sys.exit(
                "config.yaml introuvable.\n"
                "Copier config.yaml.example en config.yaml et définir vault.data_path."
            )
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
        raw = cfg.get("vault", {}).get("data_path", "")
        if not raw:
            sys.exit("vault.data_path non défini dans config.yaml.")
        vault_path = (Path(config_path).parent / raw).resolve()

    try:
        sources_path = get_sources_path()
    except SystemExit:
        import yaml
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
        raw = cfg.get("vault", {}).get("sources_path", "")
        sources_path = (Path(config_path).parent / raw).resolve() if raw else vault_path.parent / "sources"

    print(f"\nInitialisation du vault  : {vault_path}")
    print(f"Initialisation sources   : {sources_path}\n")

    # Dossiers vault (racine Obsidian)
    create_dir(vault_path, "egovault/")
    create_dir(vault_path / "notes", "egovault/notes/")
    create_dir(vault_path / ".obsidian", "egovault/.obsidian/")

    # Dossiers sources (hors vault)
    create_dir(sources_path, "sources/")
    create_dir(sources_path / "raw-sources", "sources/raw-sources/")
    create_dir(sources_path / "raw-sources" / "_archive", "sources/raw-sources/_archive/")

    # Fichiers de config — .gitignore à la racine de egovault-data/ (parent du vault)
    data_root = vault_path.parent
    create_file(data_root / ".gitignore", GITIGNORE_CONTENT, ".gitignore", args.force)
    create_file(
        vault_path / ".obsidian" / "app.json",
        json.dumps(OBSIDIAN_APP_JSON, indent=2, ensure_ascii=False) + "\n",
        ".obsidian/app.json",
        args.force,
    )
    create_file(
        vault_path / ".obsidian" / "graph.json",
        json.dumps(OBSIDIAN_GRAPH_JSON, indent=2, ensure_ascii=False) + "\n",
        ".obsidian/graph.json",
        args.force,
    )

    # Fichiers méta (vides, seront remplis par les scripts)
    create_file(vault_path / "_index.md", "# Index du vault\n\n_À générer via `update_index.py`_\n",
                "_index.md", args.force)
    create_file(vault_path / "_status.md", "# Status du vault\n\n_À générer via `vault_status.py`_\n",
                "_status.md", args.force)

    # Git
    init_git(vault_path)

    print("\nVault initialisé. Prochaines étapes :")
    print("  1. uv run python scripts/vault_status.py")
    print("  2. Ouvrir le dossier vault dans Obsidian")


if __name__ == "__main__":
    main()
