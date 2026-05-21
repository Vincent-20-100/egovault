"""
LLM provider with structured output and validation retry.
"""

import json
import re
import unicodedata
from pathlib import Path

import requests
from pydantic import ValidationError

from core.config import Settings
from core.schemas import NoteContentInput


def _slugify_tag(tag: str) -> str:
    """Normalize one LLM-emitted tag to satisfy NoteContentInput's validator:
    lowercase + ASCII (no accents) + kebab-case [a-z0-9-], no leading/trailing
    hyphens, no spaces or underscores."""
    s = unicodedata.normalize("NFKD", tag).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _normalize_tags(tags: list[str]) -> list[str]:
    """Slugify each tag and drop empties; preserve order, dedupe."""
    out: list[str] = []
    seen: set[str] = set()
    for t in tags:
        n = _slugify_tag(t)
        if n and n not in seen:
            out.append(n)
            seen.add(n)
    return out


def generate_note_content(
    source_content: str,
    source_metadata: dict,
    template_name: str,
    settings: Settings,
) -> NoteContentInput:
    """
    Call the configured LLM to generate NoteContentInput from source content.
    Retries on validation failure up to the configured maximum.
    Raises ValueError if all retries are exhausted without a valid result.
    """
    provider = settings.user.llm.provider
    if provider == "claude":
        return _generate_anthropic(source_content, source_metadata, template_name, settings)
    elif provider == "openai":
        raise NotImplementedError(
            "LLM provider 'openai' is not implemented in v1. "
            "Configure provider: claude in user.yaml."
        )
    elif provider == "ollama":
        return _generate_ollama(source_content, source_metadata, template_name, settings)
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
) -> NoteContentInput:
    import anthropic

    template = _load_template(template_name)
    api_key = settings.install.providers.anthropic_api_key
    client = anthropic.Anthropic(api_key=api_key)
    max_retries = settings.system.llm.max_retries
    user_message = _build_user_message(source_content, source_metadata, template)
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
                system=template["system_prompt"] + error_context,
                messages=[{"role": "user", "content": user_message}],
            )
        except Exception as e:
            from core.sanitize import sanitize_error
            raise RuntimeError(sanitize_error(e)) from None
        raw = message.content[0].text
        try:
            data = json.loads(raw)
            if isinstance(data.get("tags"), list):
                data["tags"] = _normalize_tags(data["tags"])
            return NoteContentInput(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e

    raise ValueError(
        f"LLM failed to produce valid NoteContentInput after {max_retries + 1} attempts. "
        f"Last error: {last_error}"
    )


def _generate_ollama(
    source_content: str,
    source_metadata: dict,
    template_name: str,
    settings: Settings,
) -> NoteContentInput:
    template = _load_template(template_name)
    base_url = settings.install.providers.ollama_base_url
    num_ctx = settings.install.providers.ollama_num_ctx
    timeout_s = settings.install.providers.ollama_timeout_s
    max_retries = settings.system.llm.max_retries
    user_message = _build_user_message(source_content, source_metadata, template)
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        error_context = (
            f"\n\nPrevious attempt failed with: {last_error}. "
            "Fix the JSON and try again."
            if last_error else ""
        )
        try:
            response = requests.post(
                f"{base_url}/api/chat",
                json={
                    "model": settings.user.llm.model,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2, "num_ctx": num_ctx},
                    "messages": [
                        {"role": "system",
                         "content": template["system_prompt"] + error_context},
                        {"role": "user", "content": user_message},
                    ],
                },
                timeout=timeout_s,
            )
            response.raise_for_status()
        except Exception as e:
            from core.sanitize import sanitize_error
            raise RuntimeError(sanitize_error(e)) from None
        try:
            raw = response.json()["message"]["content"]
            data = json.loads(raw)
            if isinstance(data.get("tags"), list):
                data["tags"] = _normalize_tags(data["tags"])
            return NoteContentInput(**data)
        except (json.JSONDecodeError, ValidationError, KeyError) as e:
            last_error = e

    raise ValueError(
        f"LLM failed to produce valid NoteContentInput after {max_retries + 1} attempts. "
        f"Last error: {last_error}"
    )
