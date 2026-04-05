"""DEPRECATED — thin wrapper. Use workflows.ingest.ingest() directly."""

from core.context import VaultContext
from core.schemas import Source


def ingest_youtube(url: str, ctx: VaultContext, auto_generate_note: bool | None = None) -> Source:
    """Delegate to unified ingest pipeline."""
    from workflows.ingest import ingest
    return ingest("youtube", url, ctx, auto_generate_note=auto_generate_note)
