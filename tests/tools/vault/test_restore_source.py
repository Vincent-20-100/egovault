import pytest
from unittest.mock import patch
from core.errors import NotFoundError, ConflictError
from core.schemas import RestoreSourceResult


def _make_source(status="pending_deletion"):
    from core.schemas import Source
    return Source(
        uid="suid-1", slug="test-source", source_type="youtube",
        status=status, date_added="2026-03-30",
    )


def test_restore_source_success(tmp_settings):
    source = _make_source()
    with patch("infrastructure.db.get_source", return_value=source), \
         patch("infrastructure.db.restore_source", return_value="rag_ready") as mock_restore:
        from tools.vault.restore_source import restore_source
        result = restore_source("suid-1", tmp_settings)
    assert result.uid == "suid-1"
    assert result.restored_status == "rag_ready"


def test_restore_source_not_found(tmp_settings):
    with patch("infrastructure.db.get_source", return_value=None):
        from tools.vault.restore_source import restore_source
        with pytest.raises(NotFoundError):
            restore_source("nonexistent", tmp_settings)


def test_restore_source_not_pending(tmp_settings):
    source = _make_source(status="rag_ready")
    with patch("infrastructure.db.get_source", return_value=source):
        from tools.vault.restore_source import restore_source
        with pytest.raises(ConflictError):
            restore_source("suid-1", tmp_settings)
