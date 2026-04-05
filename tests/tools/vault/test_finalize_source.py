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


def test_finalize_source_returns_finalize_result(ctx):
    from tools.vault.finalize_source import finalize_source

    _insert_source(ctx.db._db_path)

    result = finalize_source("src-1", ctx)

    assert isinstance(result, FinalizeResult)
    assert result.new_status == "vaulted"
    assert result.source_uid == "src-1"


def test_finalize_source_updates_db_status(ctx):
    from tools.vault.finalize_source import finalize_source

    _insert_source(ctx.db._db_path)

    finalize_source("src-1", ctx)
    source = ctx.db.get_source("src-1")

    assert source.status == "vaulted"


def test_finalize_source_moves_media_file(ctx, tmp_path):
    from tools.vault.finalize_source import finalize_source
    from core.context import VaultContext

    # Create a fake media file in a staging directory
    staging = tmp_path / "staging"
    staging.mkdir()
    media_file = staging / "audio.mp3"
    media_file.write_bytes(b"audio data")
    _insert_source(ctx.db._db_path, media_path=str(media_file))

    # Build a context with a distinct media_path to verify file was moved there
    media_dest = tmp_path / "media_dest"
    media_dest.mkdir()
    ctx_with_media = VaultContext(
        settings=ctx.settings,
        db=ctx.db,
        system_db_path=ctx.system_db_path,
        embed=ctx.embed,
        generate=ctx.generate,
        write_note=ctx.write_note,
        vault_path=ctx.vault_path,
        media_path=media_dest,
    )

    result = finalize_source("src-1", ctx_with_media)

    assert result.media_moved_to is not None
    assert Path(result.media_moved_to).exists()
    assert not media_file.exists()  # moved, not copied


def test_finalize_source_not_found_raises(ctx):
    from tools.vault.finalize_source import finalize_source

    with pytest.raises(NotFoundError):
        finalize_source("nonexistent", ctx)
