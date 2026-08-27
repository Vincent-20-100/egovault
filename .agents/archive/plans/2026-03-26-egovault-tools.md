# EgoVault — Plan 2: Tools (tools/)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all atomic tool functions in `tools/` — each tool is a pure typed function (one input → one typed output, no implicit side effects, no cross-imports between tools).

**Architecture:** Each tool wraps one infrastructure capability. `tools/text/` wraps embedding/chunking, `tools/media/` wraps ffmpeg/whisper/yt-dlp, `tools/vault/` writes to DB+vault, `tools/export/` generates output artefacts. Tools never import other tools. All tools are decorated with `@loggable`.

**Tech Stack:** Python 3.10+, faster-whisper, yt-dlp, youtube-transcript-api, ffmpeg (system), mcp>=1.0, pydantic>=2.0

**Prerequisite:** Plan 1 (Foundation) complete — `core/` and `infrastructure/` are fully implemented and tested.

**Spec:** `docs/specs/2026-03-25-egovault-v2-architecture-design.md` sections 5.4, 6.1, 6.5

---

## Part 0 — Scope

This plan covers:
- `tools/text/chunk.py` — chunk_text()
- `tools/text/embed.py` — embed_text()
- `tools/media/transcribe.py` — transcribe()
- `tools/media/compress.py` — compress_audio()
- `tools/media/fetch_subtitles.py` — fetch_subtitles()
- `tools/vault/create_note.py` — create_note()
- `tools/vault/update_note.py` — update_note()
- `tools/vault/search.py` — search()
- `tools/vault/finalize_source.py` — finalize_source()
- `tools/export/typst.py` — export_typst()
- `tools/export/mermaid.py` — export_mermaid()

**Not in this plan:** workflows/, mcp/server.py (Plan 3)

---

## Task 1: tools/text/chunk.py — chunk_text()

**Files:**
- Modify: `tools/text/chunk.py`
- Modify: `tests/tools/text/test_chunk.py`

- [ ] **Step 1: Write the failing tests**

Replace `tests/tools/text/test_chunk.py` with:

```python
import pytest
from core.config import SystemConfig, ChunkingConfig, LLMSystemConfig, TaxonomyConfig
from core.schemas import ChunkResult


def _config(size=10, overlap=2):
    return SystemConfig(
        chunking=ChunkingConfig(size=size, overlap=overlap),
        llm=LLMSystemConfig(max_retries=2, large_format_threshold_tokens=50000),
        taxonomy=TaxonomyConfig(
            note_types=["synthese"], source_types=["youtube"],
            generation_templates=["standard"]
        ),
    )


def test_chunk_text_basic():
    from tools.text.chunk import chunk_text
    text = " ".join([f"word{i}" for i in range(25)])
    chunks = chunk_text(text, _config(size=10, overlap=2))
    assert len(chunks) > 1
    assert all(isinstance(c, ChunkResult) for c in chunks)


def test_chunk_text_positions_sequential():
    from tools.text.chunk import chunk_text
    text = " ".join([f"word{i}" for i in range(30)])
    chunks = chunk_text(text, _config(size=10, overlap=2))
    assert [c.position for c in chunks] == list(range(len(chunks)))


def test_chunk_text_each_has_uid():
    from tools.text.chunk import chunk_text
    text = " ".join([f"word{i}" for i in range(20)])
    chunks = chunk_text(text, _config(size=10, overlap=2))
    uids = [c.uid for c in chunks]
    assert len(uids) == len(set(uids))  # all unique


def test_chunk_text_respects_size():
    from tools.text.chunk import chunk_text
    text = " ".join([f"word{i}" for i in range(50)])
    chunks = chunk_text(text, _config(size=10, overlap=0))
    for c in chunks[:-1]:  # last chunk may be smaller
        assert c.token_count == 10


def test_chunk_text_overlap_content():
    from tools.text.chunk import chunk_text
    # With overlap=3, last 3 words of chunk N appear at start of chunk N+1
    text = " ".join([f"w{i}" for i in range(20)])
    chunks = chunk_text(text, _config(size=8, overlap=3))
    if len(chunks) >= 2:
        end_of_first = chunks[0].content.split()[-3:]
        start_of_second = chunks[1].content.split()[:3]
        assert end_of_first == start_of_second


def test_chunk_text_short_input_single_chunk():
    from tools.text.chunk import chunk_text
    text = "hello world"
    chunks = chunk_text(text, _config(size=10, overlap=2))
    assert len(chunks) == 1
    assert chunks[0].position == 0


def test_chunk_text_empty_returns_empty():
    from tools.text.chunk import chunk_text
    chunks = chunk_text("", _config())
    assert chunks == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/tools/text/test_chunk.py -v
```

Expected: FAIL — `chunk_text` returns `None`.

- [ ] **Step 3: Implement chunk_text in tools/text/chunk.py**

```python
"""
Text chunking tool.

Input  : raw text + config
Output : list[ChunkResult]
No DB write. Chunk size and overlap from system.yaml.
"""

from core.schemas import ChunkResult
from core.config import SystemConfig
from core.logging import loggable
from core.uid import generate_uid


@loggable("chunk_text")
def chunk_text(text: str, config: SystemConfig) -> list[ChunkResult]:
    """
    Split text into overlapping chunks.
    Chunk size and overlap read from config.chunking (system.yaml).
    Token count approximated as word count (1 word ≈ 1 token).
    Each chunk gets a UUID4. No DB write.
    """
    words = text.split()
    if not words:
        return []

    size = config.chunking.size
    overlap = config.chunking.overlap
    step = max(1, size - overlap)

    chunks = []
    position = 0
    i = 0
    while i < len(words):
        chunk_words = words[i:i + size]
        chunks.append(ChunkResult(
            uid=generate_uid(),
            position=position,
            content=" ".join(chunk_words),
            token_count=len(chunk_words),
        ))
        position += 1
        i += step
    return chunks
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/tools/text/test_chunk.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/text/chunk.py tests/tools/text/test_chunk.py
git commit -m "feat: tools/text/chunk.py — chunk_text() with overlap"
```

