"""
LLM provider with structured output and validation retry.
"""

import json
import urllib.request
from pathlib import Path

from pydantic import ValidationError

from core.config import Settings
from core.schemas import NoteContentInput


def generate_note_content(
    source_content: str,
    source_metadata: dict,
    template_name: str,
    settings: Settings,
    system_prompt_extra: str | None = None,
) -> NoteContentInput:
    """
    Call the configured LLM to generate NoteContentInput from source content.
    Retries on validation failure up to the configured maximum.
    Raises ValueError if all retries are exhausted without a valid result.
    """
    provider = settings.user.llm.provider
    if provider == "claude":
        return _generate_anthropic(
            source_content, source_metadata, template_name, settings, system_prompt_extra
        )
    elif provider == "openai":
        raise NotImplementedError(
            "LLM provider 'openai' is not implemented in v1. "
            "Configure provider: claude in user.yaml."
        )
    elif provider == "ollama":
        raise NotImplementedError(
            "LLM provider 'ollama' is not implemented in v1. "
            "Configure provider: claude in user.yaml."
        )
    else:
        raise NotImplementedError(
            f"LLM provider '{provider}' is not supported. "
            "Supported in v1: claude"
        )


def _load_template(template_name: str) -> dict:
    """Load generation template by name."""
    import yaml
    template_path = Path(__file__).parent.parent / "config" / "templates" / "generation" / f"{template_name}.yaml"
    if not template_path.exists():
        raise FileNotFoundError(
            f"Generation template '{template_name}' not found at {template_path}."
        )
    with open(template_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _build_user_message(source_content: str, source_metadata: dict, template: dict) -> str:
    meta_lines = "\n".join(f"- {k}: {v}" for k, v in source_metadata.items() if v)
    return (
        f"Source metadata:\n{meta_lines}\n\n"
        f"Output schema:\n{template.get('output_schema', '')}\n\n"
        f"Source content:\n{source_content}"
    )


def _generate_anthropic(
    source_content: str,
    source_metadata: dict,
    template_name: str,
    settings: Settings,
    system_prompt_extra: str | None = None,
) -> NoteContentInput:
    import anthropic

    template = _load_template(template_name)
    api_key = settings.install.providers.anthropic_api_key
    client = anthropic.Anthropic(api_key=api_key)
    max_retries = settings.system.llm.max_retries
    user_message = _build_user_message(source_content, source_metadata, template)
    base_system = template["system_prompt"]
    if system_prompt_extra:
        base_system = f"{base_system}\n\n---\n\n{system_prompt_extra}"
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        error_context = (
            f"\n\nPrevious attempt failed with: {last_error}. "
            "Fix the JSON and try again."
            if last_error else ""
        )
        try:
            message = client.messages.create(
                model=settings.user.llm.model,
                max_tokens=4096,
                system=base_system + error_context,
                messages=[{"role": "user", "content": user_message}],
            )
        except Exception as e:
            from core.sanitize import sanitize_error
            raise RuntimeError(sanitize_error(e)) from None
        raw = message.content[0].text
        try:
            data = json.loads(raw)
            return NoteContentInput(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e

    raise ValueError(
        f"LLM failed to produce valid NoteContentInput after {max_retries + 1} attempts. "
        f"Last error: {last_error}"
    )


# Hardcoded mapping for known API providers (max input window).
_KNOWN_CONTEXT_WINDOWS: dict[tuple[str, str], int] = {
    ("claude", "claude-opus-4-6"): 200_000,
    ("claude", "claude-sonnet-4-6"): 200_000,
    ("claude", "claude-haiku-4-5-20251001"): 200_000,
    ("openai", "gpt-4"): 128_000,
    ("openai", "gpt-4o"): 128_000,
}

_FALLBACK_CONTEXT_WINDOW = 8192


def get_context_window(settings: Settings) -> int:
    """Resolve the LLM context window in tokens.

    Resolution order:
    1. settings.system.llm.context_window if set
    2. Provider-specific lookup (Ollama API call or hardcoded map)
    3. Conservative fallback (8192)
    """
    explicit = settings.system.llm.context_window
    if explicit is not None:
        return explicit

    provider = settings.user.llm.provider
    model = settings.user.llm.model

    if provider == "ollama":
        try:
            return _fetch_ollama_context_length(settings, model)
        except Exception:
            return _FALLBACK_CONTEXT_WINDOW

    return _KNOWN_CONTEXT_WINDOWS.get((provider, model), _FALLBACK_CONTEXT_WINDOW)


def _fetch_ollama_context_length(settings: Settings, model: str) -> int:
    """Call Ollama /api/show to read model_info.context_length."""
    base = settings.install.providers.ollama_base_url.rstrip("/")
    req = urllib.request.Request(
        f"{base}/api/show",
        data=json.dumps({"name": model}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    info = data.get("model_info", {})
    for key, value in info.items():
        if key.endswith(".context_length") and isinstance(value, int):
            return value
    raise ValueError("context_length not found in /api/show response")
