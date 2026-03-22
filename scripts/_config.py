"""
_config.py
Lecture centralisée de config.yaml.
Usage : from scripts._config import get_vault_path
"""
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML requis : pip install pyyaml")

_APP_ROOT = Path(__file__).parent.parent


def load_config() -> dict:
    config_path = _APP_ROOT / "config.yaml"
    if not config_path.exists():
        raise SystemExit(
            "config.yaml introuvable. Copier config.yaml.example en config.yaml et ajuster."
        )
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_vault_path() -> Path:
    cfg = load_config()
    vault_cfg = cfg.get("vault")
    if not isinstance(vault_cfg, dict):
        raise SystemExit(
            "config.yaml invalide : la clé 'vault' est absente ou mal formée.\n"
            "Vérifier config.yaml.example pour le format attendu."
        )
    raw = vault_cfg.get("data_path", ".")
    path = (_APP_ROOT / raw).resolve()
    if not path.exists():
        raise SystemExit(
            f"vault.data_path introuvable : {path}\nVérifier config.yaml"
        )
    return path


def get_sources_path() -> Path:
    cfg = load_config()
    vault_cfg = cfg.get("vault", {})
    raw = vault_cfg.get("sources_path")
    if raw:
        return (_APP_ROOT / raw).resolve()
    # Fallback : sources/ à l'intérieur du vault (ancienne structure)
    return get_vault_path() / "sources"
