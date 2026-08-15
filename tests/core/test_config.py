import pytest
import yaml
from pathlib import Path
from pydantic import ValidationError


def _write_configs(config_dir: Path, user_dir: Path):
    (config_dir / "system.yaml").write_text(yaml.dump({
        "chunking": {"size": 800, "overlap": 80},
        "llm": {"max_retries": 2, "large_format_threshold_tokens": 50000},
        "taxonomy": {
            "note_types": ["synthese"],
            "source_types": ["youtube"],
            "generation_templates": ["standard"],
        },
    }))
    (config_dir / "user.yaml").write_text(yaml.dump({
        "embedding": {"provider": "ollama", "model": "nomic-embed-text"},
        "llm": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "vault": {"content_language": "fr", "obsidian_sync": True,
                  "default_generation_template": "standard"},
    }))
    (config_dir / "install.yaml").write_text(yaml.dump({
        "paths": {"user_dir": str(user_dir)},
        "providers": {"ollama_base_url": "http://localhost:11434"},
    }))


def test_load_settings_success(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_configs(config_dir, user_dir)

    from core.config import load_settings
    settings = load_settings(config_dir)

    assert settings.system.chunking.size == 800
    assert settings.user.embedding.provider == "ollama"
    assert settings.install.providers.ollama_base_url == "http://localhost:11434"
    assert settings.taxonomy.note_types == ["synthese"]


def test_load_settings_missing_user_yaml(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_configs(config_dir, user_dir)
    (config_dir / "user.yaml").unlink()

    from core.config import load_settings
    with pytest.raises((FileNotFoundError, ValueError)):
        load_settings(config_dir)


def test_vault_db_path_default(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_configs(config_dir, user_dir)

    from core.config import load_settings
    settings = load_settings(config_dir)
    assert settings.vault_db_path == user_dir / "data" / "vault.db"
    assert settings.system_db_path == user_dir / "data" / ".system.db"


def test_vault_db_path_custom_db_file(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    (config_dir / "system.yaml").write_text(yaml.dump({
        "chunking": {"size": 800, "overlap": 80},
        "llm": {"max_retries": 2, "large_format_threshold_tokens": 50000},
        "taxonomy": {
            "note_types": ["synthese"],
            "source_types": ["youtube"],
            "generation_templates": ["standard"],
        },
    }))
    (config_dir / "user.yaml").write_text(yaml.dump({
        "embedding": {"provider": "ollama", "model": "nomic-embed-text"},
        "llm": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "vault": {"content_language": "fr", "obsidian_sync": True,
                  "default_generation_template": "standard"},
    }))
    custom_db = tmp_path / "custom" / "vault.db"
    (config_dir / "install.yaml").write_text(yaml.dump({
        "paths": {"user_dir": str(user_dir), "db_file": str(custom_db)},
        "providers": {"ollama_base_url": "http://localhost:11434"},
    }))

    from core.config import load_settings
    settings = load_settings(config_dir)
    assert settings.vault_db_path == custom_db


def test_vault_path_default(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    (user_dir / "vault" / "notes").mkdir(parents=True)
    _write_configs(config_dir, user_dir)

    from core.config import load_settings
    settings = load_settings(config_dir)
    assert settings.vault_path == user_dir / "vault" / "notes"


def test_media_path_default(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_configs(config_dir, user_dir)

    from core.config import load_settings
    settings = load_settings(config_dir)
    assert settings.media_path == user_dir / "data" / "media"


def test_embedding_config_loads_from_system_yaml(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_configs(config_dir, user_dir)
    import yaml
    sys_yaml = yaml.safe_load((config_dir / "system.yaml").read_text())
    sys_yaml["embedding"] = {"dims": 512, "provider": "openai", "model": "text-embedding-3-small"}
    (config_dir / "system.yaml").write_text(yaml.dump(sys_yaml))

    from core.config import load_settings
    settings = load_settings(config_dir)

    assert settings.system.embedding.dims == 512
    assert settings.system.embedding.provider == "openai"
    assert settings.system.embedding.model == "text-embedding-3-small"


def test_embedding_config_defaults_to_768_if_missing(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_configs(config_dir, user_dir)

    from core.config import load_settings
    settings = load_settings(config_dir)

    assert settings.system.embedding.dims == 768
    assert settings.system.embedding.provider == "ollama"


def test_taxonomy_shortcut(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_configs(config_dir, user_dir)

    from core.config import load_settings
    settings = load_settings(config_dir)
    assert settings.taxonomy is settings.system.taxonomy


def test_curate_config_defaults():
    from core.config import load_settings

    s = load_settings()
    assert s.system.curate.escalation_min_notes == 3
    assert s.system.curate.escalation_max_distance == 0.5
    assert s.system.curate.synthesis_max_chars_per_item == 800
    assert s.system.curate.confidence.reviewed_note_weight == 1.0
    assert s.system.curate.confidence.unreviewed_note_weight == 0.7
    assert s.system.curate.confidence.rrf_k == 60


def test_note_segmentation_config_defaults():
    from core.config import NoteSegmentationConfig

    cfg = NoteSegmentationConfig()
    assert cfg.sensitivity_k == 0.5
    assert cfg.min_similarity_floor == 0.35
    assert cfg.min_chunks_per_note == 3
    assert cfg.max_notes_per_source == 30
    assert cfg.max_chunks_per_candidate == 12
    assert cfg.agent_claim_ttl_seconds == 300
    assert cfg.human_claim_ttl_seconds == 3600


def test_note_segmentation_validation_bounds():
    from core.config import NoteSegmentationConfig

    with pytest.raises(ValidationError):
        NoteSegmentationConfig(sensitivity_k=-1.0)

    with pytest.raises(ValidationError):
        NoteSegmentationConfig(max_chunks_per_candidate=0)


def test_ingest_config_defaults():
    from core.config import IngestConfig

    cfg = IngestConfig()
    assert cfg.pdf.strategy == "auto"
    assert cfg.pdf.scanned_char_threshold == 50
    assert cfg.pdf.min_image_dimension == 250
    assert cfg.ocr.engine == "rapidocr"
    assert "fr" in cfg.ocr.languages
    assert cfg.media.whisper_model == "base"
    assert cfg.media.audio_compression_bitrate_kbps == 12
    assert ".png" in cfg.image.supported_extensions


def test_install_hardware_and_database_config():
    from core.config import HardwareConfig, DatabaseConfig, ApiConfig

    hw = HardwareConfig()
    assert hw.threads == 4
    assert hw.device == "cpu"

    db = DatabaseConfig()
    assert db.busy_timeout_ms == 5000

    api = ApiConfig()
    assert "http://localhost:3000" in api.cors_origins
    assert api.rate_limits.default == "60/minute"


def test_user_export_typst_config():
    from core.config import TypstExportConfig

    cfg = TypstExportConfig()
    assert cfg.font == "Liberation Serif"
    assert cfg.language == "fr"
