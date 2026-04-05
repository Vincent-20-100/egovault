import pytest


def test_job_response_shape():
    from api.models import JobResponse
    job = JobResponse(
        id="abc", status="pending", job_type="youtube",
        created_at="2026-01-01T00:00:00",
    )
    assert job.id == "abc"
    assert job.result is None
    assert job.error is None


def test_note_list_item_shape():
    from api.models import NoteListItem
    note = NoteListItem(
        uid="n1", slug="my-note", title="My Note",
        note_type="synthese", rating=4,
        tags=["tag-1"], date_created="2026-01-01",
    )
    assert note.rating == 4


def test_search_result_response_shape():
    from api.models import SearchResultResponse
    r = SearchResultResponse(
        note_uid="n1", slug="my-note", title="My Note",
        score=0.87, excerpt="Some text excerpt.",
    )
    assert r.score == 0.87


def test_note_patch_validates_rating():
    from api.models import NotePatch
    with pytest.raises(Exception):
        NotePatch(rating=6)  # out of range


def test_note_patch_allows_partial():
    from api.models import NotePatch
    patch = NotePatch(rating=3)
    assert patch.tags is None
