"""
Shared fixtures for API tests.

- tmp_settings: Settings with temp vault.db + .system.db
- client: FastAPI TestClient wrapping the app
"""

import pytest
import yaml
from pathlib import Path
from fastapi.testclient import TestClient

from core.config import load_settings
from infrastructure.db import init_db, init_system_db


def _write_configs(config_dir: Path, user_dir: Path) -> None:
    (config_dir / "system.yaml").write_text(yaml.dump({
        "chunking": {"size": 800, "overlap": 80},
        "llm": {"max_retries": 2, "large_format_threshold_tokens": 50000},
        "taxonomy": {
            "note_types": ["synthese", "reflexion"],
            "source_types": ["youtube", "audio", "pdf"],
            "generation_templates": ["standard"],
        },
    }))
    (config_dir / "user.yaml").write_text(yaml.dump({
        "embedding": {"provider": "ollama", "model": "nomic-embed-text"},
        "llm": {"provider": "ollama", "model": "llama3"},
        "vault": {"content_language": "fr", "obsidian_sync": False,
                  "default_generation_template": "standard"},
    }))
    (config_dir / "install.yaml").write_text(yaml.dump({
        "paths": {"user_dir": str(user_dir)},
        "providers": {"ollama_base_url": "http://localhost:11434"},
    }))


@pytest.fixture(scope="session")
def tmp_settings(tmp_path_factory):
    base = tmp_path_factory.mktemp("egovault")
    config_dir = base / "config"
    config_dir.mkdir()
    user_dir = base / "user"
    (user_dir / "data").mkdir(parents=True)
    (user_dir / "data" / "media").mkdir()

    _write_configs(config_dir, user_dir)
    settings = load_settings(config_dir)

    init_db(settings.vault_db_path)
    init_system_db(settings.system_db_path)

    return settings


@pytest.fixture(scope="session")
def client(tmp_settings):
    from api.main import create_app
    app = create_app(tmp_settings)
    with TestClient(app) as c:
        yield c