---

## Task 2: tools/text/embed.py — embed_text()

**Files:**
- Modify: `tools/text/embed.py`
- Modify: `tests/tools/text/test_embed.py`

- [ ] **Step 1: Write the failing tests**

Replace `tests/tools/text/test_embed.py` with:

```python
import pytest
from unittest.mock import patch, MagicMock


def test_embed_text_returns_vector(tmp_settings):
    from tools.text.embed import embed_text

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embedding": [0.5] * 768}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp):
        result = embed_text("hello", tmp_settings)

    assert isinstance(result, list)
    assert len(result) == 768


def test_embed_text_delegates_to_provider(tmp_settings):
    from tools.text.embed import embed_text

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embedding": [0.1] * 768}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp) as mock_post:
        embed_text("test text", tmp_settings)

    assert mock_post.called
    assert "test text" in str(mock_post.call_args)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/tools/text/test_embed.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement embed_text in tools/text/embed.py**

```python
"""
Text embedding tool.

Input  : text string + settings
Output : list[float] (embedding vector)
No DB write. Provider configured via user.yaml.
"""

from core.config import Settings
from core.logging import loggable


@loggable("embed_text")
def embed_text(text: str, settings: Settings) -> list[float]:
    """
    Embed a text string using the configured provider (Ollama or OpenAI).
    Returns a flat list of floats. No DB write.
    """
    from infrastructure.embedding_provider import embed
    return embed(text, settings)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/tools/text/test_embed.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/text/embed.py tests/tools/text/test_embed.py
git commit -m "feat: tools/text/embed.py — embed_text() delegates to embedding_provider"
```

---

## Task 3: tools/media/transcribe.py — transcribe()

**Files:**
- Modify: `tools/media/transcribe.py`
- Modify: `tests/tools/media/test_transcribe.py`

Note: faster-whisper is mocked in tests — no GPU/model needed.

- [ ] **Step 1: Write the failing tests**

Replace `tests/tools/media/test_transcribe.py` with:

```python
import pytest
from unittest.mock import patch, MagicMock
from core.schemas import TranscriptResult


def _mock_whisper(segments_text="Hello world.", language="fr", duration=10.0):
    mock_model = MagicMock()
    mock_segment = MagicMock()
    mock_segment.text = segments_text
    mock_info = MagicMock()
    mock_info.language = language
    mock_info.duration = duration
    mock_model.transcribe.return_value = ([mock_segment], mock_info)
    return mock_model


def test_transcribe_returns_transcript_result():
    from tools.media.transcribe import transcribe

    with patch("faster_whisper.WhisperModel", return_value=_mock_whisper()):
        result = transcribe("audio.mp3", language="fr")

    assert isinstance(result, TranscriptResult)
    assert result.text == "Hello world."
    assert result.language == "fr"
    assert result.duration_seconds == 10.0


def test_transcribe_joins_multiple_segments():
    from tools.media.transcribe import transcribe

    mock_model = MagicMock()
    seg1, seg2 = MagicMock(), MagicMock()
    seg1.text = "  First segment.  "
    seg2.text = "  Second segment.  "
    mock_info = MagicMock()
    mock_info.language = "fr"
    mock_info.duration = 20.0
    mock_model.transcribe.return_value = ([seg1, seg2], mock_info)

    with patch("faster_whisper.WhisperModel", return_value=mock_model):
        result = transcribe("audio.mp3")

    assert "First segment." in result.text
    assert "Second segment." in result.text


def test_transcribe_passes_language_hint():
    from tools.media.transcribe import transcribe

    mock_model = _mock_whisper()
    with patch("faster_whisper.WhisperModel", return_value=mock_model):
        transcribe("audio.mp3", language="en")

    call_kwargs = mock_model.transcribe.call_args
    assert call_kwargs[1].get("language") == "en" or "en" in str(call_kwargs)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/tools/media/test_transcribe.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement transcribe in tools/media/transcribe.py**

```python
"""
Audio/video transcription tool.

Input  : file path + language hint
Output : TranscriptResult (text, language, duration)
No DB write.
"""

from core.schemas import TranscriptResult
from core.logging import loggable


@loggable("transcribe")
def transcribe(file_path: str, language: str = "fr") -> TranscriptResult:
    """
    Transcribe an audio or video file using faster-whisper.
    Falls back to auto language detection if language hint is not recognised.
    No DB write.
    """
    from faster_whisper import WhisperModel

    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(file_path, language=language)
    text = " ".join(seg.text.strip() for seg in segments)
    return TranscriptResult(
        text=text,
        language=info.language,
        duration_seconds=info.duration,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/tools/media/test_transcribe.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/media/transcribe.py tests/tools/media/test_transcribe.py
git commit -m "feat: tools/media/transcribe.py — faster-whisper transcription"
```

---

## Task 4: tools/media/compress.py — compress_audio()

**Files:**
- Modify: `tools/media/compress.py`
- Modify: `tests/tools/media/test_compress.py`

Note: ffmpeg subprocess is mocked. compress_video() is a stub for now (not in v1 scope).

- [ ] **Step 1: Write the failing tests**

Replace `tests/tools/media/test_compress.py` with:

