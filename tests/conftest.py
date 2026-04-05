"""
Shared pytest fixtures for EgoVault tests.

Provides a minimal VaultContext (ctx) wired to temp storage and mock providers,
plus lower-level helpers (tmp_settings, tmp_db) for tests that need finer control.
"""

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
            "source_types": ["youtube", "audio", "video", "pdf", "livre", "texte", "html", "personnel"],
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


@pytest.fixture
def ctx(tmp_settings, tmp_path):
    """
    Fully wired VaultContext for tool-level tests.

    Uses a real SQLite DB, mock embed/write_note, and no LLM (generate=None).
    Prefer this fixture over wiring infrastructure manually in each test.
    """
    from infrastructure.db import init_db
    from infrastructure.vault_db import VaultDB
    from core.context import VaultContext

    # Real DB so tools can read back what they write
    db_path = tmp_path / "vault.db"
    init_db(db_path)
    db = VaultDB(db_path)

    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    media_path = tmp_path / "media"
    media_path.mkdir()

    from infrastructure.vault_writer import write_note as _write_note

    return VaultContext(
        settings=tmp_settings,
        db=db,
        system_db_path=tmp_path / ".system.db",
        embed=lambda text: make_embedding(0.0),
        generate=None,
        # Real vault_writer so tests that check markdown file existence work correctly
        write_note=_write_note,
        vault_path=vault_path,
        media_path=media_path,
    )
