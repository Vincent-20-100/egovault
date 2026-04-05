# EgoVault — Plan 3: Workflows + MCP

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the three ingestion workflows and the FastMCP server that routes all tools to external clients.

**Architecture:** Workflows orchestrate tool calls from Plan 2 (no business logic of their own). A new `infrastructure/llm_provider.py` handles LLM calls for note generation. `mcp/server.py` is a thin FastMCP routing layer — it imports tools and calls them, nothing more.

**Tech Stack:** Python 3.10+, mcp[cli]>=1.0, anthropic>=0.40, pypdf>=4.0, FastMCP

**Prerequisite:** Plan 2 (Tools) complete — all `tools/` functions implemented and tested.

**Spec:** `docs/specs/2026-03-25-egovault-v2-architecture-design.md` sections 5.4, 6.1, 7.0

---

## Part 0 — Scope

This plan covers:
- `pyproject.toml` — add mcp, anthropic, pypdf dependencies
- `infrastructure/db.py` — add `update_source_transcript()`
- `core/errors.py` — `LargeFormatError` exception
- `config/templates/generation/standard.yaml` — default generation template
- `infrastructure/llm_provider.py` — LLM client (Anthropic v1, stubs for others)
- `workflows/ingest_youtube.py` — full YouTube pipeline
- `workflows/ingest_audio.py` — full audio/video pipeline
- `workflows/ingest_pdf.py` — PDF/book pipeline
- `mcp/server.py` — FastMCP routing layer

**Not in this plan:** vault sync watcher, re-embedding worker, frontend, api/ (all future chantiers per spec section 7)

---

## Task 1: Prerequisites — Dependencies + DB helper

**Files:**
- Modify: `pyproject.toml`
- Modify: `infrastructure/db.py`
- Modify: `tests/infrastructure/test_db.py`

- [ ] **Step 1: Write the failing test for update_source_transcript**

Add to `tests/infrastructure/test_db.py`:

```python
def test_update_source_transcript(tmp_db):
    from infrastructure.db import insert_source, update_source_transcript, get_source
    from core.schemas import Source
    source = Source(
        uid="src-1", slug="src-one", source_type="youtube",
        status="raw", date_added="2026-03-26",
    )
    insert_source(tmp_db, source)
    update_source_transcript(tmp_db, "src-1", "full transcript text here")
    updated = get_source(tmp_db, "src-1")
    assert updated.transcript == "full transcript text here"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py::test_update_source_transcript -v
```

Expected: FAIL with `ImportError: cannot import name 'update_source_transcript'`

- [ ] **Step 3: Add update_source_transcript to infrastructure/db.py**

Insert after the `update_source_status` function (around line 165):

```python
def update_source_transcript(db_path: Path, uid: str, transcript: str) -> None:
    conn = get_connection(db_path)
    conn.execute("UPDATE sources SET transcript = ? WHERE uid = ?", (transcript, uid))
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py::test_update_source_transcript -v
```

Expected: PASS

- [ ] **Step 5: Add mcp, anthropic, pypdf to pyproject.toml**

Replace the `dependencies` block in `pyproject.toml`:

```toml
dependencies = [
    "pydantic>=2.0",
    "PyYAML>=6.0",
    "sqlite-vec>=0.1.0",
    "requests>=2.31",
    "faster-whisper>=1.2.0",
    "yt-dlp>=2026.3.0",
    "youtube-transcript-api>=1.2",
    "mcp[cli]>=1.0",
    "anthropic>=0.40",
    "pypdf>=4.0",
]
```

- [ ] **Step 6: Install new dependencies**

```bash
.venv/Scripts/python -m pip install "mcp[cli]>=1.0" "anthropic>=0.40" "pypdf>=4.0"
```

Expected: packages installed without error

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml infrastructure/db.py tests/infrastructure/test_db.py
git commit -m "feat: add mcp/anthropic/pypdf deps + update_source_transcript"
```

---

## Task 2: core/errors.py — LargeFormatError

**Files:**
- Create: `core/errors.py`
- Create: `tests/core/test_errors.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/core/test_errors.py`:

```python
from core.errors import LargeFormatError


def test_large_format_error_is_exception():
    err = LargeFormatError(source_uid="uid-1", token_count=75000, threshold=50000)
    assert isinstance(err, Exception)
    assert err.source_uid == "uid-1"
    assert err.token_count == 75000
    assert err.threshold == 50000


def test_large_format_error_message():
    err = LargeFormatError(source_uid="uid-1", token_count=75000, threshold=50000)
    msg = str(err)
    assert "uid-1" in msg
    assert "75000" in msg
    assert "50000" in msg


def test_large_format_error_can_be_raised_and_caught():
    import pytest
    with pytest.raises(LargeFormatError) as exc_info:
        raise LargeFormatError(source_uid="uid-2", token_count=60000, threshold=50000)
    assert exc_info.value.source_uid == "uid-2"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/core/test_errors.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'core.errors'`

- [ ] **Step 3: Implement core/errors.py**

Create `core/errors.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/core/test_errors.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add core/errors.py tests/core/test_errors.py
git commit -m "feat: LargeFormatError for oversized source handling"
```

---

## Task 3: config/templates/generation/standard.yaml

**Files:**
- Create: `config/templates/generation/standard.yaml`
- Create: `tests/core/test_generation_template.py`

No failing test needed for YAML file creation — test is about loading and validating.

- [ ] **Step 1: Create config/templates/generation/ directory and standard.yaml**

Create `config/templates/generation/standard.yaml`:

```yaml
# ============================================================
# GENERATION TEMPLATE: standard
# Default template — balanced extraction + personal synthesis
# ============================================================
name: standard
description: "Balanced extraction from a source with personal analytical synthesis"

