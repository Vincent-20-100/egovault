"""
Custom exceptions for EgoVault (Error Architecture V2 - Rule G6).

Centralized source of truth for all domain exceptions.
All exceptions inherit from EgoVaultError, providing:
- error_code: machine-readable snake_case identifier
- user_message: clean, human-readable message without leaking system paths or secret keys
- actionable_hint: concrete diagnostic advice to resolve the error
- http_status: standard HTTP response code for API mapping
- context: safe structured metadata dictionary
"""


class EgoVaultError(Exception):
    """
    Base exception for all EgoVault domain errors.
    Enforces standardized error codes, user messages, and actionable hints.
    """

    def __init__(
        self,
        user_message: str,
        error_code: str = "internal_error",
        actionable_hint: str = "Check system logs or configuration.",
        http_status: int = 500,
        context: dict | None = None,
    ):
        self.user_message = user_message
        self.error_code = error_code
        self.actionable_hint = actionable_hint
        self.http_status = http_status
        self.context = context or {}
        super().__init__(user_message)

    def to_dict(self) -> dict:
        """Serialize error details for API and MCP error payloads."""
        return {
            "error": self.error_code,
            "message": self.user_message,
            "hint": self.actionable_hint,
            "status_code": self.http_status,
            "context": self.context,
        }


# ============================================================
# CONFIGURATION ERRORS
# ============================================================

class ConfigError(EgoVaultError):
    """Base class for configuration and installation errors."""

    def __init__(
        self,
        user_message: str,
        error_code: str = "config_error",
        actionable_hint: str = "Check your configuration files in config/ directory.",
        http_status: int = 500,
        context: dict | None = None,
    ):
        super().__init__(
            user_message=user_message,
            error_code=error_code,
            actionable_hint=actionable_hint,
            http_status=http_status,
            context=context,
        )


class MissingConfigError(ConfigError):
    """Raised when a required configuration file is missing."""

    def __init__(self, filename: str):
        example_file = filename.replace(".yaml", ".yaml.example")
        super().__init__(
            user_message=f"Required configuration file '{filename}' was not found.",
            error_code="missing_config_file",
            actionable_hint=f"Copy {example_file} to {filename} and fill in your values.",
            http_status=500,
            context={"filename": filename},
        )


class InvalidConfigValueError(ConfigError):
    """Raised when a configuration parameter is invalid or out of bounds."""

    def __init__(self, key: str, value: str, reason: str):
        super().__init__(
            user_message=f"Configuration parameter '{key}' has invalid value '{value}': {reason}",
            error_code="invalid_config_value",
            actionable_hint="Review the configuration schema in core/config.py and fix the value.",
            http_status=500,
            context={"key": key, "value": value},
        )


class MissingSecretError(ConfigError):
    """Raised when a required API secret or key is not set."""

    def __init__(self, secret_name: str, provider: str):
        super().__init__(
            user_message=f"Missing API key '{secret_name}' required for provider '{provider}'.",
            error_code="missing_secret",
            actionable_hint=f"Set '{secret_name}' in config/install.yaml or switch to local 'ollama' provider.",
            http_status=500,
            context={"provider": provider},
        )


# ============================================================
# INGESTION ERRORS
# ============================================================

class IngestError(EgoVaultError):
    """Base class for errors that occur during content ingestion."""

    def __init__(
        self,
        user_message: str,
        error_code: str = "ingest_error",
        actionable_hint: str = "Verify the input file or URL and retry ingestion.",
        http_status: int = 400,
        context: dict | None = None,
    ):
        super().__init__(
            user_message=user_message,
            error_code=error_code,
            actionable_hint=actionable_hint,
            http_status=http_status,
            context=context,
        )


class EmptyContentError(IngestError):
    """Raised when ingested content is empty or yields no usable text."""

    def __init__(
        self,
        user_message: str = "No content could be extracted from the source.",
        actionable_hint: str = "Ensure the source file or URL contains readable text.",
    ):
        super().__init__(
            user_message=user_message,
            error_code="empty_content",
            actionable_hint=actionable_hint,
            http_status=400,
        )


