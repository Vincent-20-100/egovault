"""
Custom exceptions for EgoVault v2.
"""


class IngestError(Exception):
    """Base class for errors that occur during content ingestion."""

    def __init__(self, user_message: str, error_code: str, http_status: int = 400):
        self.error_code = error_code
        self.user_message = user_message
        self.http_status = http_status
        super().__init__(user_message)


class EmptyContentError(IngestError):
    """Raised when ingested content is empty or yields no usable text."""

    def __init__(self, user_message: str = "No content could be extracted from the source."):
        super().__init__(user_message, error_code="empty_content", http_status=400)


class ContentTooLargeError(IngestError):
    """Raised when ingested content exceeds the configured size limit."""

    def __init__(self, user_message: str = "Content exceeds the maximum allowed size."):
        super().__init__(user_message, error_code="content_too_large", http_status=413)


class LargeFormatError(IngestError):
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
        user_message = (
            f"Source '{source_uid}' has {token_count} tokens, "
            f"exceeding threshold of {threshold}. "
            "Source is rag_ready. Use manual note creation or provide an external summary."
        )
        super().__init__(user_message, error_code="large_format", http_status=422)


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
