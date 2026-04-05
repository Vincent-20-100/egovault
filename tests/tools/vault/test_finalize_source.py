import pytest
from datetime import date
from pathlib import Path
from core.schemas import Source, FinalizeResult
from core.errors import NotFoundError
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

    with mock.patch.object(type(tmp_settings), "vault_db_path",
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

    with mock.patch.object(type(tmp_settings), "vault_db_path",
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

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: media_dest)):
        result = finalize_source("src-1", tmp_settings)

    assert result.media_moved_to is not None
    assert Path(result.media_moved_to).exists()
    assert not media_file.exists()  # moved, not copied


def test_finalize_source_not_found_raises(tmp_settings, tmp_db, tmp_path):
    from tools.vault.finalize_source import finalize_source

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: tmp_path / "media")):
        with pytest.raises(NotFoundError):
            finalize_source("nonexistent", tmp_settings)
