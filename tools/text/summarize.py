"""
Text summarization tool.

Not yet implemented — placeholder for large-format workflow.
"""

from core.context import VaultContext
from core.schemas import SummaryResult
from core.logging import loggable


@loggable("summarize")
def summarize(text: str, ctx: VaultContext) -> SummaryResult:
    """Generate a concise summary via LLM. Not yet implemented."""
    ...
