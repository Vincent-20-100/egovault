"""
Factory for building the application context.

Surfaces (API, CLI, MCP) call build_context() at startup and pass the result to tools.
"""

from core.config import Settings
from core.context import VaultContext

from infrastructure import embedding_provider, llm_provider, vault_writer
from infrastructure.vault_db import VaultDB


def _llm_is_configured(settings: Settings) -> bool:
    """Check if a supported LLM provider has credentials configured."""
    if settings.user.llm.provider == "claude":
        return bool(settings.install.providers.anthropic_api_key)
    return False


def build_context(settings: Settings) -> VaultContext:
    """Build a fully wired VaultContext from application settings."""
    db = VaultDB(settings.vault_db_path)

    embed_fn = lambda text: embedding_provider.embed(text, settings)  # noqa: E731

    # LLM generation is optional — None when no provider is configured
    generate_fn = None
    if _llm_is_configured(settings):
        generate_fn = lambda content, metadata, template: (  # noqa: E731
            llm_provider.generate_note_content(content, metadata, template, settings)
        )

    write_fn = lambda note, vault_path: vault_writer.write_note(note, vault_path)  # noqa: E731

    return VaultContext(
        settings=settings,
        db=db,
        system_db_path=settings.system_db_path,
        embed=embed_fn,
        generate=generate_fn,
        write_note=write_fn,
        vault_path=settings.vault_path,
        media_path=settings.media_path,
    )
