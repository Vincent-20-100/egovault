import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from tests.conftest import make_embedding

from core.schemas import SubtitleResult, ChunkResult, Source, NoteResult, Note
from core.errors import LargeFormatError


def _make_note_result(source_uid="src-gen"):
    note = Note(
        uid="note-gen", source_uid=source_uid, slug="generated-note",
        note_type=None, source_type=None, generation_template="standard",
        rating=None, sync_status="synced", title="Generated", docstring="desc",
        body="body content here", url=None, status="draft",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test-tag"],
    )
    return NoteResult(note=note, markdown_path="/vault/generated-note.md")


def _make_settings_with_db(tmp_settings, tmp_db):
    return tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )


def _make_subtitle_result(text="Hello world transcript here."):
    return SubtitleResult(text=text, language="fr", source="subtitles")


def _make_chunk(uid="c1", pos=0, text="chunk content here"):
    return ChunkResult(uid=uid, position=pos, content=text, token_count=3)


def test_ingest_youtube_returns_source(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )

    with patch("workflows.ingest_youtube.fetch_subtitles", return_value=_make_subtitle_result()), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=make_embedding()):

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
         patch("workflows.ingest_youtube.embed_text", return_value=make_embedding()):

        result = ingest_youtube("https://youtube.com/watch?v=abc123", settings)

    stored = get_source(tmp_db, result.uid)
    assert stored.status == "rag_ready"
    assert stored.transcript == "Hello world transcript here."


def test_ingest_youtube_chunks_stored(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube
    from infrastructure.db import get_vault_connection

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
         patch("workflows.ingest_youtube.embed_text", return_value=make_embedding()):

        result = ingest_youtube("https://youtube.com/watch?v=xyz", settings)

    conn = get_vault_connection(tmp_db)
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
         patch("workflows.ingest_youtube.embed_text", return_value=make_embedding()):

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
         patch("workflows.ingest_youtube.embed_text", return_value=make_embedding()):

        with pytest.raises(LargeFormatError) as exc_info:
            ingest_youtube("https://youtube.com/watch?v=big2", settings)
        source_uid_holder["uid"] = exc_info.value.source_uid

    stored = get_source(tmp_db, source_uid_holder["uid"])
    assert stored.status == "rag_ready"


def test_ingest_youtube_auto_generate_true_creates_draft(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube

    settings = _make_settings_with_db(tmp_settings, tmp_db)

    with patch("workflows.ingest_youtube.fetch_subtitles", return_value=_make_subtitle_result()), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=make_embedding()), \
         patch("workflows.ingest_youtube._llm_is_configured", return_value=True), \
         patch("workflows.ingest_youtube.generate_note_from_source",
               return_value=_make_note_result()) as mock_gen:

        result = ingest_youtube("https://youtube.com/watch?v=abc", settings,
                                auto_generate_note=True)

    assert result.status == "rag_ready"
    mock_gen.assert_called_once()


def test_ingest_youtube_auto_generate_false_skips_note(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube

    settings = _make_settings_with_db(tmp_settings, tmp_db)

    with patch("workflows.ingest_youtube.fetch_subtitles", return_value=_make_subtitle_result()), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=make_embedding()), \
         patch("workflows.ingest_youtube.generate_note_from_source") as mock_gen:

        result = ingest_youtube("https://youtube.com/watch?v=skip", settings,
                                auto_generate_note=False)

    assert result.status == "rag_ready"
    mock_gen.assert_not_called()


def test_ingest_youtube_auto_generate_none_reads_config_true(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube

    settings = _make_settings_with_db(tmp_settings, tmp_db)
    settings_with_flag = settings.model_copy(
        update={"user": settings.user.model_copy(
            update={"llm": settings.user.llm.model_copy(
                update={"auto_generate_note": True}
            )}
        )}
    )

    with patch("workflows.ingest_youtube.fetch_subtitles", return_value=_make_subtitle_result()), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=make_embedding()), \
         patch("workflows.ingest_youtube._llm_is_configured", return_value=True), \
         patch("workflows.ingest_youtube.generate_note_from_source",
               return_value=_make_note_result()) as mock_gen:

        ingest_youtube("https://youtube.com/watch?v=cfg", settings_with_flag,
                       auto_generate_note=None)

    mock_gen.assert_called_once()


def test_ingest_youtube_auto_generate_none_reads_config_false(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube

    settings = _make_settings_with_db(tmp_settings, tmp_db)

    with patch("workflows.ingest_youtube.fetch_subtitles", return_value=_make_subtitle_result()), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=make_embedding()), \
         patch("workflows.ingest_youtube.generate_note_from_source") as mock_gen:

        ingest_youtube("https://youtube.com/watch?v=cfg2", settings,
                       auto_generate_note=None)

    mock_gen.assert_not_called()


def test_ingest_youtube_llm_not_configured_skips_note(tmp_settings, tmp_db, caplog):
    import logging
    from workflows.ingest_youtube import ingest_youtube

    settings = _make_settings_with_db(tmp_settings, tmp_db)

    with patch("workflows.ingest_youtube.fetch_subtitles", return_value=_make_subtitle_result()), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=make_embedding()), \
         patch("workflows.ingest_youtube._llm_is_configured", return_value=False), \
         patch("workflows.ingest_youtube.generate_note_from_source") as mock_gen, \
         caplog.at_level(logging.INFO, logger="workflows.ingest_youtube"):

        result = ingest_youtube("https://youtube.com/watch?v=nollm", settings,
                                auto_generate_note=True)

    assert result.status == "rag_ready"
    mock_gen.assert_not_called()
    assert any("LLM not configured" in r.message for r in caplog.records)


def test_ingest_youtube_large_format_skips_note_and_raises(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube
    from core.errors import LargeFormatError

    settings = _make_settings_with_db(tmp_settings, tmp_db)
    big_text = " ".join(["word"] * 50001)

    with patch("workflows.ingest_youtube.fetch_subtitles",
               return_value=_make_subtitle_result(big_text)), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=make_embedding()), \
         patch("workflows.ingest_youtube.generate_note_from_source") as mock_gen:

        with pytest.raises(LargeFormatError):
            ingest_youtube("https://youtube.com/watch?v=big3", settings,
                           auto_generate_note=True)

    mock_gen.assert_not_called()
