"""DEPRECATED — thin wrapper. Use workflows.ingest.ingest() directly."""

from core.context import VaultContext
from core.schemas import Source


def ingest_pdf(
    file_path: str,
    ctx: VaultContext,
    title: str | None = None,
    source_type: str = "pdf",
    auto_generate_note: bool | None = None,
) -> Source:
    """Delegate to unified ingest pipeline."""
    from workflows.ingest import ingest
    return ingest(source_type, file_path, ctx, title=title, auto_generate_note=auto_generate_note)
