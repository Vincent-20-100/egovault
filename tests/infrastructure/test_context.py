"""
Tests for infrastructure/context.py — build_context() factory.

Verifies that build_context() returns a valid VaultContext with correctly
typed fields. Providers are not called (no real Ollama/Anthropic needed).
"""

import pytest
from pathlib import Path

from core.context import VaultContext, EmbedFn, GenerateFn, WriteNoteFn
from infrastructure.vault_db import VaultDB


# ============================================================
# HELPERS
# ============================================================

def _make_settings_with_no_llm(tmp_settings):
    """Return settings with no anthropic_api_key (LLM not configured)."""
    # tmp_settings has no anthropic key by default
    return tmp_settings


def _make_settings_with_llm(tmp_settings):
    """Return a settings copy with a (fake) anthropic_api_key set."""
    # Rebuild install config with a fake key
    import copy
    settings = copy.deepcopy(tmp_settings)
    object.__setattr__(settings.install.providers, "anthropic_api_key", "sk-test-fake-key")
    return settings


# ============================================================
# _llm_is_configured helper
# ============================================================

def test_llm_is_not_configured_when_no_key(tmp_settings):
    from infrastructure.context import _llm_is_configured
    assert _llm_is_configured(tmp_settings) is False


def test_llm_is_configured_when_claude_with_key(tmp_settings):
    from infrastructure.context import _llm_is_configured
    settings = _make_settings_with_llm(tmp_settings)
    assert _llm_is_configured(settings) is True


def test_llm_is_not_configured_when_provider_is_not_claude(tmp_settings):
    from infrastructure.context import _llm_is_configured
    import copy
    settings = copy.deepcopy(tmp_settings)
    object.__setattr__(settings.install.providers, "anthropic_api_key", "sk-fake")
    object.__setattr__(settings.user.llm, "provider", "openai")
    assert _llm_is_configured(settings) is False


def test_llm_is_configured_true_for_ollama(tmp_settings):
    from core.config import LLMUserConfig
    from infrastructure.context import _llm_is_configured

    s = tmp_settings.model_copy(
        update={"user": tmp_settings.user.model_copy(
            update={"llm": LLMUserConfig(provider="ollama", model="qwen2.5:7b-instruct")}
        )}
    )
    assert _llm_is_configured(s) is True


# ============================================================
# build_context — field types and presence
# ============================================================

def test_build_context_returns_vault_context(tmp_settings):
    from infrastructure.context import build_context
    ctx = build_context(tmp_settings)
    assert isinstance(ctx, VaultContext)


def test_build_context_db_is_vault_db(tmp_settings):
    from infrastructure.context import build_context
    ctx = build_context(tmp_settings)
    assert isinstance(ctx.db, VaultDB)


def test_build_context_settings_is_same_object(tmp_settings):
    from infrastructure.context import build_context
    ctx = build_context(tmp_settings)
    assert ctx.settings is tmp_settings


def test_build_context_system_db_path_is_path(tmp_settings):
    from infrastructure.context import build_context
    ctx = build_context(tmp_settings)
    assert isinstance(ctx.system_db_path, Path)


def test_build_context_vault_path_is_path(tmp_settings):
    from infrastructure.context import build_context
    ctx = build_context(tmp_settings)
    assert isinstance(ctx.vault_path, Path)


def test_build_context_media_path_is_path(tmp_settings):
    from infrastructure.context import build_context
    ctx = build_context(tmp_settings)
    assert isinstance(ctx.media_path, Path)


def test_build_context_embed_is_callable(tmp_settings):
    from infrastructure.context import build_context
    ctx = build_context(tmp_settings)
    assert callable(ctx.embed)


def test_build_context_write_note_is_callable(tmp_settings):
    from infrastructure.context import build_context
    ctx = build_context(tmp_settings)
    assert callable(ctx.write_note)


def test_build_context_generate_is_none_when_no_llm(tmp_settings):
    from infrastructure.context import build_context
    ctx = build_context(tmp_settings)
    # tmp_settings has no anthropic_api_key
    assert ctx.generate is None


def test_build_context_generate_is_callable_when_llm_configured(tmp_settings):
    from infrastructure.context import build_context
    settings = _make_settings_with_llm(tmp_settings)
    ctx = build_context(settings)
    assert callable(ctx.generate)


# ============================================================
# build_context — schema bootstrap (all surfaces)
# ============================================================

def test_build_context_initializes_vault_schema(tmp_settings):
    """build_context() must leave the vault DB queryable for CLI/MCP, not only API."""
    from infrastructure.context import build_context
    from infrastructure.db import get_vault_connection
    build_context(tmp_settings)
    conn = get_vault_connection(tmp_settings.vault_db_path)
    conn.execute("SELECT * FROM sources LIMIT 0")
    conn.execute("SELECT * FROM notes LIMIT 0")
    conn.execute("SELECT * FROM chunks LIMIT 0")
    conn.close()


def test_build_context_initializes_system_schema(tmp_settings):
    from infrastructure.context import build_context
    from infrastructure.db import get_system_connection
    build_context(tmp_settings)
    conn = get_system_connection(tmp_settings.system_db_path)
    conn.execute("SELECT * FROM jobs LIMIT 0")
    conn.close()


# ============================================================
# build_context — path derivation matches settings
# ============================================================

def test_build_context_vault_path_matches_settings(tmp_settings):
    from infrastructure.context import build_context
    ctx = build_context(tmp_settings)
    assert ctx.vault_path == tmp_settings.vault_path


def test_build_context_media_path_matches_settings(tmp_settings):
    from infrastructure.context import build_context
    ctx = build_context(tmp_settings)
    assert ctx.media_path == tmp_settings.media_path


def test_build_context_system_db_path_matches_settings(tmp_settings):
    from infrastructure.context import build_context
    ctx = build_context(tmp_settings)
    assert ctx.system_db_path == tmp_settings.system_db_path