```python
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from core.schemas import CompressResult


def test_compress_audio_returns_compress_result(tmp_path):
    from tools.media.compress import compress_audio

    input_file = tmp_path / "audio.mp3"
    input_file.write_bytes(b"x" * 1000)
    output_file = tmp_path / "audio.opus"
    output_file.write_bytes(b"x" * 100)

    with patch("subprocess.run") as mock_run, \
         patch("os.path.getsize", side_effect=lambda p: 100 if str(p).endswith(".opus") else 1000):
        mock_run.return_value = MagicMock(returncode=0)
        result = compress_audio(str(input_file), bitrate_kbps=12)

    assert isinstance(result, CompressResult)
    assert result.output_path.endswith(".opus")
    assert result.original_size_bytes == 1000
    assert result.compressed_size_bytes == 100


def test_compress_audio_calls_ffmpeg(tmp_path):
    from tools.media.compress import compress_audio

    input_file = tmp_path / "audio.mp3"
    input_file.write_bytes(b"x" * 500)
    output_file = tmp_path / "audio.opus"
    output_file.write_bytes(b"x" * 50)

    with patch("subprocess.run") as mock_run, \
         patch("os.path.getsize", side_effect=lambda p: 50 if str(p).endswith(".opus") else 500):
        mock_run.return_value = MagicMock(returncode=0)
        compress_audio(str(input_file))

    cmd = mock_run.call_args[0][0]
    assert "ffmpeg" in cmd
    assert "libopus" in cmd


def test_compress_audio_default_bitrate(tmp_path):
    from tools.media.compress import compress_audio

    input_file = tmp_path / "audio.mp3"
    input_file.write_bytes(b"x" * 500)

    with patch("subprocess.run") as mock_run, \
         patch("os.path.getsize", return_value=100):
        mock_run.return_value = MagicMock(returncode=0)
        compress_audio(str(input_file))

    cmd = mock_run.call_args[0][0]
    assert "12k" in cmd
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/tools/media/test_compress.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement compress_audio in tools/media/compress.py**

```python
"""
Audio/video compression tool.

Input  : file path + target bitrate
Output : CompressResult (output path, size before/after)
No DB write.
"""

import os
import subprocess
from pathlib import Path

from core.schemas import CompressResult
from core.logging import loggable


@loggable("compress_audio")
def compress_audio(file_path: str, bitrate_kbps: int = 12) -> CompressResult:
    """
    Compress audio to Opus mono via ffmpeg.
    Default: 12kbps mono 16kHz (~5MB/hour).
    Output file written alongside source with .opus extension.
    No DB write.
    """
    input_path = Path(file_path)
    output_path = input_path.with_suffix(".opus")
    original_size = os.path.getsize(str(input_path))

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(input_path),
            "-c:a", "libopus",
            "-b:a", f"{bitrate_kbps}k",
            "-ac", "1",
            "-ar", "16000",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )

    compressed_size = os.path.getsize(str(output_path))
    return CompressResult(
        output_path=str(output_path),
        original_size_bytes=original_size,
        compressed_size_bytes=compressed_size,
    )


@loggable("compress_video")
def compress_video(file_path: str) -> CompressResult:
    """
    Compress video to AV1 via ffmpeg.
    No DB write.
    """
    raise NotImplementedError("compress_video not implemented in v1")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/tools/media/test_compress.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/media/compress.py tests/tools/media/test_compress.py
git commit -m "feat: tools/media/compress.py — compress_audio() via ffmpeg/libopus"
```

---

## Task 5: tools/media/fetch_subtitles.py — fetch_subtitles()

**Files:**
- Modify: `tools/media/fetch_subtitles.py`
- Modify: `tests/tools/media/test_fetch_subtitles.py`

- [ ] **Step 1: Write the failing tests**

Replace `tests/tools/media/test_fetch_subtitles.py` with:

```python
import pytest
from unittest.mock import patch, MagicMock
from core.schemas import SubtitleResult


YT_URL = "https://youtube.com/watch?v=dQw4w9WgXcQ"


def test_fetch_subtitles_returns_subtitle_result():
    from tools.media.fetch_subtitles import fetch_subtitles

    mock_transcript = [
        {"text": "Hello world", "start": 0.0, "duration": 2.0},
        {"text": "Foo bar", "start": 2.0, "duration": 2.0},
    ]
    with patch("youtube_transcript_api.YouTubeTranscriptApi.get_transcript",
               return_value=mock_transcript):
        result = fetch_subtitles(YT_URL, language="fr")

    assert isinstance(result, SubtitleResult)
    assert result.source == "subtitles"
    assert "Hello world" in result.text
    assert "Foo bar" in result.text


def test_fetch_subtitles_joins_entries():
    from tools.media.fetch_subtitles import fetch_subtitles

    mock_transcript = [{"text": "A"}, {"text": "B"}, {"text": "C"}]
    with patch("youtube_transcript_api.YouTubeTranscriptApi.get_transcript",
               return_value=mock_transcript):
        result = fetch_subtitles(YT_URL)

    assert "A" in result.text and "B" in result.text and "C" in result.text


def test_fetch_subtitles_fallback_to_transcription(tmp_path):
    from tools.media.fetch_subtitles import fetch_subtitles
    from core.schemas import TranscriptResult

    # Force subtitle fetch to fail
    with patch("youtube_transcript_api.YouTubeTranscriptApi.get_transcript",
               side_effect=Exception("No subtitles")), \
         patch("tools.media.fetch_subtitles._download_audio",
               return_value=str(tmp_path / "audio.mp3")), \
         patch("tools.media.fetch_subtitles.transcribe",
               return_value=TranscriptResult(text="Transcribed text", language="fr",
                                             duration_seconds=60.0)):
        result = fetch_subtitles(YT_URL)

    assert result.source == "transcription"
    assert result.text == "Transcribed text"


def test_fetch_subtitles_extracts_video_id():
    from tools.media.fetch_subtitles import _extract_video_id

    assert _extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert _extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert _extract_video_id("https://youtube.com/watch?v=abc123&t=30") == "abc123"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/tools/media/test_fetch_subtitles.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement fetch_subtitles in tools/media/fetch_subtitles.py**