class ContentTooLargeError(IngestError):
    """Raised when ingested content exceeds the configured size limit."""

    def __init__(
        self,
        user_message: str = "Content exceeds the maximum allowed size limit.",
        actionable_hint: str = "Reduce file size or increase limits in config/system.yaml under 'upload'.",
    ):
        super().__init__(
            user_message=user_message,
            error_code="content_too_large",
            actionable_hint=actionable_hint,
            http_status=413,
        )


class UnsupportedFormatError(IngestError):
    """Raised when the input file extension or MIME type is not supported."""

    def __init__(self, format_name: str):
        super().__init__(
            user_message=f"Unsupported content format: '{format_name}'.",
            error_code="unsupported_format",
            actionable_hint="Provide a supported format (PDF, audio, video, text, HTML, web URL, image).",
            http_status=400,
            context={"format": format_name},
        )


class CorruptMediaError(IngestError):
    """Raised when a media file (audio, video, PDF) is corrupt or unreadable."""

    def __init__(self, media_path: str, reason: str):
        super().__init__(
            user_message=f"Media file cannot be decoded: {reason}",
            error_code="corrupt_media",
            actionable_hint="Check if the file is corrupted or encoded in an unsupported codec.",
            http_status=422,
            context={"media_path": media_path},
        )


class LargeFormatError(IngestError):
    """
    Deprecated: Large format error for legacy threshold checking.
    Maintained for backwards compatibility with existing tests.
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
        super().__init__(
            user_message=user_message,
            error_code="large_format",
            actionable_hint="Source is indexed and searchable. Segment into candidates or create notes manually.",
            http_status=422,
            context={"source_uid": source_uid, "token_count": token_count, "threshold": threshold},
        )


# ============================================================
# PROVIDER & MODEL ERRORS
# ============================================================

class ProviderError(EgoVaultError):
    """Base class for AI embedding and LLM provider errors."""

    def __init__(
        self,
        user_message: str,
        error_code: str = "provider_error",
        actionable_hint: str = "Check provider status, connection, and API keys.",
        http_status: int = 502,
        context: dict | None = None,
    ):
        super().__init__(
            user_message=user_message,
            error_code=error_code,
            actionable_hint=actionable_hint,
            http_status=http_status,
            context=context,
        )


class ProviderUnavailableError(ProviderError):
    """Raised when an external or local AI service is unreachable."""

    def __init__(self, provider: str, url: str):
        super().__init__(
            user_message=f"AI service '{provider}' is unavailable at '{url}'.",
            error_code="provider_unavailable",
            actionable_hint=f"Ensure the service is running (e.g. 'ollama serve') and accessible.",
            http_status=503,
            context={"provider": provider, "url": url},
        )


class ModelNotFoundError(ProviderError):
    """Raised when a requested model is not found on the provider."""

    def __init__(self, model_name: str, provider: str):
        super().__init__(
            user_message=f"Model '{model_name}' was not found on provider '{provider}'.",
            error_code="model_not_found",
            actionable_hint=f"Install the model on the provider (e.g. 'ollama pull {model_name}').",
            http_status=502,
            context={"model": model_name, "provider": provider},
        )


class ProviderTimeoutError(ProviderError):
    """Raised when a provider API call exceeds configured timeout."""

    def __init__(self, provider: str, timeout_seconds: int):
        super().__init__(
            user_message=f"Request to AI provider '{provider}' timed out after {timeout_seconds}s.",
            error_code="provider_timeout",
            actionable_hint="Increase timeout in config/install.yaml or reduce input size.",
            http_status=504,
            context={"provider": provider, "timeout_seconds": timeout_seconds},
        )


class StructuredOutputValidationError(ProviderError):
    """Raised when LLM output cannot be parsed into required Pydantic schema."""

    def __init__(self, model_name: str, raw_output: str, reason: str):
        super().__init__(
            user_message=f"Model '{model_name}' generated invalid structured output: {reason}",
            error_code="structured_output_validation_failed",
            actionable_hint="Retry the operation or switch to a higher-capability model.",
            http_status=502,
            context={"model": model_name},
        )


# ============================================================
# RESOURCE & STATE ERRORS
# ============================================================

class ResourceError(EgoVaultError):
    """Base class for database resource, state, and concurrency errors."""

    def __init__(
        self,
        user_message: str,
        error_code: str = "resource_error",
        actionable_hint: str = "Verify resource UID and current vault state.",
        http_status: int = 400,
        context: dict | None = None,
    ):
        super().__init__(
            user_message=user_message,
            error_code=error_code,
            actionable_hint=actionable_hint,
            http_status=http_status,
            context=context,
        )


class NotFoundError(ResourceError):
    """Raised when a requested resource (Note, Source, Chunk, Candidate) does not exist."""

    def __init__(
        self,
        resource: str,
        uid: str,
        actionable_hint: str = "Verify the UID and ensure the resource exists and has not been purged.",
    ):
        self.resource = resource
        self.uid = uid
        super().__init__(
            user_message=f"{resource} not found: {uid}",
            error_code="not_found",
            actionable_hint=actionable_hint,
            http_status=404,
            context={"resource": resource, "uid": uid},
        )


class ConflictError(ResourceError):
    """Raised when an operation conflicts with current resource state."""

    def __init__(
        self,
        resource: str,
        uid: str,
        reason: str,
        actionable_hint: str = "Resolve the conflicting resource state before repeating the operation.",
    ):
        self.resource = resource
        self.uid = uid
        self.reason = reason
        super().__init__(
            user_message=f"{resource} '{uid}': {reason}",
            error_code="conflict",
            actionable_hint=actionable_hint,
            http_status=409,
            context={"resource": resource, "uid": uid, "reason": reason},
        )


class CandidateClaimedError(ResourceError):
    """Raised when an agent attempts to claim a candidate locked by another active session."""

    def __init__(self, candidate_uid: str, claimed_by: str, ttl_remaining_seconds: int):
        super().__init__(
            user_message=(
                f"Candidate '{candidate_uid}' is currently locked by session '{claimed_by}' "
                f"(expires in {ttl_remaining_seconds}s)."
            ),
            error_code="candidate_already_claimed",
            actionable_hint="Pick another candidate with list_note_candidates(status='queued') or wait.",
            http_status=409,
            context={
                "candidate_uid": candidate_uid,
                "claimed_by": claimed_by,
                "ttl_remaining_seconds": ttl_remaining_seconds,
            },
        )


class ExpiredLockError(ResourceError):
    """Raised when a note conversion is attempted with an expired or lost lock."""

    def __init__(
        self,
        user_message: str = "Candidate lock has expired or was reclaimed by another session.",
        error_code: str = "expired_candidate_lock",
        actionable_hint: str = "Re-claim the candidate using claim_note_candidate() before converting.",
    ):
        super().__init__(
            user_message=user_message,
            error_code=error_code,
            actionable_hint=actionable_hint,
            http_status=409,
        )


# ============================================================
# SECURITY & CONFINEMENT ERRORS
# ============================================================

class SecurityError(EgoVaultError):
    """Base class for security and path confinement violations."""

    def __init__(
        self,
        user_message: str,
        error_code: str = "security_error",
        actionable_hint: str = "Ensure operation complies with security boundaries.",
        http_status: int = 403,
        context: dict | None = None,
    ):
        super().__init__(
            user_message=user_message,
            error_code=error_code,
            actionable_hint=actionable_hint,
            http_status=http_status,
            context=context,
        )


class PathTraversalError(SecurityError):
    """Raised when a file path violates confinement boundaries."""

    def __init__(self, attempted_path: str):
        super().__init__(
            user_message=f"Access denied: Path '{attempted_path}' is outside allowed directories.",
            error_code="path_traversal_denied",
            actionable_hint="Operations are strictly restricted to configured media and vault directories.",
            http_status=403,
            context={"attempted_path": attempted_path},
        )


class SSRFBlockedError(SecurityError):
    """Raised when a URL targets a private IP, loopback, or cloud metadata endpoint."""

    def __init__(self, url: str, reason: str):
        super().__init__(
            user_message=f"URL request blocked by security policy: {reason}",
            error_code="ssrf_blocked",
            actionable_hint="Provide a publicly routable HTTP or HTTPS URL.",
            http_status=403,
            context={"url": url, "reason": reason},
        )
