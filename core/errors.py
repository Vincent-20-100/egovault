"""
Custom exceptions for EgoVault v2.
"""


class LargeFormatError(Exception):
    """
    Raised when a source exceeds large_format_threshold_tokens.
    The source is indexed for RAG (rag_ready) but note generation is blocked.
    See spec section 7.0 for the two recovery options:
      1. User writes the note manually.
      2. User provides an external summary as generation input.
    """

    def __init__(self, source_uid: str, token_count: int, threshold: int):
        self.source_uid = source_uid
        self.token_count = token_count
        self.threshold = threshold
        super().__init__(
            f"Source '{source_uid}' has {token_count} tokens, "
            f"exceeding threshold of {threshold}. "
            "Source is rag_ready. Use manual note creation or provide an external summary."
        )


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, uid: str):
        self.resource = resource
        self.uid = uid
        super().__init__(f"{resource} not found: {uid}")


class ConflictError(Exception):
    """Raised when an operation conflicts with current resource state."""

    def __init__(self, resource: str, uid: str, reason: str):
        self.resource = resource
        self.uid = uid
        self.reason = reason
        super().__init__(f"{resource} '{uid}': {reason}")