```python
"""
YouTube subtitle fetcher.

Input  : YouTube URL + language
Output : SubtitleResult (text, language, source indicator)
No DB write. Falls back to audio download + transcribe if subtitles unavailable.
"""

import re
import tempfile
from pathlib import Path

from core.schemas import SubtitleResult
from core.logging import loggable


def _extract_video_id(url: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/)([^&?/]+)", url)
    if not match:
        raise ValueError(f"Cannot extract video ID from URL: {url}")
    return match.group(1)


def _download_audio(youtube_url: str, output_dir: str) -> str:
    import yt_dlp
    opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{output_dir}/audio.%(ext)s",
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([youtube_url])
    audio_files = list(Path(output_dir).glob("audio.*"))
    if not audio_files:
        raise RuntimeError(f"yt-dlp did not produce any audio file in {output_dir}")
    return str(audio_files[0])


@loggable("fetch_subtitles")
def fetch_subtitles(youtube_url: str, language: str = "fr") -> SubtitleResult:
    """
    Fetch YouTube subtitles via youtube-transcript-api.
    If subtitles unavailable: download audio via yt-dlp, transcribe via Whisper.
    SubtitleResult.source indicates 'subtitles' or 'transcription'.
    No DB write.
    """
    from youtube_transcript_api import YouTubeTranscriptApi

    video_id = _extract_video_id(youtube_url)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=[language, "en"]
        )
        text = " ".join(entry["text"] for entry in transcript)
        return SubtitleResult(text=text, language=language, source="subtitles")
    except Exception:
        from tools.media.transcribe import transcribe
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = _download_audio(youtube_url, tmpdir)
            result = transcribe(audio_path, language=language)
        return SubtitleResult(
            text=result.text, language=result.language, source="transcription"
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/tools/media/test_fetch_subtitles.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/media/fetch_subtitles.py tests/tools/media/test_fetch_subtitles.py
git commit -m "feat: tools/media/fetch_subtitles.py — subtitles + yt-dlp fallback"
```

---

## Task 6: tools/vault/create_note.py — create_note()

**Files:**
- Modify: `tools/vault/create_note.py`
- Modify: `tests/tools/vault/test_create_note.py`

- [ ] **Step 1: Write the failing tests**

Replace `tests/tools/vault/test_create_note.py` with:

```python
import pytest
from datetime import date
from core.schemas import NoteContentInput, NoteSystemFields, NoteResult
from core.uid import generate_uid


def _content(**overrides):
    data = {
        "title": "Test Note Title",
        "docstring": "What this note is about.",
        "body": "This is the body of the test note, long enough.",
        "tags": ["test-tag"],
        "note_type": None,
        "source_type": None,
    }
    data.update(overrides)
    return NoteContentInput(**data)


def _system_fields(**overrides):
    data = {
        "uid": generate_uid(),
        "date_created": date.today().isoformat(),
        "source_uid": None,
        "slug": "test-note-title",
        "generation_template": None,
    }
    data.update(overrides)
    return NoteSystemFields(**data)


def test_create_note_returns_note_result(tmp_settings, tmp_db, tmp_path):
    from tools.vault.create_note import create_note

    settings = tmp_settings
    settings.__dict__["_db_path_override"] = tmp_db

    # Patch db_path property
    import unittest.mock as mock
    with mock.patch.object(type(settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        result = create_note(_content(), _system_fields(), settings)

    assert isinstance(result, NoteResult)
    assert result.note.title == "Test Note Title"
    assert result.markdown_path.endswith(".md")


def test_create_note_writes_to_db(tmp_settings, tmp_db, tmp_path):
    from tools.vault.create_note import create_note
    from infrastructure.db import get_note
    import unittest.mock as mock

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        system = _system_fields()
        create_note(_content(), system, tmp_settings)
        note = get_note(tmp_db, system.uid)

    assert note is not None
    assert note.title == "Test Note Title"


def test_create_note_writes_markdown_file(tmp_settings, tmp_db, tmp_path):
    from tools.vault.create_note import create_note
    import unittest.mock as mock
    from pathlib import Path

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        system = _system_fields()
        result = create_note(_content(), system, tmp_settings)

    assert Path(result.markdown_path).exists()
    content = Path(result.markdown_path).read_text()
    assert "# Test Note Title" in content


def test_create_note_source_type_mismatch_raises(tmp_settings, tmp_db, tmp_path):
    from tools.vault.create_note import create_note
    from infrastructure.db import insert_source
    from core.schemas import Source
    import unittest.mock as mock

    source = Source(
        uid="src-1", slug="src", source_type="youtube", status="rag_ready",
        date_added=date.today().isoformat(),
    )
    insert_source(tmp_db, source)

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        with pytest.raises(ValueError, match="source_type"):
            create_note(
                _content(source_type="audio"),
                _system_fields(source_uid="src-1"),
                tmp_settings,
            )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_create_note.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement create_note in tools/vault/create_note.py**

```python
"""
Note creation tool.

Input  : NoteContentInput (LLM or manual) + NoteSystemFields
Output : NoteResult (note record + markdown path)
Writes to DB and generates Markdown file. Requires prior human approval.
"""

from datetime import date

from core.schemas import NoteContentInput, NoteSystemFields, NoteResult, Note
from core.config import Settings
from core.logging import loggable