system_prompt: |
  You are a knowledge synthesis assistant helping build a personal knowledge vault.
  Your task: read the provided source content and generate a structured note in JSON.

  CRITICAL RULES:
  - Return ONLY valid JSON matching the schema below. No markdown fences, no commentary.
  - The note must be in the content_language specified below (default: French).
  - tags: kebab-case, lowercase, no accents, no spaces (e.g. "bitcoin", "theorie-des-jeux").
  - note_type: one of the allowed types listed below.
  - docstring: 1-3 sentences maximum. State: what the source says, why it matters, what the key thesis is.
  - body: structured Markdown with ## sections. Include key ideas, quotes (as > blockquotes), and your synthesis.
  - Do NOT set generation_template — it is set by the system, not you.
  - Do NOT set rating — it is set by the user, not you.

output_schema: |
  {
    "title": "string (3-200 chars)",
    "docstring": "string (max 300 chars, 1-3 sentences: what/why/thesis)",
    "body": "string (Markdown, min 10 chars, ## sections encouraged)",
    "note_type": "string (one of the allowed taxonomy values)",
    "source_type": "string (one of the allowed taxonomy values)",
    "tags": ["list of 1-10 kebab-case strings"],
    "url": null
  }
```

- [ ] **Step 2: Write the failing test for template loading**

Create `tests/core/test_generation_template.py`:

```python
import pytest
import yaml
from pathlib import Path


def test_standard_template_exists():
    template_path = Path("config/templates/generation/standard.yaml")
    assert template_path.exists(), "standard.yaml must exist"


