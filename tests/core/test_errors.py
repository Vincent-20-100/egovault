import pytest
from core.errors import (
    EgoVaultError,
    MissingConfigError,
    InvalidConfigValueError,
    MissingSecretError,
    EmptyContentError,
    ContentTooLargeError,
    UnsupportedFormatError,
    CorruptMediaError,
    LargeFormatError,
    ProviderUnavailableError,
    ModelNotFoundError,
    ProviderTimeoutError,
    StructuredOutputValidationError,
    NotFoundError,
    ConflictError,
    CandidateClaimedError,
    ExpiredLockError,
    PathTraversalError,
    SSRFBlockedError,
)


def test_egovault_error_base():
    err = EgoVaultError(
        user_message="Something failed",
        error_code="failed_op",
        actionable_hint="Try again",
        http_status=400,
        context={"key": "val"},
    )
    assert str(err) == "Something failed"
    assert err.user_message == "Something failed"
    assert err.error_code == "failed_op"
    assert err.actionable_hint == "Try again"
    assert err.http_status == 400
    assert err.context == {"key": "val"}

    d = err.to_dict()
    assert d["error"] == "failed_op"
    assert d["message"] == "Something failed"
    assert d["hint"] == "Try again"
    assert d["status_code"] == 400
    assert d["context"] == {"key": "val"}


def test_config_errors():
    err = MissingConfigError("system.yaml")
    assert err.error_code == "missing_config_file"
    assert "system.yaml" in err.user_message
    assert "system.yaml.example" in err.actionable_hint

    err2 = InvalidConfigValueError("chunking.size", "-5", "must be >= 1")
    assert err2.error_code == "invalid_config_value"

    err3 = MissingSecretError("openai_api_key", "openai")
    assert err3.error_code == "missing_secret"
    assert "install.yaml" in err3.actionable_hint


def test_ingest_errors():
    assert EmptyContentError().error_code == "empty_content"
    assert ContentTooLargeError().error_code == "content_too_large"
    assert UnsupportedFormatError("xyz").error_code == "unsupported_format"
    assert CorruptMediaError("audio.mp3", "invalid header").error_code == "corrupt_media"

    lf = LargeFormatError("src_1", 60000, 50000)
    assert lf.source_uid == "src_1"
    assert lf.token_count == 60000
    assert lf.threshold == 50000
    assert lf.http_status == 422


def test_provider_errors():
    err1 = ProviderUnavailableError("ollama", "http://localhost:11434")
    assert err1.error_code == "provider_unavailable"
    assert err1.http_status == 503

    err2 = ModelNotFoundError("nomic-embed-text", "ollama")
    assert err2.error_code == "model_not_found"
    assert err2.http_status == 502

    err3 = ProviderTimeoutError("ollama", 180)
    assert err3.error_code == "provider_timeout"
    assert err3.http_status == 504

    err4 = StructuredOutputValidationError("qwen", "{invalid}", "JSONDecodeError")
    assert err4.error_code == "structured_output_validation_failed"


def test_resource_errors():
    nf = NotFoundError("Note", "note_123")
    assert nf.resource == "Note"
    assert nf.uid == "note_123"
    assert nf.error_code == "not_found"
    assert nf.http_status == 404

    cf = ConflictError("Source", "src_123", "already marked for deletion")
    assert cf.resource == "Source"
    assert cf.uid == "src_123"
    assert cf.error_code == "conflict"
    assert cf.http_status == 409

    cc = CandidateClaimedError("cand_1", "agent_alpha", 120)
    assert cc.error_code == "candidate_already_claimed"
    assert cc.context["claimed_by"] == "agent_alpha"
    assert cc.context["ttl_remaining_seconds"] == 120

    el = ExpiredLockError()
    assert el.error_code == "expired_candidate_lock"
    assert el.http_status == 409


def test_security_errors():
    pt = PathTraversalError("/etc/passwd")
    assert pt.error_code == "path_traversal_denied"
    assert pt.http_status == 403

    ssrf = SSRFBlockedError("http://169.254.169.254", "metadata endpoint")
    assert ssrf.error_code == "ssrf_blocked"
    assert ssrf.http_status == 403
