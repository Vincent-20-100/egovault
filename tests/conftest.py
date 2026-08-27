"""
Shared pytest fixtures for EgoVault tests.

Provides a minimal VaultContext (ctx) wired to temp storage and mock providers,
plus lower-level helpers (tmp_settings, tmp_db) for tests that need finer control.
"""

import pytest
import yaml


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
        "note_segmentation": {
            "sensitivity_k": 0.5,
            "min_similarity_floor": 0.35,
            "min_chunks_per_note": 3,
            "max_notes_per_source": 30,
            "max_chunks_per_candidate": 12,
            "agent_claim_ttl_seconds": 300,
            "human_claim_ttl_seconds": 3600,
        },
        "curate": {
            "escalation_min_notes": 3,
            "escalation_max_distance": 0.5,
            "synthesis_max_chars_per_item": 800,
            "use_hybrid_retrieval": False,
            "confidence": {
                "reviewed_note_weight": 1.0,
                "unreviewed_note_weight": 0.7,
                "rrf_k": 60,
            },
        },
        "ingest": {
            "pdf": {
                "strategy": "auto",
                "scanned_char_threshold": 50,
                "extract_images": True,
                "min_image_dimension": 250,
                "max_repeated_image_count": 2,
            },
            "ocr": {
                "engine": "rapidocr",
                "languages": ["fr", "en"],
            },
            "media": {
                "whisper_model": "base",
                "whisper_device": "cpu",
                "whisper_compute_type": "int8",
                "audio_compression_bitrate_kbps": 12,
                "subtitle_fallback_languages": ["fr", "en"],
            },
            "image": {
                "supported_extensions": [".png", ".jpg", ".jpeg", ".webp", ".svg"],
                "vlm_captioning": False,
            },
        },
        "llm": {"max_retries": 2, "max_tokens": 4096, "temperature": 0.2, "large_format_threshold_tokens": 50000},
        "upload": {"max_audio_mb": 500, "max_pdf_mb": 100, "max_text_chars": 500000},
        "web": {
            "extraction_tier": 0,
            "max_response_mb": 10,
            "timeout_seconds": 30,
            "min_fetch_interval_seconds": 2,
            "max_redirects": 5,
        },
        "taxonomy": {
            "note_types": ["synthese", "concept", "reflexion", "idee"],
            "source_types": ["youtube", "audio", "video", "pdf", "livre", "texte", "html", "web", "image", "personnel"],
            "generation_templates": ["standard"],
        },
    }))

    (config_dir / "user.yaml").write_text(yaml.dump({
        "embedding": {"provider": "ollama", "model": "nomic-embed-text"},
        "llm": {"provider": "claude", "model": "claude-sonnet-4-6", "auto_generate_note": False},
        "vault": {
            "content_language": "fr",
            "obsidian_sync": True,
            "default_generation_template": "standard",
        },
        "export": {
            "typst": {
                "font": "Liberation Serif",
                "heading_font": "Liberation Sans",
                "code_font": "DejaVu Sans Mono",
                "language": "fr",
            },
        },
        "allow_destructive_ops": False,
    }))

    user_dir = tmp_path / "egovault-user"
    (user_dir / "data").mkdir(parents=True)
    (user_dir / "vault" / "notes").mkdir(parents=True)

    (config_dir / "install.yaml").write_text(yaml.dump({
        "paths": {"user_dir": str(user_dir)},
        "hardware": {"threads": 4, "device": "cpu"},
        "database": {"busy_timeout_ms": 5000},
        "api": {
            "cors_origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "rate_limits": {"default": "60/minute", "ingest": "10/minute", "search": "120/minute"},
        },
        "providers": {
            "ollama_base_url": "http://localhost:11434",
            "ollama_num_ctx": 8192,
            "ollama_timeout_s": 180,
            "openai_api_key": None,
            "anthropic_api_key": None,
        },
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
        # Non-zero: cosine distance is undefined for the zero vector
        embed=lambda text: make_embedding(),
        generate=None,
        # Real vault_writer so tests that check markdown file existence work correctly
        write_note=_write_note,
        vault_path=vault_path,
        media_path=media_path,
    )
