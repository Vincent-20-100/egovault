"""
VaultContext — dependency injection container for EgoVault tools.

Tools receive a VaultContext instead of importing infrastructure directly.
This enables testing with mocks and swapping providers without touching tools.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from core.config import Settings
from core.schemas import Note, NoteContentInput

if TYPE_CHECKING:
    # Avoids circular import — core/ must not depend on infrastructure/ at runtime
    from infrastructure.vault_db import VaultDB


# -- Protocols: signatures that infrastructure providers must satisfy --


class EmbedFn(Protocol):
    """Text → embedding vector."""

    def __call__(self, text: str) -> list[float]: ...


class GenerateFn(Protocol):
    """Source content + metadata → structured note content via LLM."""

    def __call__(
        self,
        source_content: str,
        source_metadata: dict,
        template_name: str,
    ) -> NoteContentInput: ...


class WriteNoteFn(Protocol):
    """Write a Note to the vault as markdown, return the file path."""

    def __call__(self, note: Note, vault_path: Path) -> Path: ...


# -- Context dataclass --


@dataclass
class VaultContext:
    """All infrastructure dependencies, built once and passed to every tool."""

    settings: Settings
    db: "VaultDB"
    system_db_path: Path
    embed: EmbedFn
    generate: GenerateFn | None  # None = no LLM configured
    write_note: WriteNoteFn
    vault_path: Path
    media_path: Path
