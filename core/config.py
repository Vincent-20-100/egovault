"""
Configuration loader for EgoVault.

Loads, merges, and validates the 3-tier configuration (system.yaml, user.yaml, install.yaml).
Strictly validated via Pydantic at startup — missing or out-of-bounds fields fail fast.
"""

from pathlib import Path
from pydantic import BaseModel, Field


# ============================================================
# TAXONOMY CONFIG (system.yaml)
# ============================================================

class TaxonomyConfig(BaseModel):
    note_types: list[str] = Field(default_factory=lambda: ["synthese", "concept", "reflexion", "idee"])
    source_types: list[str] = Field(default_factory=lambda: [
        "youtube", "audio", "video", "pdf", "livre", "texte", "web", "image", "personnel"
    ])
    generation_templates: list[str] = Field(default_factory=lambda: ["standard"])


# ============================================================
# SYSTEM CONFIG (system.yaml)
# ============================================================

class ChunkingConfig(BaseModel):
    size: int = Field(default=800, ge=1, le=40000)
    overlap: int = Field(default=80, ge=0, le=10000)


class EmbeddingConfig(BaseModel):
    dims: int = Field(default=768, ge=64, le=4096)
    provider: str = "ollama"
    model: str = "nomic-embed-text"


class NoteSegmentationConfig(BaseModel):
    sensitivity_k: float = Field(default=0.5, ge=0.0, le=5.0)
    min_similarity_floor: float = Field(default=0.35, ge=0.0, le=1.0)
    min_chunks_per_note: int = Field(default=3, ge=1, le=50)
    max_notes_per_source: int = Field(default=30, ge=1, le=500)
    max_chunks_per_candidate: int = Field(default=12, ge=1, le=100)
    agent_claim_ttl_seconds: int = Field(default=300, ge=10, le=86400)
    human_claim_ttl_seconds: int = Field(default=3600, ge=60, le=604800)


class QueryVaultConfidenceConfig(BaseModel):
    reviewed_note_weight: float = Field(default=1.0, ge=0.0, le=10.0)
    unreviewed_note_weight: float = Field(default=0.7, ge=0.0, le=10.0)
    rrf_k: int = Field(default=60, ge=1, le=1000)


class QueryVaultConfig(BaseModel):
    escalation_min_notes: int = Field(default=3, ge=1, le=50)
    escalation_max_distance: float = Field(default=0.5, ge=0.0, le=2.0)
    synthesis_max_chars_per_item: int = Field(default=800, ge=100, le=10000)
    use_hybrid_retrieval: bool = False
    confidence: QueryVaultConfidenceConfig = Field(default_factory=QueryVaultConfidenceConfig)


CurateConfidenceConfig = QueryVaultConfidenceConfig
CurateConfig = QueryVaultConfig


class IngestPdfConfig(BaseModel):
    strategy: str = "auto"
    scanned_char_threshold: int = Field(default=50, ge=0, le=1000)
    extract_images: bool = True
    min_image_dimension: int = Field(default=250, ge=50, le=5000)
    max_repeated_image_count: int = Field(default=2, ge=1, le=100)


class IngestOcrConfig(BaseModel):
    engine: str = "rapidocr"
    dpi: int = Field(default=150, ge=72, le=600)
    languages: list[str] = Field(default_factory=lambda: ["fr", "en"])


class IngestMediaConfig(BaseModel):
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    audio_compression_bitrate_kbps: int = Field(default=12, ge=6, le=320)
    subtitle_fallback_languages: list[str] = Field(default_factory=lambda: ["fr", "en"])


class IngestImageConfig(BaseModel):
    supported_extensions: list[str] = Field(
        default_factory=lambda: [".png", ".jpg", ".jpeg", ".webp", ".svg"]
    )
    vlm_captioning: bool = False


class IngestConfig(BaseModel):
    pdf: IngestPdfConfig = Field(default_factory=IngestPdfConfig)
    ocr: IngestOcrConfig = Field(default_factory=IngestOcrConfig)
    media: IngestMediaConfig = Field(default_factory=IngestMediaConfig)
    image: IngestImageConfig = Field(default_factory=IngestImageConfig)