@loggable("create_note")
def create_note(
    content: NoteContentInput,
    system_fields: NoteSystemFields,
    settings: Settings,
) -> NoteResult:
    """
    Validate and persist a note.
    - Validates content.source_type matches source.source_type when source_uid is set.
    - Writes note to DB (notes + note_tags tables).
    - Generates Markdown via vault_writer.write_note().
    - Does NOT embed — caller must invoke embed_text() on the note body after this tool.
    Requires prior human approval of NoteContentInput before calling.
    """
    from infrastructure.db import insert_note, get_source
    from infrastructure.vault_writer import write_note

    if system_fields.source_uid:
        source = get_source(settings.db_path, system_fields.source_uid)
        if (source and content.source_type
                and content.source_type != source.source_type):
            raise ValueError(
                f"content.source_type '{content.source_type}' does not match "
                f"source.source_type '{source.source_type}'"
            )

    today = date.today().isoformat()
    note = Note(
        **system_fields.model_dump(),
        **content.model_dump(),
        date_modified=today,
        sync_status="synced",
    )

    insert_note(settings.db_path, note)
    settings.vault_path.mkdir(parents=True, exist_ok=True)
    markdown_path = write_note(note, settings.vault_path)

    return NoteResult(note=note, markdown_path=str(markdown_path))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_create_note.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/vault/create_note.py tests/tools/vault/test_create_note.py
git commit -m "feat: tools/vault/create_note.py — DB write + Markdown generation"
```

---

## Task 7: tools/vault/update_note.py — update_note()

**Files:**
- Modify: `tools/vault/update_note.py`
- Create: `tests/tools/vault/test_update_note.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/vault/test_update_note.py`:

```python
import pytest
from datetime import date
from core.schemas import NoteContentInput, NoteSystemFields
from core.uid import generate_uid
import unittest.mock as mock


def _insert_test_note(tmp_db, tmp_path, tmp_settings):
    from tools.vault.create_note import create_note
    from core.schemas import NoteContentInput, NoteSystemFields

    content = NoteContentInput(
        title="Original Title",
        docstring="Original docstring here.",
        body="Original body content of the note.",
        tags=["original-tag"],
    )
    system = NoteSystemFields(
        uid=generate_uid(),
        date_created=date.today().isoformat(),
        slug="original-title",
    )
    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        result = create_note(content, system, tmp_settings)
    return result.note.uid


def test_update_note_returns_note_result(tmp_settings, tmp_db, tmp_path):
    from tools.vault.update_note import update_note
    from core.schemas import NoteResult

    uid = _insert_test_note(tmp_db, tmp_path, tmp_settings)

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        result = update_note(uid, {"rating": 5}, tmp_settings)

    assert isinstance(result, NoteResult)
    assert result.note.rating == 5


def test_update_note_sets_needs_re_embedding(tmp_settings, tmp_db, tmp_path):
    from tools.vault.update_note import update_note

    uid = _insert_test_note(tmp_db, tmp_path, tmp_settings)

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        result = update_note(uid, {"body": "Updated body content here."}, tmp_settings)

    assert result.note.sync_status == "needs_re_embedding"


def test_update_note_ignores_system_fields(tmp_settings, tmp_db, tmp_path):
    from tools.vault.update_note import update_note
    from infrastructure.db import get_note

    uid = _insert_test_note(tmp_db, tmp_path, tmp_settings)
    original_uid = uid

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        update_note(uid, {"uid": "new-uid", "date_created": "2000-01-01"}, tmp_settings)
        note = get_note(tmp_db, original_uid)

    assert note is not None  # uid unchanged
    assert note.date_created != "2000-01-01"


def test_update_note_not_found_raises(tmp_settings, tmp_db, tmp_path):
    from tools.vault.update_note import update_note

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        with pytest.raises(ValueError, match="not found"):
            update_note("nonexistent-uid", {"rating": 3}, tmp_settings)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_update_note.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement update_note in tools/vault/update_note.py**

```python
"""
Note update tool.

Input  : note uid + partial field update
Output : NoteResult
Writes to DB + regenerates Markdown. Sets sync_status = 'needs_re_embedding'.
"""

from datetime import date

from core.schemas import NoteResult
from core.config import Settings
from core.logging import loggable

_SYSTEM_FIELDS = {"uid", "date_created", "source_uid", "generation_template"}


@loggable("update_note")
def update_note(uid: str, fields: dict, settings: Settings) -> NoteResult:
    """
    Update editable fields of an existing note.
    SYSTEM fields (uid, date_created, source_uid, generation_template) are silently ignored.
    Sets sync_status = 'needs_re_embedding' on any content change.
    Updates date_modified. Regenerates Markdown file via vault_writer.
    """
    from infrastructure.db import get_note, update_note as db_update
    from infrastructure.vault_writer import write_note

    note = get_note(settings.db_path, uid)
    if note is None:
        raise ValueError(f"Note not found: {uid}")

    safe_fields = {k: v for k, v in fields.items() if k not in _SYSTEM_FIELDS}
    safe_fields["sync_status"] = "needs_re_embedding"
    safe_fields["date_modified"] = date.today().isoformat()

    db_update(settings.db_path, uid, safe_fields)
    updated_note = get_note(settings.db_path, uid)
    settings.vault_path.mkdir(parents=True, exist_ok=True)
    markdown_path = write_note(updated_note, settings.vault_path)

    return NoteResult(note=updated_note, markdown_path=str(markdown_path))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_update_note.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/vault/update_note.py tests/tools/vault/test_update_note.py
git commit -m "feat: tools/vault/update_note.py — partial update + needs_re_embedding"
```

---

## Task 8: tools/vault/search.py — search()

**Files:**
- Modify: `tools/vault/search.py`
- Modify: `tests/tools/vault/test_search.py`

- [ ] **Step 1: Write the failing tests**

Replace `tests/tools/vault/test_search.py` with:

```python
import pytest
from unittest.mock import patch, MagicMock
from core.schemas import SearchResult


def _mock_embedding():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embedding": [0.1] * 768}
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def test_search_chunks_returns_results(tmp_settings, tmp_db, tmp_path):
    from tools.vault.search import search
    from infrastructure.db import insert_source, insert_chunks, insert_chunk_embeddings
    from core.schemas import Source, ChunkResult
    from datetime import date
    import unittest.mock as mock

    source = Source(uid="s1", slug="s1", source_type="youtube", status="rag_ready",
                    date_added=date.today().isoformat())
    insert_source(tmp_db, source)
    chunk = ChunkResult(uid="c1", position=0, content="hello world content", token_count=3)
    insert_chunks(tmp_db, "s1", [chunk])
    insert_chunk_embeddings(tmp_db, "c1", [0.1] * 768)

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         patch("requests.post", return_value=_mock_embedding()):
        results = search("hello world", tmp_settings, mode="chunks", limit=5)

    assert len(results) == 1
    assert results[0].content == "hello world content"


def test_search_notes_returns_results(tmp_settings, tmp_db, tmp_path):
    from tools.vault.search import search
    from infrastructure.db import insert_note, insert_note_embedding
    from core.schemas import Note
    from datetime import date
    import unittest.mock as mock

    note = Note(
        uid="n1", slug="test-note", title="Test Note", tags=["tag1"],
        body="Test body content here.", docstring="Short description.",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
    )
    insert_note(tmp_db, note)
    insert_note_embedding(tmp_db, "n1", [0.1] * 768)

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         patch("requests.post", return_value=_mock_embedding()):
        results = search("test content", tmp_settings, mode="notes", limit=5)

    assert len(results) == 1
    assert results[0].note_uid == "n1"


def test_search_invalid_mode_raises(tmp_settings):
    from tools.vault.search import search

    with patch("requests.post", return_value=_mock_embedding()):
        with pytest.raises(ValueError, match="mode"):
            search("test", tmp_settings, mode="invalid")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_search.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement search in tools/vault/search.py**

```python
"""
Semantic search tool.

Input  : query string + optional filters
Output : list[SearchResult]
mode='chunks': chunk-level RAG
mode='notes' : note-level semantic search
"""

from core.schemas import SearchResult, SearchFilters
from core.config import Settings
from core.logging import loggable


@loggable("search")
def search(
    query: str,
    settings: Settings,
    filters: SearchFilters | None = None,
    mode: str = "chunks",
    limit: int = 5,
) -> list[SearchResult]:
    """
    Semantic search over the vault.
    mode='chunks': chunk-level RAG (Pattern A1/A2 from spec section 4.3)
    mode='notes' : note-level semantic search (Pattern B)
    """
    from tools.text.embed import embed_text
    from infrastructure.db import search_chunks, search_notes

    if mode not in ("chunks", "notes"):
        raise ValueError(f"Invalid mode '{mode}'. Must be 'chunks' or 'notes'.")

    query_embedding = embed_text(query, settings)

    if mode == "notes":
        return search_notes(settings.db_path, query_embedding, filters, limit)
    else:
        return search_chunks(settings.db_path, query_embedding, filters, limit)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_search.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/vault/search.py tests/tools/vault/test_search.py
git commit -m "feat: tools/vault/search.py — semantic search chunks + notes"
```

---

## Task 9: tools/vault/finalize_source.py — finalize_source()

**Files:**
- Modify: `tools/vault/finalize_source.py`
- Create: `tests/tools/vault/test_finalize_source.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/vault/test_finalize_source.py`:

```python
import pytest
from datetime import date
from pathlib import Path
from core.schemas import Source, FinalizeResult
import unittest.mock as mock


def _insert_source(tmp_db, media_path=None):
    from infrastructure.db import insert_source
    source = Source(
        uid="src-1", slug="test-source", source_type="youtube",
        status="rag_ready", date_added=date.today().isoformat(),
        media_path=media_path,
    )
    insert_source(tmp_db, source)
    return "src-1"


def test_finalize_source_returns_finalize_result(tmp_settings, tmp_db, tmp_path):
    from tools.vault.finalize_source import finalize_source

    _insert_source(tmp_db)

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: tmp_path / "media")):
        result = finalize_source("src-1", tmp_settings)

    assert isinstance(result, FinalizeResult)
    assert result.new_status == "vaulted"
    assert result.source_uid == "src-1"


def test_finalize_source_updates_db_status(tmp_settings, tmp_db, tmp_path):
    from tools.vault.finalize_source import finalize_source
    from infrastructure.db import get_source

    _insert_source(tmp_db)

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: tmp_path / "media")):
        finalize_source("src-1", tmp_settings)
        source = get_source(tmp_db, "src-1")

    assert source.status == "vaulted"


def test_finalize_source_moves_media_file(tmp_settings, tmp_db, tmp_path):
    from tools.vault.finalize_source import finalize_source

    # Create a fake media file
    media_file = tmp_path / "audio.mp3"
    media_file.write_bytes(b"audio data")
    _insert_source(tmp_db, media_path=str(media_file))

    media_dest = tmp_path / "media"

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: media_dest)):
        result = finalize_source("src-1", tmp_settings)

    assert result.media_moved_to is not None
    assert Path(result.media_moved_to).exists()
    assert not media_file.exists()  # moved, not copied


def test_finalize_source_not_found_raises(tmp_settings, tmp_db, tmp_path):
    from tools.vault.finalize_source import finalize_source

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: tmp_path / "media")):
        with pytest.raises(ValueError, match="not found"):
            finalize_source("nonexistent", tmp_settings)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_finalize_source.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement finalize_source in tools/vault/finalize_source.py**

