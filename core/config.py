"""
Configuration loader for EgoVault v2.

Loads and merges the three config files:
  - config/system.yaml  (versioned, algorithm params + taxonomy)
  - config/user.yaml    (gitignored, user preferences)
  - config/install.yaml (gitignored, machine paths + secrets)

Validated via a single Pydantic Settings model at startup.
Missing required fields → explicit error before anything executes.
"""

from pydantic import BaseModel
from pathlib import Path


# ============================================================
# TAXONOMY MODELS
# ============================================================

class TaxonomyConfig(BaseModel):
    note_types: list[str]
    source_types: list[str]
    generation_templates: list[str]


# ============================================================
# SYSTEM CONFIG (system.yaml)
# ============================================================

class ChunkingConfig(BaseModel):
    size: int = 800
    overlap: int = 80


class LLMSystemConfig(BaseModel):
    max_retries: int = 2
    large_format_threshold_tokens: int = 50000


class UploadConfig(BaseModel):
    max_audio_mb: int = 500
    max_pdf_mb: int = 100


class SystemConfig(BaseModel):
    chunking: ChunkingConfig
    llm: LLMSystemConfig
    upload: UploadConfig = UploadConfig()
    taxonomy: TaxonomyConfig


# ============================================================
# USER CONFIG (user.yaml)
# ============================================================

class EmbeddingUserConfig(BaseModel):
    provider: str = "ollama"
    model: str = "nomic-embed-text"


class LLMUserConfig(BaseModel):
    provider: str = "ollama"
    model: str = "llama3"


class VaultUserConfig(BaseModel):
    content_language: str = "fr"
    obsidian_sync: bool = True
    default_generation_template: str = "standard"


class UserConfig(BaseModel):
    embedding: EmbeddingUserConfig
    llm: LLMUserConfig
    vault: VaultUserConfig


# ============================================================
# INSTALL CONFIG (install.yaml)
# ============================================================

class PathsConfig(BaseModel):
    user_dir: str = "../egovault-user"
    data_dir: str | None = None
    vault_dir: str | None = None
    media_dir: str | None = None
    db_file: str | None = None


class ProvidersConfig(BaseModel):
    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


class InstallConfig(BaseModel):
    paths: PathsConfig
    providers: ProvidersConfig


# ============================================================
# MERGED SETTINGS — single object passed everywhere
# ============================================================

class Settings(BaseModel):
    system: SystemConfig
    user: UserConfig
    install: InstallConfig

    @property
    def taxonomy(self) -> TaxonomyConfig:
        return self.system.taxonomy

    def _data_dir(self) -> Path:
        if self.install.paths.data_dir:
            return Path(self.install.paths.data_dir)
        return Path(self.install.paths.user_dir) / "data"

    @property
    def vault_db_path(self) -> Path:
        """Resolved path to vault.db (user knowledge — must be backed up)."""
        if self.install.paths.db_file:
            return Path(self.install.paths.db_file)
        return self._data_dir() / "vault.db"

    @property
    def system_db_path(self) -> Path:
        """Resolved path to .system.db (operational state — can be wiped)."""
        return self._data_dir() / ".system.db"

    @property
    def vault_path(self) -> Path:
        """Resolved path to the Obsidian vault notes/ directory."""
        if self.install.paths.vault_dir:
            return Path(self.install.paths.vault_dir)
        return Path(self.install.paths.user_dir) / "vault" / "notes"

    @property
    def media_path(self) -> Path:
        """Resolved path to the media/ directory."""
        if self.install.paths.media_dir:
            return Path(self.install.paths.media_dir)
        return self._data_dir() / "media"


def load_settings(config_dir: Path | None = None) -> Settings:
    """
    Load, merge, and validate all three config files.
    config_dir defaults to the repo root's config/ directory.
    Raises FileNotFoundError if any required config file is missing.
    """
    import yaml

    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "config"

    def _load(filename: str) -> dict:
        path = config_dir / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Required config file not found: {path}\n"
                f"Copy {filename.replace('.yaml', '.yaml.example')} and fill in your values."
            )
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    system_data = _load("system.yaml")
    user_data = _load("user.yaml")
    install_data = _load("install.yaml")

    return Settings(
        system=SystemConfig(**system_data),
        user=UserConfig(**user_data),
        install=InstallConfig(**install_data),
    )