class LLMSystemConfig(BaseModel):
    max_retries: int = Field(default=2, ge=0, le=10)
    max_tokens: int = Field(default=4096, ge=256, le=32768)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    large_format_threshold_tokens: int = Field(default=50000, ge=1000)  # Legacy threshold fallback


class UploadConfig(BaseModel):
    max_audio_mb: int = Field(default=500, ge=1, le=5000)
    max_pdf_mb: int = Field(default=100, ge=1, le=2000)
    max_text_chars: int = Field(default=500_000, ge=1000, le=50_000_000)


class WebConfig(BaseModel):
    extraction_tier: int = Field(default=0, ge=0, le=2)
    max_response_mb: int = Field(default=10, ge=1, le=100)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    min_fetch_interval_seconds: int = Field(default=2, ge=0, le=60)
    max_redirects: int = Field(default=5, ge=0, le=20)


class SystemConfig(BaseModel):
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    note_segmentation: NoteSegmentationConfig = Field(default_factory=NoteSegmentationConfig)
    query_vault: QueryVaultConfig = Field(default_factory=QueryVaultConfig)
    ingest: IngestConfig = Field(default_factory=IngestConfig)
    llm: LLMSystemConfig = Field(default_factory=LLMSystemConfig)
    upload: UploadConfig = Field(default_factory=UploadConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    taxonomy: TaxonomyConfig = Field(default_factory=TaxonomyConfig)

    @property
    def curate(self) -> QueryVaultConfig:
        return self.query_vault


# ============================================================
# USER CONFIG (user.yaml)
# ============================================================

class EmbeddingUserConfig(BaseModel):
    provider: str = "ollama"
    model: str = "nomic-embed-text"


class LLMUserConfig(BaseModel):
    provider: str = "ollama"
    model: str = "llama3"
    auto_generate_note: bool = False


class VaultUserConfig(BaseModel):
    content_language: str = "fr"
    obsidian_sync: bool = True
    default_generation_template: str = "standard"


class TypstExportConfig(BaseModel):
    font: str = "Liberation Serif"
    heading_font: str = "Liberation Sans"
    code_font: str = "DejaVu Sans Mono"
    language: str = "fr"


class ExportUserConfig(BaseModel):
    typst: TypstExportConfig = Field(default_factory=TypstExportConfig)


class UserConfig(BaseModel):
    embedding: EmbeddingUserConfig = Field(default_factory=EmbeddingUserConfig)
    llm: LLMUserConfig = Field(default_factory=LLMUserConfig)
    vault: VaultUserConfig = Field(default_factory=VaultUserConfig)
    export: ExportUserConfig = Field(default_factory=ExportUserConfig)
    allow_destructive_ops: bool = False  # Expose delete/purge tools via MCP


# ============================================================
# INSTALL CONFIG (install.yaml)
# ============================================================

class PathsConfig(BaseModel):
    user_dir: str = "../egovault-user"
    data_dir: str | None = None
    vault_dir: str | None = None
    media_dir: str | None = None
    db_file: str | None = None


class HardwareConfig(BaseModel):
    threads: int = Field(default=4, ge=1, le=64)
    device: str = "cpu"


class DatabaseConfig(BaseModel):
    busy_timeout_ms: int = Field(default=5000, ge=100, le=60000)


class ApiRateLimitsConfig(BaseModel):
    default: str = "60/minute"
    ingest: str = "10/minute"
    search: str = "120/minute"


class ApiConfig(BaseModel):
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    rate_limits: ApiRateLimitsConfig = Field(default_factory=ApiRateLimitsConfig)


class ProvidersConfig(BaseModel):
    ollama_base_url: str = "http://localhost:11434"
    ollama_num_ctx: int = Field(default=8192, ge=512, le=131072)
    ollama_timeout_s: int = Field(default=180, ge=10, le=3600)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


class InstallConfig(BaseModel):
    paths: PathsConfig = Field(default_factory=PathsConfig)
    hardware: HardwareConfig = Field(default_factory=HardwareConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)


# ============================================================
# MERGED SETTINGS — single object passed everywhere via VaultContext
# ============================================================

class Settings(BaseModel):
    system: SystemConfig = Field(default_factory=SystemConfig)
    user: UserConfig = Field(default_factory=UserConfig)
    install: InstallConfig = Field(default_factory=InstallConfig)

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