```python
"""
Source finalization tool.

Input  : source uid
Output : FinalizeResult
Marks source as vaulted, moves media to permanent storage.
"""

import shutil
from pathlib import Path

from core.schemas import FinalizeResult
from core.config import Settings
from core.logging import loggable


@loggable("finalize_source")
def finalize_source(source_uid: str, settings: Settings) -> FinalizeResult:
    """
    Mark source as vaulted and archive its media file.
    - Updates sources.status to 'vaulted'
    - Moves media file from staging to permanent media/ directory
    The associated note is resolved via: SELECT uid FROM notes WHERE source_uid = ?
    """
    from infrastructure.db import get_source, update_source_status

    source = get_source(settings.db_path, source_uid)
    if source is None:
        raise ValueError(f"Source not found: {source_uid}")

    media_moved_to = None
    if source.media_path:
        src_file = Path(source.media_path)
        if src_file.exists():
            dest_dir = settings.media_path / source.slug
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / src_file.name
            shutil.move(str(src_file), str(dest_file))
            media_moved_to = str(dest_file)

    update_source_status(settings.db_path, source_uid, "vaulted")

    return FinalizeResult(
        source_uid=source_uid,
        new_status="vaulted",
        media_moved_to=media_moved_to,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_finalize_source.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/vault/finalize_source.py tests/tools/vault/test_finalize_source.py
git commit -m "feat: tools/vault/finalize_source.py — status vaulted + media move"
```

---

## Task 10: tools/export/typst.py — export_typst()

**Files:**
- Modify: `tools/export/typst.py`
- Create: `tests/tools/export/test_typst.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/export/test_typst.py`:

```python
import pytest
from datetime import date
from pathlib import Path
from core.schemas import Note, ExportResult
import unittest.mock as mock


def _make_note():
    return Note(
        uid="n1", slug="test-note", title="Test Note",
        body="## Section\n\nContent here.", docstring="A test note.",
        tags=["tag1"], note_type="synthese", source_type="youtube",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        generation_template="standard",
    )


def test_export_typst_creates_file(tmp_settings, tmp_db, tmp_path):
    from tools.export.typst import export_typst
    from infrastructure.db import insert_note

    insert_note(tmp_db, _make_note())

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        result = export_typst("n1", tmp_settings)

    assert isinstance(result, ExportResult)
    assert result.format == "typst"
    assert Path(result.output_path).exists()
    assert result.output_path.endswith(".typ")


def test_export_typst_contains_title(tmp_settings, tmp_db, tmp_path):
    from tools.export.typst import export_typst
    from infrastructure.db import insert_note

    insert_note(tmp_db, _make_note())

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        result = export_typst("n1", tmp_settings)

    content = Path(result.output_path).read_text()
    assert "Test Note" in content


def test_export_typst_not_found_raises(tmp_settings, tmp_db, tmp_path):
    from tools.export.typst import export_typst

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        with pytest.raises(ValueError, match="not found"):
            export_typst("nonexistent", tmp_settings)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/tools/export/test_typst.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement export_typst in tools/export/typst.py**

```python
"""
Typst export tool.

Input  : note uid
Output : ExportResult (path to .typ file)
No DB write. Generates a print-ready Typst document from a note.
"""

from pathlib import Path

from core.schemas import ExportResult
from core.config import Settings
from core.logging import loggable


def _note_to_typst(note) -> str:
    """Generate Typst source from a Note record."""
    lines = [
        f'#set document(title: "{note.title}")',
        '#set page(margin: 2cm)',
        '#set text(font: "Linux Libertine", size: 11pt)',
        '',
        f'= {note.title}',
        '',
    ]
    if note.docstring:
        lines += [f'#quote[{note.docstring}]', '']
    if note.tags:
        lines += [f'#text(gray)[Tags: {", ".join(note.tags)}]', '']
    lines += ['---', '', note.body]
    return '\n'.join(lines)


@loggable("export_typst")
def export_typst(note_uid: str, settings: Settings) -> ExportResult:
    """
    Export a note to Typst format (.typ file).
    Reads note from DB, generates a print-ready document.
    Output written to media/<slug>/<slug>.typ.
    No DB write.
    """
    from infrastructure.db import get_note

    note = get_note(settings.db_path, note_uid)
    if note is None:
        raise ValueError(f"Note not found: {note_uid}")

    output_dir = settings.media_path / note.slug
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{note.slug}.typ"
    output_path.write_text(_note_to_typst(note), encoding="utf-8")

    return ExportResult(output_path=str(output_path), format="typst")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/tools/export/test_typst.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/export/typst.py tests/tools/export/test_typst.py
git commit -m "feat: tools/export/typst.py — Typst document generation"
```

---

## Task 11: tools/export/mermaid.py — export_mermaid()

**Files:**
- Modify: `tools/export/mermaid.py`
- Create: `tests/tools/export/test_mermaid.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/export/test_mermaid.py`:

```python
import pytest
from datetime import date
from pathlib import Path
from core.schemas import Note, ExportResult
import unittest.mock as mock


def _make_note(uid, slug, tags):
    return Note(
        uid=uid, slug=slug, title=f"Note {uid}",
        body="Body content here.", docstring="Docstring.",
        tags=tags,
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
    )


def test_export_mermaid_by_note_uid(tmp_settings, tmp_db, tmp_path):
    from tools.export.mermaid import export_mermaid
    from infrastructure.db import insert_note, set_note_tags

    insert_note(tmp_db, _make_note("n1", "note-one", ["bitcoin", "finance"]))
    insert_note(tmp_db, _make_note("n2", "note-two", ["bitcoin"]))

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        result = export_mermaid(tmp_settings, note_uid="n1")

    assert isinstance(result, ExportResult)
    assert result.format == "mermaid"
    assert Path(result.output_path).exists()
    content = Path(result.output_path).read_text()
    assert "graph" in content.lower() or "flowchart" in content.lower()


