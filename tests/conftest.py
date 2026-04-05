import pytest
import yaml
from pathlib import Path


# ============================================================
# EMBEDDING TEST HELPERS
# ============================================================

EMBEDDING_DIMS: int = 768
"""Dimension of mock embeddings — mirrors system.yaml:embedding.dims."""


def make_embedding(value: float = 0.1) -> list[float]:
    """Create a mock embedding vector with the configured dimension."""
    return [value] * EMBEDDING_DIMS


@pytest.fixture
def tmp_settings(tmp_path):
    """Minimal Settings built from test config files. Uses tmp_path as user_dir."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    (config_dir / "system.yaml").write_text(yaml.dump({
        "chunking": {"size": 800, "overlap": 80},
        "embedding": {"dims": 768, "provider": "ollama", "model": "nomic-embed-text"},
        "llm": {"max_retries": 2, "large_format_threshold_tokens": 50000},
        "taxonomy": {
            "note_types": ["synthese", "concept", "reflexion"],
            "source_types": ["youtube", "audio", "pdf"],
            "generation_templates": ["standard"],
        },
    }))

    (config_dir / "user.yaml").write_text(yaml.dump({
        "embedding": {"provider": "ollama", "model": "nomic-embed-text"},
        "llm": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "vault": {
            "content_language": "fr",
            "obsidian_sync": True,
            "default_generation_template": "standard",
        },
        "allow_destructive_ops": False,
    }))

    user_dir = tmp_path / "egovault-user"
    (user_dir / "data").mkdir(parents=True)
    (user_dir / "vault" / "notes").mkdir(parents=True)

    (config_dir / "install.yaml").write_text(yaml.dump({
        "paths": {"user_dir": str(user_dir)},
        "providers": {"ollama_base_url": "http://localhost:11434"},
    }))

    from core.config import load_settings
    return load_settings(config_dir)


@pytest.fixture
def tmp_db(tmp_path):
    """Initialized test database (all tables created)."""
    from infrastructure.db import init_db
    db_file = tmp_path / "test.db"
    init_db(db_file)
    return db_file
