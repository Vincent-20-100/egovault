"""Token estimation — heuristic, zero dependencies.

Used by the synthesis cascade to decide when a source exceeds the
LLM context window. Accuracy is not critical: a ~10% drift on a
threshold ratio of 0.6 is well within the safety margin.
"""

WORDS_PER_TOKEN = 0.75


def estimate_tokens(text: str) -> int:
    """Estimate token count from word count using a fixed ratio."""
    if not text or not text.strip():
        return 0
    return round(len(text.split()) / WORDS_PER_TOKEN)