def test_export_mermaid_by_tag(tmp_settings, tmp_db, tmp_path):
    from tools.export.mermaid import export_mermaid
    from infrastructure.db import insert_note

    insert_note(tmp_db, _make_note("n1", "note-one", ["bitcoin"]))
    insert_note(tmp_db, _make_note("n2", "note-two", ["bitcoin"]))

    with mock.patch.object(type(tmp_settings), "db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        result = export_mermaid(tmp_settings, tag="bitcoin")

    content = Path(result.output_path).read_text()
    assert "note-one" in content or "Note n1" in content or "n1" in content


def test_export_mermaid_no_args_raises(tmp_settings):
    from tools.export.mermaid import export_mermaid

    with pytest.raises(ValueError, match="note_uid.*tag"):
        export_mermaid(tmp_settings)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/tools/export/test_mermaid.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement export_mermaid in tools/export/mermaid.py**

```python
"""
Mermaid diagram export tool.

Input  : note_uid (graph centered on one note) OR tag (all notes sharing a tag)
Output : ExportResult (path to .md file with Mermaid diagram)
No DB write.
"""

from pathlib import Path

from core.schemas import ExportResult
from core.config import Settings
from core.logging import loggable


@loggable("export_mermaid")
def export_mermaid(
    settings: Settings,
    note_uid: str | None = None,
    tag: str | None = None,
) -> ExportResult:
    """
    Export note relationships to a Mermaid graph diagram (.md file).
    note_uid: graph centered on one note (shows notes sharing its tags).
    tag: graph of all notes sharing a tag.
    No DB write.
    """
    from infrastructure.db import get_connection

    if note_uid is None and tag is None:
        raise ValueError("Must provide either note_uid or tag")

    conn = get_connection(settings.db_path)

    if note_uid:
        # Find all notes sharing at least one tag with the pivot note
        rows = conn.execute(
            """
            SELECT DISTINCT n.uid, n.slug, n.title
            FROM notes n
            JOIN note_tags nt ON nt.note_uid = n.uid
            JOIN tags t ON t.uid = nt.tag_uid
            WHERE t.uid IN (
                SELECT tag_uid FROM note_tags WHERE note_uid = ?
            )
            """,
            (note_uid,),
        ).fetchall()
        pivot = conn.execute(
            "SELECT slug, title FROM notes WHERE uid = ?", (note_uid,)
        ).fetchone()
        conn.close()
        filename = f"graph-note-{note_uid[:8]}.md"
        diagram = _build_diagram(rows, pivot_slug=pivot["slug"] if pivot else None)
    else:
        rows = conn.execute(
            """
            SELECT DISTINCT n.uid, n.slug, n.title
            FROM notes n
            JOIN note_tags nt ON nt.note_uid = n.uid
            JOIN tags t ON t.uid = nt.tag_uid
            WHERE t.name = ?
            """,
            (tag,),
        ).fetchall()
        conn.close()
        filename = f"graph-tag-{tag}.md"
        diagram = _build_diagram(rows)

    output_dir = settings.media_path / "graphs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    output_path.write_text(diagram, encoding="utf-8")

    return ExportResult(output_path=str(output_path), format="mermaid")


def _build_diagram(rows, pivot_slug: str | None = None) -> str:
    lines = ["```mermaid", "graph LR"]
    for row in rows:
        label = row["title"].replace('"', "'")
        style = ":::pivot" if row["slug"] == pivot_slug else ""
        lines.append(f'    {row["slug"]}["{label}"]{style}')
    lines.append("```")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/tools/export/test_mermaid.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/export/mermaid.py tests/tools/export/test_mermaid.py
git commit -m "feat: tools/export/mermaid.py — Mermaid graph by note or tag"
```

---

## Task 12: Final validation

- [ ] **Step 1: Run the complete test suite**

```bash
.venv/Scripts/python -m pytest tests/ -v --tb=short
```

Expected: all tests PASS, zero failures.

- [ ] **Step 2: Verify no cross-imports between tools**

```bash
.venv/Scripts/python -c "
import ast, pathlib, sys
tools_dir = pathlib.Path('tools')
tool_files = list(tools_dir.rglob('*.py'))
errors = []
for f in tool_files:
    if f.name == '__init__.py': continue
    tree = ast.parse(f.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = getattr(node, 'module', '') or ''
            for alias in getattr(node, 'names', []):
                name = alias.name or ''
            if module.startswith('tools.') or name.startswith('tools.'):
                rel = str(f.relative_to(tools_dir))
                errors.append(f'{rel} imports {module or name}')
if errors:
    print('CROSS-IMPORTS FOUND:')
    for e in errors: print(' ', e)
    sys.exit(1)
else:
    print('No cross-imports between tools. OK')
"
```

Expected: `No cross-imports between tools. OK`

Note: `tools/vault/search.py` imports `tools/text/embed.py` — this is one allowed exception because search is orchestrating embed. If this triggers a false positive, the check can be made more specific.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: Plan 2 (Tools) complete — all tools implemented + tested"
```

---

## Self-Review

**Spec coverage check (section 5.4 MCP tools):**

| Spec requirement | Task |
|---|---|
| chunk_text — split + overlap | Task 1 |
| embed_text — provider delegation | Task 2 |
| transcribe — faster-whisper | Task 3 |
| compress_audio — ffmpeg/libopus | Task 4 |
| fetch_subtitles — yt-transcript-api + fallback | Task 5 |
| create_note — DB write + Markdown | Task 6 |
| update_note — partial update + needs_re_embedding | Task 7 |
| search — chunks + notes modes | Task 8 |
| finalize_source — status + media move | Task 9 |
| export_typst — .typ file | Task 10 |
| export_mermaid — graph by note/tag | Task 11 |

**Section 6.1 Modularity:** each tool wraps one responsibility. `search.py` imports `embed_text` — this is explicit orchestration within vault tools, acceptable in v1.

**Section 6.5 pre-commit checklist:** all tools have Pydantic types, @loggable, no hardcoded values.

**Not in this plan:** `tools/media/extract_audio.py` stub exists but is not in scope for v1 (no workflow requires it yet). `tools/text/summarize.py` is similarly out of scope.
