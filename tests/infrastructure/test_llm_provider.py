"""Tests for LLM provider — mocks the Anthropic SDK at module level."""

import sys
from unittest.mock import patch, MagicMock

import pytest


# Inject a fake anthropic module so late imports succeed without the real package
if "anthropic" not in sys.modules:
    sys.modules["anthropic"] = MagicMock()


def test_generate_note_content_calls_anthropic(tmp_settings):
    from infrastructure.llm_provider import generate_note_content

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text='''{
        "title": "Bitcoin et la décentralisation",
        "docstring": "Bitcoin remet en question le monopole étatique sur la monnaie.",
        "body": "## Idée principale\\n\\nBitcoin est un réseau décentralisé.",
        "note_type": "synthese",
        "source_type": "youtube",
        "tags": ["bitcoin", "decentralisation"],
        "url": null
    }''')]

    with patch("anthropic.Anthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = mock_message

        result = generate_note_content(
            source_content="Bitcoin is a decentralized currency.",
            source_metadata={"title": "Bitcoin talk", "source_type": "youtube"},
            template_name="standard",
            settings=tmp_settings,
        )

    from core.schemas import NoteContentInput
    assert isinstance(result, NoteContentInput)
    assert result.title == "Bitcoin et la décentralisation"
    assert "bitcoin" in result.tags


def test_generate_note_content_retries_on_invalid_json(tmp_settings):
    from infrastructure.llm_provider import generate_note_content

    good_json = '''{
        "title": "Titre valide ok",
        "docstring": "Un docstring valide.",
        "body": "## Corps\\n\\nContenu du corps.",
        "note_type": "synthese",
        "source_type": "youtube",
        "tags": ["test"],
        "url": null
    }'''

    call_count = 0
    def fake_create(**kwargs):
        nonlocal call_count
        call_count += 1
        msg = MagicMock()
        if call_count == 1:
            msg.content = [MagicMock(text="not valid json")]
        else:
            msg.content = [MagicMock(text=good_json)]
        return msg

    with patch("anthropic.Anthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.side_effect = fake_create

        result = generate_note_content(
            source_content="Test content here.",
            source_metadata={"title": "Test", "source_type": "youtube"},
            template_name="standard",
            settings=tmp_settings,
        )

    assert call_count == 2  # one retry
    assert result.title == "Titre valide ok"


def test_generate_note_content_raises_after_max_retries(tmp_settings):
    from infrastructure.llm_provider import generate_note_content

    bad_msg = MagicMock()
    bad_msg.content = [MagicMock(text="invalid json always")]

    with patch("anthropic.Anthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = bad_msg

        with pytest.raises(ValueError, match="LLM failed to produce valid NoteContentInput"):
            generate_note_content(
                source_content="Test.",
                source_metadata={"title": "Test", "source_type": "youtube"},
                template_name="standard",
                settings=tmp_settings,
            )


def test_anthropic_auth_error_does_not_leak_key(monkeypatch):
    """Auth errors from the LLM SDK must not contain the API key."""
    from infrastructure.llm_provider import _generate_anthropic

    settings = MagicMock()
    settings.install.providers.anthropic_api_key = "sk-ant-api03-realkey123456789012345678901234567890"
    settings.system.llm.max_retries = 0
    settings.user.llm.model = "claude-sonnet-4-6"

    class FakeAPIError(Exception):
        pass

    def mock_anthropic_constructor(api_key):
        client = MagicMock()
        client.messages.create.side_effect = FakeAPIError(
            f"Invalid API key: sk-ant-api03-realkey123456789012345678901234567890"
        )
        return client

    monkeypatch.setattr("anthropic.Anthropic", mock_anthropic_constructor)

    with pytest.raises(Exception) as exc_info:
        _generate_anthropic("test", {}, "standard", settings)

    error_msg = str(exc_info.value)
    assert "sk-ant-api03-realkey" not in error_msg


def test_generate_note_content_unknown_provider_raises(tmp_settings):
    from infrastructure.llm_provider import generate_note_content
    from core.config import LLMUserConfig

    bad_settings = tmp_settings.model_copy(
        update={"user": tmp_settings.user.model_copy(
            update={"llm": LLMUserConfig(provider="unknown", model="x")}
        )}
    )
    with pytest.raises(NotImplementedError, match="LLM provider 'unknown'"):
        generate_note_content(
            source_content="test",
            source_metadata={},
            template_name="standard",
            settings=bad_settings,
        )


def test_get_context_window_returns_explicit_override():
    from infrastructure.llm_provider import get_context_window
    settings = MagicMock()
    settings.system.llm.context_window = 32000
    assert get_context_window(settings) == 32000


def test_get_context_window_returns_claude_default_when_unset():
    from infrastructure.llm_provider import get_context_window
    settings = MagicMock()
    settings.system.llm.context_window = None
    settings.user.llm.provider = "claude"
    settings.user.llm.model = "claude-opus-4-6"
    assert get_context_window(settings) == 200_000


def test_get_context_window_returns_conservative_fallback_for_unknown_provider():
    from infrastructure.llm_provider import get_context_window
    settings = MagicMock()
    settings.system.llm.context_window = None
    settings.user.llm.provider = "unknown"
    settings.user.llm.model = "??"
    assert get_context_window(settings) == 8192
