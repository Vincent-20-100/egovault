# Configuration & Zero-Hardcode Architecture (TOML / YAML + Pydantic)

> **Golden Rule (Zero-Hardcode)**: Code describes *how* to process logic; configuration files describe *what parameters, thresholds, paths, and credentials* to use. Never hardcode numbers or strings that could conceivably change between environments or runs.

---

## 🎯 1. Why TOML is the Modern Python Standard

* **Human-friendly**: Intuitive syntax, native typing (integers, floats, booleans, dates, arrays, nested tables).
* **Python Native**: Standard library support via `tomllib` (Python 3.11+) for reading; `tomli-w` for writing.
* **Ecosystem Alignment**: `pyproject.toml`, `ruff.toml`, and modern tools already use TOML.

---

## 🏗️ 2. Clean Configuration Pattern (Pydantic BaseSettings)

### Example `config.toml`:

```toml
[server]
host = "127.0.0.1"
port = 8000
timeout_seconds = 60
workers = 4

[processing]
batch_size = 250
similarity_threshold = 0.82
max_retry_attempts = 3
retry_delay_seconds = 1.5

[storage]
data_dir = "./var/data"
db_filename = "vault.sqlite"
enable_wal_mode = true
```

### Type-Safe Loader (`core/config.py`):

```python
"""Application settings loader with strict Pydantic validation."""

from pathlib import Path
from typing import Self
import tomllib

from pydantic import BaseModel, Field, field_validator


class ServerConfig(BaseModel):
    """Server network and execution configuration."""

    host: str = Field(default="127.0.0.1", description="Bind host address")
    port: int = Field(default=8000, ge=1024, le=65535, description="TCP port number")
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    workers: int = Field(default=4, ge=1, le=64)


class ProcessingConfig(BaseModel):
    """Business logic thresholds and tuning parameters."""

    batch_size: int = Field(default=250, gt=0, le=10_000)
    similarity_threshold: float = Field(default=0.82, ge=0.0, le=1.0)
    max_retry_attempts: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: float = Field(default=1.5, ge=0.1, le=60.0)


class StorageConfig(BaseModel):
    """Filesystem and database storage settings."""

    data_dir: Path = Field(default=Path("./var/data"))
    db_filename: str = Field(default="vault.sqlite")
    enable_wal_mode: bool = Field(default=True)

    @field_validator("data_dir", mode="after")
    @classmethod
    def ensure_dir_resolved(cls, v: Path) -> Path:
        """Resolve path to absolute form."""
        return v.expanduser().resolve()

    @property
    def db_path(self) -> Path:
        """Derive complete database file path."""
        return self.data_dir / self.db_filename


class Settings(BaseModel):
    """Root configuration object containing all sub-configurations."""

    server: ServerConfig
    processing: ProcessingConfig
    storage: StorageConfig

    @classmethod
    def from_toml(cls, toml_path: Path | str) -> Self:
        """Load and validate settings from a TOML file.

        Args:
            toml_path: Path to the configuration TOML file.

        Returns:
            Validated, immutable Settings instance.

        Raises:
            FileNotFoundError: If the specified config file does not exist.
            ValueError: If TOML is malformed or validation fails.
        """
        path = Path(toml_path)
        if not path.is_file():
            raise FileNotFoundError(f"Configuration file not found at: {path.absolute()}")

        with path.open("rb") as f:
            raw_data = tomllib.load(f)

        return cls.model_validate(raw_data)
```

---

## 🌐 3. Environment Variable Overrides (`pydantic-settings`)

For production or containerized environments (12-Factor App), allow environment variables to cleanly override TOML defaults:

```bash
uv add pydantic-settings
```

```python
"""Environment-aware settings using pydantic-settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class AppSettings(BaseSettings):
    """Global settings with automated ENV override support."""

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_nested_delimiter="__",
        toml_file="config.toml",
        extra="ignore",
    )

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    api_key: str = Field(default="", description="Secret API key from environment")
```

Setting `export APP_PORT=9000` automatically overrides the port to `9000`.

---

## 🚫 Anti-Vibecoding Checklist for Config

- [ ] **Semantic Tuning Parameters in Config**: If a value represents a runtime threshold, timeout, batch limit, filesystem path, or network endpoint (e.g. `similarity_threshold = 0.82`, `timeout = 30`), it MUST reside in `config.toml` / `settings.yaml`.
- [ ] **Structural & Math Constants in Code**: Universal constants (e.g. `SECONDS_PER_DAY = 86_400`, loop offsets `+ 1`, percentage conversions `* 100`) belong in code as named module constants or inline math literals.
- [ ] **No raw hardcoded paths**: Avoid string literals like `"/tmp/output.csv"`. Use `pathlib.Path` objects in config models.
- [ ] **Typed validation**: Every config field must declare validation boundaries (`ge=...`, `le=...`, `gt=0`) to fail fast at startup on invalid values.
- [ ] **Immutability**: Once loaded into runtime context, settings should be treated as read-only.
