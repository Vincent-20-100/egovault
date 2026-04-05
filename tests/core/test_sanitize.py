# tests/core/test_sanitize.py
"""Tests for core.sanitize — redaction and error sanitizing."""

from core.sanitize import redact_sensitive, sanitize_error


class TestRedactSensitive:
    def test_redacts_openai_key(self):
        text = '{"api_key": "sk-abc123def456ghi789jkl012mno345pqr678"}'
        result = redact_sensitive(text)
        assert "sk-abc123" not in result
        assert "sk-***REDACTED***" in result

    def test_redacts_anthropic_key(self):
        text = "error: sk-ant-api03-abcdef1234567890abcdef1234567890 is invalid"
        result = redact_sensitive(text)
        assert "sk-ant-api03" not in result
        assert "sk-***REDACTED***" in result

    def test_redacts_openrouter_key(self):
        text = "key=sk-or-v1-abcdef1234567890abcdef"
        result = redact_sensitive(text)
        assert "sk-or-v1" not in result
        assert "sk-***REDACTED***" in result

    def test_redacts_json_key_fields(self):
        text = '{"openai_api_key": "my-secret-key-value", "name": "test"}'
        result = redact_sensitive(text)
        assert "my-secret-key-value" not in result
        assert '"name": "test"' in result

    def test_redacts_password_fields(self):
        text = '{"password": "hunter2", "user": "admin"}'
        result = redact_sensitive(text)
        assert "hunter2" not in result

    def test_preserves_normal_text(self):
        text = '{"query": "what is antifragility?", "mode": "chunks"}'
        assert redact_sensitive(text) == text

    def test_handles_none(self):
        assert redact_sensitive(None) is None

    def test_handles_empty_string(self):
        assert redact_sensitive("") == ""

    def test_no_double_redaction_key_in_json_field(self):
        text = '{"api_key": "sk-abc123def456ghi789jkl012mno345pqr678"}'
        result = redact_sensitive(text)
        assert result.count("REDACTED") == 1
        assert "sk-abc123" not in result


class TestSanitizeError:
    def test_strips_absolute_paths_unix(self):
        err = FileNotFoundError("/home/user/Documents/egovault-user/data/vault.db")
        result = sanitize_error(err)
        assert "/home/user" not in result
        assert "vault.db" in result

    def test_strips_absolute_paths_windows(self):
        err = FileNotFoundError("C:\\Users\\Vincent\\Documents\\egovault-user\\data\\vault.db")
        result = sanitize_error(err)
        assert "C:\\Users\\Vincent" not in result
        assert "vault.db" in result

    def test_strips_api_keys_from_error(self):
        err = RuntimeError("Auth failed with key sk-abc123def456ghi789jkl012mno345pqr678")
        result = sanitize_error(err)
        assert "sk-abc123" not in result
        assert "sk-***REDACTED***" in result

    def test_preserves_error_type_and_message(self):
        err = ValueError("invalid youtube url")
        result = sanitize_error(err)
        assert "ValueError" in result
        assert "invalid youtube url" in result
