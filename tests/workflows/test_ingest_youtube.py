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
         patch("workflows.ingest_youtube.embed_text", return_value=[0.1] * 768):

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
