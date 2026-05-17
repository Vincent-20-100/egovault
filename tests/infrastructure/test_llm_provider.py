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


def _ollama_settings(tmp_settings):
    from core.config import LLMUserConfig
    return tmp_settings.model_copy(
        update={"user": tmp_settings.user.model_copy(
            update={"llm": LLMUserConfig(provider="ollama", model="qwen2.5:7b-instruct")}
        )}
    )


def _ollama_response(text):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"message": {"role": "assistant", "content": text}}
    return resp


def test_generate_note_content_ollama_happy_path(tmp_settings):
    from infrastructure.llm_provider import generate_note_content
    from core.schemas import NoteContentInput

    good = '''{
        "title": "Decentralisation et resilience",
        "docstring": "Les systemes decentralises resistent mieux aux pannes.",
        "body": "## Idee\\n\\nPas de point unique de defaillance.",
        "note_type": "synthese",
        "source_type": "youtube",
        "tags": ["decentralisation"],
        "url": null
    }'''

    with patch("infrastructure.llm_provider.requests.post",
               return_value=_ollama_response(good)) as mock_post:
        result = generate_note_content(
            source_content="Les systemes decentralises...",
            source_metadata={"title": "Test", "source_type": "youtube"},
            template_name="standard",
            settings=_ollama_settings(tmp_settings),
        )

    assert isinstance(result, NoteContentInput)
    assert result.title == "Decentralisation et resilience"
    assert mock_post.call_count == 1


def test_ollama_malformed_200_body_retries_then_raises(tmp_settings):
    from infrastructure.llm_provider import generate_note_content

    bad = MagicMock()
    bad.raise_for_status.return_value = None
    bad.json.return_value = {"error": "model 'x' not found"}  # no 'message' key, HTTP 200
    with patch("infrastructure.llm_provider.requests.post", return_value=bad):
        with pytest.raises(ValueError, match="LLM failed to produce valid NoteContentInput"):
            generate_note_content(
                "c", {"title": "T", "source_type": "youtube"}, "standard",
                _ollama_settings(tmp_settings),
            )


def test_ollama_retries_on_invalid_then_succeeds(tmp_settings):
    from infrastructure.llm_provider import generate_note_content

    good = '''{
        "title": "Titre valide ok",
        "docstring": "Un docstring valide.",
        "body": "## Corps\\n\\nContenu.",
        "note_type": "synthese",
        "source_type": "youtube",
        "tags": ["test"],
        "url": null
    }'''
    calls = {"n": 0, "payloads": []}

    def fake_post(*a, **k):
        calls["n"] += 1
        calls["payloads"].append(k["json"])
        return _ollama_response("not json" if calls["n"] == 1 else good)

    with patch("infrastructure.llm_provider.requests.post", side_effect=fake_post):
        result = generate_note_content(
            "c", {"title": "T", "source_type": "youtube"}, "standard",
            _ollama_settings(tmp_settings),
        )
    assert calls["n"] == 2
    assert result.title == "Titre valide ok"
    assert "Previous attempt failed" in calls["payloads"][1]["messages"][0]["content"]


def test_ollama_raises_after_max_retries(tmp_settings):
    from infrastructure.llm_provider import generate_note_content

    with patch("infrastructure.llm_provider.requests.post",
               return_value=_ollama_response("invalid always")) as mock_post:
        with pytest.raises(ValueError, match="LLM failed to produce valid NoteContentInput"):
            generate_note_content(
                "c", {"title": "T", "source_type": "youtube"}, "standard",
                _ollama_settings(tmp_settings),
            )
    assert mock_post.call_count == 3


def test_ollama_down_raises_sanitized_runtime_error(tmp_settings):
    from infrastructure.llm_provider import generate_note_content
    import requests

    def boom(*a, **k):
        raise requests.ConnectionError("connection refused to http://localhost:11434")

    with patch("infrastructure.llm_provider.requests.post", side_effect=boom):
        with pytest.raises(RuntimeError) as exc:
            generate_note_content(
                "c", {"title": "T", "source_type": "youtube"}, "standard",
                _ollama_settings(tmp_settings),
            )
    assert "Traceback" not in str(exc.value)


def test_ollama_payload_shape(tmp_settings):
    from infrastructure.llm_provider import generate_note_content

    good = '''{"title":"Titre ok valide","docstring":"D.","body":"## Body\\n\\nContent here",
        "note_type":"synthese","source_type":"youtube","tags":["t"],"url":null}'''
    with patch("infrastructure.llm_provider.requests.post",
               return_value=_ollama_response(good)) as mp:
        generate_note_content(
            "c", {"title": "T", "source_type": "youtube"}, "standard",
            _ollama_settings(tmp_settings),
        )
    payload = mp.call_args.kwargs["json"]
    assert payload["format"] == "json"
    assert payload["model"] == "qwen2.5:7b-instruct"
    assert payload["stream"] is False
    assert payload["messages"][0]["role"] == "system"
    assert mp.call_args.kwargs["timeout"] == 180


def test_ollama_does_not_enforce_taxonomy_context(tmp_settings):
    from infrastructure.llm_provider import generate_note_content

    # note_type 'totally-unknown' is NOT in tmp_settings taxonomy
    payload = '''{
        "title": "Titre hors taxo ok",
        "docstring": "D.",
        "body": "## Body section\\n\\nContent text here",
        "note_type": "totally-unknown",
        "source_type": "youtube",
        "tags": ["t"],
        "url": null
    }'''
    with patch("infrastructure.llm_provider.requests.post",
               return_value=_ollama_response(payload)):
        result = generate_note_content(
            "c", {"title": "T", "source_type": "youtube"}, "standard",
            _ollama_settings(tmp_settings),
        )
    assert result.note_type == "totally-unknown"  # same as claude: no context = no enforcement


def test_ollama_http_error_model_not_pulled_sanitized(tmp_settings):
    from infrastructure.llm_provider import generate_note_content
    import requests

    def http_404(*a, **k):
        raise requests.HTTPError("404 Client Error: Not Found - model 'qwen2.5:7b-instruct' not found")

    with patch("infrastructure.llm_provider.requests.post", side_effect=http_404):
        with pytest.raises(RuntimeError) as exc:
            generate_note_content(
                "c", {"title": "T", "source_type": "youtube"}, "standard",
                _ollama_settings(tmp_settings),
            )
    assert "Traceback" not in str(exc.value)
