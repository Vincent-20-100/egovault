"""
Text summarization tool.

Input  : text + settings
Output : SummaryResult
No DB write. Used internally by workflows — not exposed directly to users.
"""

from core.schemas import SummaryResult
from core.config import Settings
from core.logging import loggable


@loggable("summarize")
def summarize(text: str, settings: Settings) -> SummaryResult:
    """
    Generate a concise summary of the provided text via LLM.
    Used by large-format workflow (external summary path).
    No DB write.
    """
    ...
