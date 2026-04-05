import pytest
import yaml
from pathlib import Path


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
