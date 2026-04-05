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
