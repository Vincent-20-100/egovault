"""
_core.py
Utilitaires partagés pour tous les handlers d'ingestion.
Ne jamais appeler directement — importé par youtube.py, audio.py, etc.
"""
import re
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML requis : pip install pyyaml")

from scripts._config import get_vault_path, get_sources_path

# Constantes de détection de type — importées par capture.py et queue.py
YOUTUBE_PATTERN = re.compile(r"(youtube\.com|youtu\.be)")
AUDIO_EXTENSIONS = frozenset({".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"})
VIDEO_EXTENSIONS = frozenset({".mp4", ".mkv", ".avi", ".mov", ".webm"})

ACCENT_MAP = str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc")

STATUS_PENDING = "pending"
STATUS_READY   = "ready"
STATUS_FAILED  = "failed"
_VALID_STATUSES = {STATUS_PENDING, STATUS_READY, STATUS_FAILED}

RAW_SOURCES = get_sources_path() / "raw-sources"


def slug(text: str, max_len: int = 50) -> str:
    """Normalise un texte en slug kebab-case sans accents."""
    text = text.lower().translate(ACCENT_MAP)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text[:max_len].strip("-")


def _unique_folder(base: Path) -> Path:
    """Retourne base si disponible, sinon base-2, base-3, etc."""
    if not base.exists():
        return base
    i = 2
    while True:
        candidate = base.parent / f"{base.name}-{i}"
        if not candidate.exists():
            return candidate
        i += 1


def make_drop_off(title: str, source_type: str, url: str = "",
                  extra_fields: dict | None = None) -> Path:
    """
    Crée un sous-dossier dans raw-sources/ et écrit source.md avec status: pending.
    En cas de doublon de slug, ajoute automatiquement -2, -3, etc.
    Retourne le chemin du dossier créé.
    """
    date = datetime.now().strftime("%Y-%m-%d")
    folder_path = _unique_folder(RAW_SOURCES / slug(title))

    # Sécurité : s'assurer que le chemin reste sous RAW_SOURCES
    if not str(folder_path.resolve()).startswith(str(RAW_SOURCES.resolve())):
        raise ValueError(f"Chemin hors de RAW_SOURCES : {folder_path}")

    folder_path.mkdir(parents=True, exist_ok=True)

    fields = {
        "date_ajout": date,
        "type_source": source_type,
        "titre": title,
        "url": url,
        "status": STATUS_PENDING,
        "note_creee": "",
    }
    if extra_fields:
        fields.update(extra_fields)

    content = "---\n" + yaml.dump(
        fields, allow_unicode=True, default_flow_style=False, sort_keys=False
    ) + "---\n"
    (folder_path / "source.md").write_text(content, encoding="utf-8")
    return folder_path


def set_status(folder_path: Path, status: str):
    """Met à jour le champ status dans source.md."""
    if status not in _VALID_STATUSES:
        raise ValueError(f"Status invalide : {status!r}. Valeurs : {_VALID_STATUSES}")
    source_md = folder_path / "source.md"
    text = source_md.read_text(encoding="utf-8")
    text = re.sub(r"^status:.*$", f"status: {status}", text, flags=re.MULTILINE)
    source_md.write_text(text, encoding="utf-8")


def find_duplicate(url: str, raw_sources: Path | None = None) -> "Path | None":
    """
    Cherche un drop-off existant avec la même URL dans raw-sources/ (hors _archive/).
    Retourne le chemin du dossier si trouvé, None sinon.
    """
    if not url:
        return None
    root = raw_sources if raw_sources is not None else RAW_SOURCES
    if not root.exists():
        return None
    for source_md in root.rglob("source.md"):
        if "_archive" in source_md.parts:
            continue
        try:
            text = source_md.read_text(encoding="utf-8")
            match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
            if match:
                data = yaml.safe_load(match.group(1)) or {}
                if data.get("url") == url:
                    return source_md.parent
        except (yaml.YAMLError, OSError):
            continue
    return None