def test_standard_template_has_required_keys():
    template_path = Path("config/templates/generation/standard.yaml")
    with open(template_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "name" in data
    assert "system_prompt" in data
    assert "output_schema" in data
    assert data["name"] == "standard"


def test_standard_template_system_prompt_non_empty():
    template_path = Path("config/templates/generation/standard.yaml")
    with open(template_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert len(data["system_prompt"].strip()) > 50
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/core/test_generation_template.py -v
```

Expected: 3 PASSED (template already created in step 1)

- [ ] **Step 4: Commit**

```bash
git add config/templates/generation/standard.yaml tests/core/test_generation_template.py
git commit -m "feat: standard generation template YAML"
```

---

## Task 4: infrastructure/llm_provider.py — LLM client

**Files:**
- Create: `infrastructure/llm_provider.py`
- Create: `tests/infrastructure/test_llm_provider.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/infrastructure/test_llm_provider.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_llm_provider.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'infrastructure.llm_provider'`

- [ ] **Step 3: Check that LLMUserConfig is accessible (needed by test)**

Verify `core/config.py` exports `LLMUserConfig`. Run:

```bash
.venv/Scripts/python -c "from core.config import LLMUserConfig; print('ok')"
```

If this fails, find the LLM config class name in `core/config.py` and update the test import accordingly before continuing.

- [ ] **Step 4: Implement infrastructure/llm_provider.py**

Create `infrastructure/llm_provider.py`:

```python
"""
LLM provider for EgoVault v2.

Dispatches to Anthropic (v1). OpenAI and Ollama raise NotImplementedError.
Handles Pydantic validation retries (max_retries from system config).
"""

import json
from pathlib import Path

from core.config import Settings
from core.schemas import NoteContentInput


def generate_note_content(
    source_content: str,
    source_metadata: dict,
    template_name: str,
    settings: Settings,
) -> NoteContentInput:
    """
    Call the configured LLM to generate NoteContentInput from source content.
    Loads generation template YAML from config/templates/generation/{template_name}.yaml.
    Retries up to settings.system.llm.max_retries times on validation failure.
    Raises ValueError if max_retries exceeded without a valid result.
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
    """Load generation template YAML from config/templates/generation/."""
    import yaml
    template_path = Path("config/templates/generation") / f"{template_name}.yaml"
    if not template_path.exists():
        raise FileNotFoundError(
            f"Generation template '{template_name}' not found at {template_path}. "
            "Ensure the template name is in system.yaml:taxonomy.generation_templates "
            "and the corresponding .yaml file exists."
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
        message = client.messages.create(
            model=settings.user.llm.model,
            max_tokens=4096,
            system=template["system_prompt"] + error_context,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = message.content[0].text
        try:
            data = json.loads(raw)
            return NoteContentInput(**data)
        except (json.JSONDecodeError, Exception) as e:
            last_error = e

    raise ValueError(
        f"LLM failed to produce valid NoteContentInput after {max_retries + 1} attempts. "
        f"Last error: {last_error}"
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_llm_provider.py -v
```

Expected: 4 PASSED

- [ ] **Step 6: Commit**

```bash
git add infrastructure/llm_provider.py tests/infrastructure/test_llm_provider.py
git commit -m "feat: LLM provider (Anthropic v1) with retry logic"
```

---

## Task 5: workflows/ingest_youtube.py

**Files:**
- Modify: `workflows/ingest_youtube.py`
- Modify: `tests/workflows/test_ingest_youtube.py`

- [ ] **Step 1: Write the failing tests**

Replace `tests/workflows/test_ingest_youtube.py` with:

```python
import pytest
from unittest.mock import patch, MagicMock
from core.schemas import SubtitleResult, ChunkResult, Source
from core.errors import LargeFormatError


def _make_subtitle_result(text="Hello world transcript here."):
    return SubtitleResult(text=text, language="fr", source="subtitles")


def _make_chunk(uid="c1", pos=0, text="chunk content here"):
    return ChunkResult(uid=uid, position=pos, content=text, token_count=3)


def test_ingest_youtube_returns_source(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube

    # Override settings to point to tmp_db
    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )

    with patch("workflows.ingest_youtube.fetch_subtitles", return_value=_make_subtitle_result()), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=[0.1] * 768):

        result = ingest_youtube("https://youtube.com/watch?v=dQw4w9WgXcQ", settings)

    assert isinstance(result, Source)
    assert result.status == "rag_ready"
    assert result.source_type == "youtube"


def test_ingest_youtube_status_transitions(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube
    from infrastructure.db import get_source

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )

    with patch("workflows.ingest_youtube.fetch_subtitles", return_value=_make_subtitle_result()), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=[0.1] * 768):

        result = ingest_youtube("https://youtube.com/watch?v=abc123", settings)

    stored = get_source(tmp_db, result.uid)
    assert stored.status == "rag_ready"
    assert stored.transcript == "Hello world transcript here."


def test_ingest_youtube_chunks_stored(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube
    from infrastructure.db import get_connection

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    chunks = [_make_chunk("c1", 0, "chunk one content"), _make_chunk("c2", 1, "chunk two content")]

    with patch("workflows.ingest_youtube.fetch_subtitles", return_value=_make_subtitle_result()), \
         patch("workflows.ingest_youtube.chunk_text", return_value=chunks), \
         patch("workflows.ingest_youtube.embed_text", return_value=[0.1] * 768):

        result = ingest_youtube("https://youtube.com/watch?v=xyz", settings)

    conn = get_connection(tmp_db)
    rows = conn.execute("SELECT * FROM chunks WHERE source_uid = ?", (result.uid,)).fetchall()
    conn.close()
    assert len(rows) == 2


def test_ingest_youtube_raises_large_format_error(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    # 50001 words > threshold of 50000
    big_text = " ".join(["word"] * 50001)

    with patch("workflows.ingest_youtube.fetch_subtitles",
               return_value=SubtitleResult(text=big_text, language="fr", source="subtitles")), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=[0.1] * 768):

        with pytest.raises(LargeFormatError) as exc_info:
            ingest_youtube("https://youtube.com/watch?v=big", settings)

    assert exc_info.value.source_uid is not None
    assert exc_info.value.token_count > 50000


def test_ingest_youtube_source_stays_rag_ready_after_large_format(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube
    from infrastructure.db import get_source

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    big_text = " ".join(["word"] * 50001)
    source_uid_holder = {}

    with patch("workflows.ingest_youtube.fetch_subtitles",
               return_value=SubtitleResult(text=big_text, language="fr", source="subtitles")), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=[0.1] * 768):

        with pytest.raises(LargeFormatError) as exc_info:
            ingest_youtube("https://youtube.com/watch?v=big2", settings)
        source_uid_holder["uid"] = exc_info.value.source_uid

    stored = get_source(tmp_db, source_uid_holder["uid"])
    assert stored.status == "rag_ready"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/workflows/test_ingest_youtube.py -v
```

Expected: FAIL with `ImportError` or `NotImplementedError` from the stub

- [ ] **Step 3: Implement workflows/ingest_youtube.py**

Replace `workflows/ingest_youtube.py` with:

```python
"""
YouTube ingestion workflow.

Pipeline:
  fetch_subtitles → chunk_text → embed_chunks → [LLM → create_note → embed_note]

The LLM + note steps are skipped if:
  - No LLM configured (LLM-free mode) → source stays rag_ready
  - Source exceeds large_format_threshold_tokens → LargeFormatError raised

Status transitions managed here:
  raw → transcribing → text_ready → embedding → rag_ready [→ pre_vaulted → vaulted]
"""

import re
from datetime import date

from core.config import Settings
from core.errors import LargeFormatError
from core.schemas import Source
from core.uid import generate_uid, make_unique_slug
from infrastructure.db import (
    get_source,
    insert_chunk_embeddings,
    insert_chunks,
    insert_source,
    list_sources_by_status,
    update_source_status,
    update_source_transcript,
)
from tools.media.fetch_subtitles import fetch_subtitles
from tools.text.chunk import chunk_text
from tools.text.embed import embed_text


def _extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL for slug generation."""
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else "unknown"


def ingest_youtube(url: str, settings: Settings) -> Source:
    """
    Run the full YouTube ingestion pipeline.
    Returns the Source record at rag_ready status.
    Raises LargeFormatError if source exceeds token threshold.
    Human validation of NoteContentInput is required before DB write (not in this function).
    """
    db = settings.db_path
    today = date.today().isoformat()
    source_uid = generate_uid()
    video_id = _extract_video_id(url)

    # Collect existing slugs for collision resolution
    from infrastructure.db import get_connection
    conn = get_connection(db)
    existing_slugs = {row[0] for row in conn.execute("SELECT slug FROM sources").fetchall()}
    conn.close()

    slug = make_unique_slug(f"youtube-{video_id}", existing_slugs)

    source = Source(
        uid=source_uid,
        slug=slug,
        source_type="youtube",
        status="raw",
        url=url,
        date_added=today,
    )
    insert_source(db, source)

    # Step 1: Fetch subtitles
    update_source_status(db, source_uid, "transcribing")
    subtitle_result = fetch_subtitles(url, settings)
    update_source_transcript(db, source_uid, subtitle_result.text)
    update_source_status(db, source_uid, "text_ready")

    # Step 2: Check size — rough word-count estimate
    token_count = len(subtitle_result.text.split())
    threshold = settings.system.llm.large_format_threshold_tokens

    # Step 3: Chunk + embed regardless of size (source must reach rag_ready)
    update_source_status(db, source_uid, "embedding")
    chunks = chunk_text(subtitle_result.text, settings.system)
    insert_chunks(db, source_uid, chunks)
    for chunk in chunks:
        embedding = embed_text(chunk.content, settings)
        insert_chunk_embeddings(db, chunk.uid, embedding)

    update_source_status(db, source_uid, "rag_ready")

    if token_count > threshold:
        raise LargeFormatError(
            source_uid=source_uid,
            token_count=token_count,
            threshold=threshold,
        )

    return get_source(db, source_uid)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/workflows/test_ingest_youtube.py -v
```

Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add workflows/ingest_youtube.py tests/workflows/test_ingest_youtube.py
git commit -m "feat: ingest_youtube workflow with LargeFormatError handling"
```

---

## Task 6: workflows/ingest_audio.py

**Files:**
- Modify: `workflows/ingest_audio.py`
- Modify: `tests/workflows/test_ingest_audio.py`

- [ ] **Step 1: Write the failing tests**

Replace `tests/workflows/test_ingest_audio.py` with:

```python
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from core.schemas import TranscriptResult, CompressResult, ChunkResult, Source
from core.errors import LargeFormatError


def _compress_result(tmp_path):
    out = tmp_path / "compressed.opus"
    out.write_bytes(b"fake opus data")
    return CompressResult(
        output_path=str(out),
        original_size_bytes=1000,
        compressed_size_bytes=200,
    )


def _transcript():
    return TranscriptResult(text="Audio transcript text here.", language="fr", duration_seconds=60.0)


def _chunk(uid="c1", pos=0):
    return ChunkResult(uid=uid, position=pos, content="chunk content here", token_count=3)


def test_ingest_audio_returns_rag_ready_source(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake mp3")

    with patch("workflows.ingest_audio.compress_audio", return_value=_compress_result(tmp_path)), \
         patch("workflows.ingest_audio.transcribe", return_value=_transcript()), \
         patch("workflows.ingest_audio.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_audio.embed_text", return_value=[0.1] * 768):

        result = ingest_audio(str(audio_file), settings, title="Test Audio")

    assert isinstance(result, Source)
    assert result.status == "rag_ready"
    assert result.source_type == "audio"


def test_ingest_audio_stores_transcript(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio
    from infrastructure.db import get_source

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake mp3")

    with patch("workflows.ingest_audio.compress_audio", return_value=_compress_result(tmp_path)), \
         patch("workflows.ingest_audio.transcribe", return_value=_transcript()), \
         patch("workflows.ingest_audio.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_audio.embed_text", return_value=[0.1] * 768):

        result = ingest_audio(str(audio_file), settings)

    stored = get_source(tmp_db, result.uid)
    assert stored.transcript == "Audio transcript text here."


def test_ingest_audio_uses_title_for_slug(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake mp3")

    with patch("workflows.ingest_audio.compress_audio", return_value=_compress_result(tmp_path)), \
         patch("workflows.ingest_audio.transcribe", return_value=_transcript()), \
         patch("workflows.ingest_audio.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_audio.embed_text", return_value=[0.1] * 768):

        result = ingest_audio(str(audio_file), settings, title="Mon Podcast Génial")

    assert "mon-podcast-genial" in result.slug


def test_ingest_audio_raises_large_format_error(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake mp3")
    big_transcript = TranscriptResult(
        text=" ".join(["word"] * 50001), language="fr", duration_seconds=3600.0
    )

    with patch("workflows.ingest_audio.compress_audio", return_value=_compress_result(tmp_path)), \
         patch("workflows.ingest_audio.transcribe", return_value=big_transcript), \
         patch("workflows.ingest_audio.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_audio.embed_text", return_value=[0.1] * 768):

        with pytest.raises(LargeFormatError):
            ingest_audio(str(audio_file), settings)


def test_ingest_audio_detects_video_source_type(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    # Note: tmp_settings only has "audio" and "video" in source_types for this test
    # We need video in the taxonomy — tmp_settings includes "audio", "pdf" but not "video"
    # The conftest has source_types: [youtube, audio, pdf] — use audio for this test
    audio_file = tmp_path / "recording.mp3"
    audio_file.write_bytes(b"fake mp3")

    with patch("workflows.ingest_audio.compress_audio", return_value=_compress_result(tmp_path)), \
         patch("workflows.ingest_audio.transcribe", return_value=_transcript()), \
         patch("workflows.ingest_audio.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_audio.embed_text", return_value=[0.1] * 768):

        result = ingest_audio(str(audio_file), settings, source_type="audio")

    assert result.source_type == "audio"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/workflows/test_ingest_audio.py -v
```

Expected: FAIL with `ImportError` or `NotImplementedError`

- [ ] **Step 3: Implement workflows/ingest_audio.py**

Replace `workflows/ingest_audio.py` with:

```python
"""
Audio/video file ingestion workflow.

Pipeline:
  compress → transcribe → chunk_text → embed_chunks → [LLM → create_note → embed_note]

Handles source_types: audio, video.
Status transitions: raw → transcribing → text_ready → embedding → rag_ready [→ pre_vaulted → vaulted]
"""

from datetime import date
from pathlib import Path

from core.config import Settings
from core.errors import LargeFormatError
from core.schemas import Source
from core.uid import generate_uid, make_unique_slug
from infrastructure.db import (
    get_connection,
    get_source,
    insert_chunk_embeddings,
    insert_chunks,
    insert_source,
    update_source_status,
    update_source_transcript,
)
from tools.media.compress import compress_audio
from tools.media.transcribe import transcribe
from tools.text.chunk import chunk_text
from tools.text.embed import embed_text


def ingest_audio(
    file_path: str,
    settings: Settings,
    title: str | None = None,
    source_type: str = "audio",
) -> Source:
    """
    Run the full audio/video ingestion pipeline.
    Compresses media first (Opus/AV1), then transcribes via faster-whisper.
    Returns the Source record at rag_ready status.
    Raises LargeFormatError if transcript exceeds token threshold.
    """
    db = settings.db_path
    today = date.today().isoformat()
    source_uid = generate_uid()
    file_stem = Path(file_path).stem

    conn = get_connection(db)
    existing_slugs = {row[0] for row in conn.execute("SELECT slug FROM sources").fetchall()}
    conn.close()

    base_name = title if title else file_stem
    slug = make_unique_slug(base_name, existing_slugs)

    source = Source(
        uid=source_uid,
        slug=slug,
        source_type=source_type,
        status="raw",
        title=title,
        date_added=today,
    )
    insert_source(db, source)

    # Step 1: Compress
    update_source_status(db, source_uid, "transcribing")
    compressed = compress_audio(file_path, settings)

    # Step 2: Transcribe
    transcript_result = transcribe(compressed.output_path, settings)
    update_source_transcript(db, source_uid, transcript_result.text)
    update_source_status(db, source_uid, "text_ready")

    # Step 3: Chunk + embed
    token_count = len(transcript_result.text.split())
    threshold = settings.system.llm.large_format_threshold_tokens

    update_source_status(db, source_uid, "embedding")
    chunks = chunk_text(transcript_result.text, settings.system)
    insert_chunks(db, source_uid, chunks)
    for chunk in chunks:
        embedding = embed_text(chunk.content, settings)
        insert_chunk_embeddings(db, chunk.uid, embedding)

    update_source_status(db, source_uid, "rag_ready")

    if token_count > threshold:
        raise LargeFormatError(
            source_uid=source_uid,
            token_count=token_count,
            threshold=threshold,
        )

    return get_source(db, source_uid)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/workflows/test_ingest_audio.py -v
```

Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add workflows/ingest_audio.py tests/workflows/test_ingest_audio.py
git commit -m "feat: ingest_audio workflow (compress → transcribe → chunk → embed)"
```

---

## Task 7: workflows/ingest_pdf.py

**Files:**
- Modify: `workflows/ingest_pdf.py`
- Modify: `tests/workflows/test_ingest_pdf.py`

Note: PDF text extraction uses `pypdf` for v1 simplicity. Docling (spec comment) is a future upgrade for better layout analysis.

- [ ] **Step 1: Write the failing tests**

Replace `tests/workflows/test_ingest_pdf.py` with:

```python
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from core.schemas import ChunkResult, Source
from core.errors import LargeFormatError


def _chunk(uid="c1", pos=0):
    return ChunkResult(uid=uid, position=pos, content="pdf chunk content", token_count=3)


def test_ingest_pdf_returns_rag_ready_source(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_pdf import ingest_pdf

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    pdf_file = tmp_path / "document.pdf"
    pdf_file.write_bytes(b"fake pdf bytes")

    with patch("workflows.ingest_pdf._extract_pdf_text", return_value="PDF extracted text content."), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_pdf.embed_text", return_value=[0.1] * 768):

        result = ingest_pdf(str(pdf_file), settings, title="Mon Document")

    assert isinstance(result, Source)
    assert result.status == "rag_ready"
    assert result.source_type == "pdf"


def test_ingest_pdf_stores_transcript(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_pdf import ingest_pdf
    from infrastructure.db import get_source

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_bytes(b"fake pdf")

    with patch("workflows.ingest_pdf._extract_pdf_text", return_value="PDF content here."), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_pdf.embed_text", return_value=[0.1] * 768):

        result = ingest_pdf(str(pdf_file), settings)

    stored = get_source(tmp_db, result.uid)
    assert stored.transcript == "PDF content here."


def test_ingest_pdf_livre_source_type(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_pdf import ingest_pdf

    # Add "livre" to source_types for this test using a fresh settings
    import yaml
    from pathlib import Path as P
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "system.yaml").write_text(yaml.dump({
        "chunking": {"size": 800, "overlap": 80},
        "llm": {"max_retries": 2, "large_format_threshold_tokens": 50000},
        "taxonomy": {
            "note_types": ["synthese"],
            "source_types": ["youtube", "audio", "pdf", "livre"],
            "generation_templates": ["standard"],
        },
    }))
    user_dir = tmp_path / "eu"
    (user_dir / "data").mkdir(parents=True)
    (user_dir / "vault" / "notes").mkdir(parents=True)
    (config_dir / "user.yaml").write_text(yaml.dump({
        "embedding": {"provider": "ollama", "model": "nomic-embed-text"},
        "llm": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "vault": {"content_language": "fr", "obsidian_sync": True, "default_generation_template": "standard"},
    }))
    (config_dir / "install.yaml").write_text(yaml.dump({
        "paths": {"user_dir": str(user_dir), "db_file": str(tmp_db)},
        "providers": {"ollama_base_url": "http://localhost:11434"},
    }))
    from core.config import load_settings
    settings = load_settings(config_dir)

    pdf_file = tmp_path / "book.pdf"
    pdf_file.write_bytes(b"fake pdf")

    with patch("workflows.ingest_pdf._extract_pdf_text", return_value="Book content here."), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_pdf.embed_text", return_value=[0.1] * 768):

        result = ingest_pdf(str(pdf_file), settings, source_type="livre")

    assert result.source_type == "livre"


def test_ingest_pdf_raises_large_format_error(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_pdf import ingest_pdf

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    pdf_file = tmp_path / "big.pdf"
    pdf_file.write_bytes(b"fake pdf")

    with patch("workflows.ingest_pdf._extract_pdf_text",
               return_value=" ".join(["word"] * 50001)), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_pdf.embed_text", return_value=[0.1] * 768):

        with pytest.raises(LargeFormatError):
            ingest_pdf(str(pdf_file), settings)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/workflows/test_ingest_pdf.py -v
```

Expected: FAIL with `ImportError` or `NotImplementedError`

- [ ] **Step 3: Implement workflows/ingest_pdf.py**

Replace `workflows/ingest_pdf.py` with:

```python
"""
PDF/book ingestion workflow.

Pipeline:
  extract_text (pypdf) → chunk_text → embed_chunks → [LLM → create_note → embed_note]

Handles source_types: pdf, livre (same pipeline, different taxonomy value).
source_type: web — future chantier, not implemented in v1.
Status transitions: raw → transcribing → text_ready → embedding → rag_ready [→ pre_vaulted → vaulted]

Note: spec mentions Docling for better PDF layout analysis (tables, columns, figures).
pypdf is used in v1 for simplicity. Upgrade to Docling is a future chantier.
"""

from datetime import date
from pathlib import Path

from core.config import Settings
from core.errors import LargeFormatError
from core.schemas import Source
from core.uid import generate_uid, make_unique_slug
from infrastructure.db import (
    get_connection,
    get_source,
    insert_chunk_embeddings,
    insert_chunks,
    insert_source,
    update_source_status,
    update_source_transcript,
)
from tools.text.chunk import chunk_text
from tools.text.embed import embed_text


def _extract_pdf_text(file_path: str) -> str:
    """Extract full text from a PDF using pypdf."""
    import pypdf
    reader = pypdf.PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def ingest_pdf(
    file_path: str,
    settings: Settings,
    title: str | None = None,
    source_type: str = "pdf",
) -> Source:
    """
    Run the full PDF ingestion pipeline.
    source_type: 'pdf' or 'livre' — same pipeline, different metadata.
    Returns the Source record at rag_ready status.
    Raises LargeFormatError if extracted text exceeds token threshold.
    """
    db = settings.db_path
    today = date.today().isoformat()
    source_uid = generate_uid()
    file_stem = Path(file_path).stem

    conn = get_connection(db)
    existing_slugs = {row[0] for row in conn.execute("SELECT slug FROM sources").fetchall()}
    conn.close()

    base_name = title if title else file_stem
    slug = make_unique_slug(base_name, existing_slugs)

    source = Source(
        uid=source_uid,
        slug=slug,
        source_type=source_type,
        status="raw",
        title=title,
        date_added=today,
    )
    insert_source(db, source)

    # Step 1: Extract text
    update_source_status(db, source_uid, "transcribing")
    text = _extract_pdf_text(file_path)
    update_source_transcript(db, source_uid, text)
    update_source_status(db, source_uid, "text_ready")

    # Step 2: Chunk + embed
    token_count = len(text.split())
    threshold = settings.system.llm.large_format_threshold_tokens

    update_source_status(db, source_uid, "embedding")
    chunks = chunk_text(text, settings.system)
    insert_chunks(db, source_uid, chunks)
    for chunk in chunks:
        embedding = embed_text(chunk.content, settings)
        insert_chunk_embeddings(db, chunk.uid, embedding)

    update_source_status(db, source_uid, "rag_ready")

    if token_count > threshold:
        raise LargeFormatError(
            source_uid=source_uid,
            token_count=token_count,
            threshold=threshold,
        )

    return get_source(db, source_uid)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/workflows/test_ingest_pdf.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add workflows/ingest_pdf.py tests/workflows/test_ingest_pdf.py
git commit -m "feat: ingest_pdf workflow (pypdf text extraction)"
```

---

## Task 8: mcp/server.py — FastMCP routing layer

**Files:**
- Modify: `mcp/server.py`
- Create: `tests/mcp/__init__.py`
- Create: `tests/mcp/test_server.py`

The MCP server is routing only. All business logic lives in `tools/`. Tests verify that the right tool is called with the right arguments — not that the tool logic is correct (that is tested in Plan 2).

- [ ] **Step 1: Create tests/mcp/__init__.py**

```bash
echo "" > tests/mcp/__init__.py
```

- [ ] **Step 2: Write the failing tests**

Create `tests/mcp/test_server.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from core.schemas import (
    ChunkResult, SearchResult, NoteResult, FinalizeResult,
    TranscriptResult, CompressResult, SubtitleResult, ExportResult,
)


# ---------------------------------------------------------------------------
# chunk_text
# ---------------------------------------------------------------------------

def test_mcp_chunk_text_calls_tool(tmp_settings):
    import mcp.server as srv

    chunk = ChunkResult(uid="c1", position=0, content="hello world here", token_count=3)
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._chunk_text_tool", return_value=[chunk]) as mock_tool:
        result = srv.chunk_text("hello world here")

    mock_tool.assert_called_once()
    assert len(result) == 1
    assert result[0]["uid"] == "c1"


# ---------------------------------------------------------------------------
# embed_text
# ---------------------------------------------------------------------------

def test_mcp_embed_text_calls_tool(tmp_settings):
    import mcp.server as srv

    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._embed_text_tool", return_value=[0.1] * 768) as mock_tool:
        result = srv.embed_text("hello")

    mock_tool.assert_called_once_with("hello", tmp_settings)
    assert len(result) == 768


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def test_mcp_search_calls_tool(tmp_settings):
    import mcp.server as srv

    sr = SearchResult(content="content", title="title", distance=0.1)
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._search_tool", return_value=[sr]) as mock_tool:
        result = srv.search("bitcoin")

    mock_tool.assert_called_once()
    assert len(result) == 1
    assert result[0]["content"] == "content"


# ---------------------------------------------------------------------------
# transcribe
# ---------------------------------------------------------------------------

def test_mcp_transcribe_calls_tool(tmp_settings):
    import mcp.server as srv

    tr = TranscriptResult(text="bonjour", language="fr", duration_seconds=10.0)
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._transcribe_tool", return_value=tr) as mock_tool:
        result = srv.transcribe("/path/to/audio.mp3")

    mock_tool.assert_called_once()
    assert result["text"] == "bonjour"


# ---------------------------------------------------------------------------
# compress_audio
# ---------------------------------------------------------------------------

def test_mcp_compress_audio_calls_tool(tmp_settings):
    import mcp.server as srv

    cr = CompressResult(output_path="/tmp/out.opus", original_size_bytes=1000, compressed_size_bytes=200)
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._compress_audio_tool", return_value=cr) as mock_tool:
        result = srv.compress_audio("/path/to/audio.mp3")

    mock_tool.assert_called_once()
    assert result["output_path"] == "/tmp/out.opus"


# ---------------------------------------------------------------------------
# fetch_subtitles
# ---------------------------------------------------------------------------

def test_mcp_fetch_subtitles_calls_tool(tmp_settings):
    import mcp.server as srv

    sub = SubtitleResult(text="subtitle text", language="fr", source="subtitles")
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._fetch_subtitles_tool", return_value=sub) as mock_tool:
        result = srv.fetch_subtitles("https://youtube.com/watch?v=abc")

    mock_tool.assert_called_once()
    assert result["text"] == "subtitle text"


# ---------------------------------------------------------------------------
# export_typst
# ---------------------------------------------------------------------------

def test_mcp_export_typst_calls_tool(tmp_settings):
    import mcp.server as srv

    er = ExportResult(output_path="/tmp/note.typ", format="typst")
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._export_typst_tool", return_value=er) as mock_tool:
        result = srv.export_typst("note-uid-1")

    mock_tool.assert_called_once_with("note-uid-1", tmp_settings)
    assert result["output_path"] == "/tmp/note.typ"


# ---------------------------------------------------------------------------
# export_mermaid
# ---------------------------------------------------------------------------

def test_mcp_export_mermaid_calls_tool(tmp_settings):
    import mcp.server as srv

    er = ExportResult(output_path="/tmp/graph.md", format="mermaid")
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._export_mermaid_tool", return_value=er) as mock_tool:
        result = srv.export_mermaid(tag="bitcoin")

    mock_tool.assert_called_once()
    assert result["format"] == "mermaid"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/mcp/test_server.py -v
```

Expected: FAIL (imports fail — server.py has no FastMCP setup)

- [ ] **Step 4: Implement mcp/server.py**

Replace `mcp/server.py` with:

```python
"""
MCP server for EgoVault v2.

Exposes tools/ via the Model Context Protocol (FastMCP).
All business logic lives in tools/ — this file is routing only.

Tool groups:
  Vault tools    : create_note, search, get_note, finalize_source
  Atomic tools   : transcribe, compress_audio, fetch_subtitles, chunk_text, embed_text
  Export tools   : export_typst, export_mermaid

[FUTURE] Template tools: manage_generation_template (human validation required)
"""

from mcp.server.fastmcp import FastMCP

from core.config import load_settings
from core.schemas import SearchFilters

# Lazy imports of tools (to allow patching in tests)
from tools.media.compress import compress_audio as _compress_audio_tool
from tools.media.fetch_subtitles import fetch_subtitles as _fetch_subtitles_tool
from tools.media.transcribe import transcribe as _transcribe_tool
from tools.text.chunk import chunk_text as _chunk_text_tool
from tools.text.embed import embed_text as _embed_text_tool
from tools.vault.create_note import create_note as _create_note_tool
from tools.vault.finalize_source import finalize_source as _finalize_source_tool
from tools.vault.search import search as _search_tool
from tools.export.typst import export_typst as _export_typst_tool
from tools.export.mermaid import export_mermaid as _export_mermaid_tool
from infrastructure.db import get_note as _get_note

settings = load_settings()
mcp = FastMCP("egovault")


# ============================================================
# Vault tools — full pipeline, writes to DB
# ============================================================

@mcp.tool()
def create_note(source_uid: str, content: dict) -> dict:
    """Validate and create a note. Writes to DB and generates Markdown.
    Requires prior human approval of content."""
    from core.schemas import NoteContentInput, NoteSystemFields
    from core.uid import generate_uid, make_unique_slug
    from infrastructure.db import get_connection
    from datetime import date

    db = settings.db_path
    conn = get_connection(db)
    existing_slugs = {row[0] for row in conn.execute("SELECT slug FROM notes").fetchall()}
    conn.close()

    content_input = NoteContentInput(**content)
    today = date.today().isoformat()
    system_fields = NoteSystemFields(
        uid=generate_uid(),
        date_created=today,
        source_uid=source_uid if source_uid else None,
        slug=make_unique_slug(content_input.title, existing_slugs),
    )
    result = _create_note_tool(content_input, system_fields, settings)
    return result.model_dump(mode="json")


@mcp.tool()
def search(query: str, filters: dict | None = None, mode: str = "chunks") -> list[dict]:
    """Semantic search over chunks or notes with optional SQL filters.
    Filters: source_type, tags, date_from, date_to, note_type."""
    search_filters = SearchFilters(**(filters or {}))
    results = _search_tool(query, search_filters, settings)
    return [r.model_dump(mode="json") for r in results]


@mcp.tool()
def get_note(uid: str) -> dict:
    """Retrieve full note by UID."""
    note = _get_note(settings.db_path, uid)
    if note is None:
        raise ValueError(f"Note '{uid}' not found")
    return note.model_dump(mode="json")


@mcp.tool()
def finalize_source(source_uid: str) -> dict:
    """Mark source as vaulted. Moves media to permanent storage."""
    result = _finalize_source_tool(source_uid, settings)
    return result.model_dump(mode="json")


# ============================================================
# Atomic tools — standalone, no DB write unless stated
# ============================================================

@mcp.tool()
def transcribe(file_path: str, language: str = "fr") -> dict:
    """Transcribe audio/video to text. No DB write."""
    result = _transcribe_tool(file_path, settings)
    return result.model_dump(mode="json")


@mcp.tool()
def compress_audio(file_path: str, bitrate_kbps: int = 12) -> dict:
    """Compress audio to Opus mono. No DB write. Default: 12kbps mono 16kHz."""
    result = _compress_audio_tool(file_path, settings)
    return result.model_dump(mode="json")


@mcp.tool()
def fetch_subtitles(youtube_url: str, language: str = "fr") -> dict:
    """Fetch YouTube subtitles. Falls back to audio download + transcribe. No DB write."""
    result = _fetch_subtitles_tool(youtube_url, settings)
    return result.model_dump(mode="json")


@mcp.tool()
def chunk_text(text: str) -> list[dict]:
    """Split text into chunks per system.yaml:chunking config. No DB write."""
    results = _chunk_text_tool(text, settings.system)
    return [r.model_dump(mode="json") for r in results]


@mcp.tool()
def embed_text(text: str) -> list[float]:
    """Embed text using configured provider. No DB write."""
    return _embed_text_tool(text, settings)


# ============================================================
# Export tools — generate output artefacts
# ============================================================

@mcp.tool()
def export_typst(note_uid: str) -> dict:
    """Export note to Typst format (.typ file). No DB write."""
    result = _export_typst_tool(note_uid, settings)
    return result.model_dump(mode="json")


@mcp.tool()
def export_mermaid(note_uid: str | None = None, tag: str | None = None) -> dict:
    """Export note relationships to Mermaid diagram (.md file). No DB write."""
    result = _export_mermaid_tool(note_uid, tag, settings)
    return result.model_dump(mode="json")


# ============================================================
# [FUTURE] Template management — human validation required
# ============================================================
# @mcp.tool()
# def manage_generation_template(action, name, system_prompt, sections): ...


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/mcp/test_server.py -v
```

Expected: 8 PASSED

- [ ] **Step 6: Run full test suite**

```bash
.venv/Scripts/python -m pytest tests/ -v
```

Expected: All tests pass (80 from Plan 1 + tests from Plan 2 + tests from Plan 3)

- [ ] **Step 7: Commit**

```bash
git add mcp/server.py tests/mcp/__init__.py tests/mcp/test_server.py
git commit -m "feat: FastMCP server routing layer (all tools exposed)"
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Task |
|---|---|
| `LargeFormatError` on oversized source (spec 7.0) | Task 2 |
| Generation template YAML (spec 3.2) | Task 3 |
| LLM client with max_retries (spec 5.1, 6.3) | Task 4 |
| YouTube pipeline: fetch_subtitles → chunk → embed (spec workflow docstring) | Task 5 |
| Audio pipeline: compress → transcribe → chunk → embed | Task 6 |
| PDF pipeline: extract_text → chunk → embed | Task 7 |
| MCP vault tools: create_note, search, get_note, finalize_source (spec 5.4) | Task 8 |
| MCP atomic tools: transcribe, compress, fetch_subtitles, chunk_text, embed_text (spec 5.4) | Task 8 |
| MCP export tools: export_typst, export_mermaid (spec 5.4) | Task 8 |
| Status transitions raw→transcribing→text_ready→embedding→rag_ready (spec 4.1) | Tasks 5, 6, 7 |
| `update_source_transcript` DB helper | Task 1 |
| mcp, anthropic, pypdf dependencies | Task 1 |

### Placeholder scan — none found.

### Type consistency

- `compress_audio(file_path, settings)` — tool takes `(str, Settings)`. Task 6 workflow calls it correctly.
- `transcribe(file_path, settings)` — tool takes `(str, Settings)`. Task 6 calls correctly.
- `chunk_text(text, system_config)` — tool takes `(str, SystemConfig)`. Tasks 5/6/7 pass `settings.system`. Correct.
- `embed_text(text, settings)` — tool takes `(str, Settings)`. All workflows pass `settings`. Correct.
- `insert_chunk_embeddings(db, chunk_uid, embedding)` — single chunk. Workflows loop per chunk. Correct.
- MCP `chunk_text` calls `_chunk_text_tool(text, settings.system)` — correct.
- MCP `embed_text` calls `_embed_text_tool(text, settings)` — correct.

---

**Plan complete and saved to `docs/superpowers/plans/2026-03-26-egovault-v2-workflows-mcp.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch with checkpoints

**Which approach?**
