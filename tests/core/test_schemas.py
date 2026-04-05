import pytest
from pydantic import ValidationError
from core.schemas import NoteContentInput


# Helper: minimal valid NoteContentInput data (no taxonomy context needed for tag tests)
def _base():
    return {
        "title": "Test Note",
        "docstring": "A test note.",
        "body": "Some body content here.",
        "tags": ["valid-tag"],
    }


def test_tags_valid():
    data = {**_base(), "tags": ["decentralisation", "bitcoin", "monnaie-numerique"]}
    note = NoteContentInput(**data)
    assert note.tags == ["decentralisation", "bitcoin", "monnaie-numerique"]


def test_tags_empty_string_rejected():
    with pytest.raises(ValidationError, match="empty"):
        NoteContentInput(**{**_base(), "tags": [""]})


def test_tags_uppercase_rejected():
    with pytest.raises(ValidationError, match="lowercase"):
        NoteContentInput(**{**_base(), "tags": ["Bitcoin"]})


def test_tags_accent_rejected():
    with pytest.raises(ValidationError, match="ASCII"):
        NoteContentInput(**{**_base(), "tags": ["décentralisation"]})


def test_tags_spaces_rejected():
    with pytest.raises(ValidationError, match="kebab"):
        NoteContentInput(**{**_base(), "tags": ["tag avec espaces"]})


def test_tags_underscore_rejected():
    with pytest.raises(ValidationError, match="kebab"):
        NoteContentInput(**{**_base(), "tags": ["tag_underscore"]})


def test_tags_too_long_rejected():
    with pytest.raises(ValidationError, match="80"):
        NoteContentInput(**{**_base(), "tags": ["a" * 81]})


def test_tags_duplicates_rejected():
    with pytest.raises(ValidationError, match="duplicate"):
        NoteContentInput(**{**_base(), "tags": ["bitcoin", "bitcoin"]})


def test_tags_min_one_required():
    with pytest.raises(ValidationError):
        NoteContentInput(**{**_base(), "tags": []})


def test_tags_max_ten():
    # 10 tags is fine
    tags = [f"tag-{i}" for i in range(10)]
    note = NoteContentInput(**{**_base(), "tags": tags})
    assert len(note.tags) == 10

    # 11 tags fails
    with pytest.raises(ValidationError):
        NoteContentInput(**{**_base(), "tags": [f"tag-{i}" for i in range(11)]})


# ---- Taxonomy validation tests ----

def _taxonomy_ctx():
    """Minimal taxonomy context for model_validate."""
    return {
        "taxonomy": type("T", (), {
            "note_types": ["synthese", "concept"],
            "source_types": ["youtube", "audio"],
            "generation_templates": ["standard"],
        })()
    }


def test_taxonomy_valid_note_type():
    data = {**_base(), "note_type": "synthese"}
    note = NoteContentInput.model_validate(data, context=_taxonomy_ctx())
    assert note.note_type == "synthese"


def test_taxonomy_invalid_note_type():
    data = {**_base(), "note_type": "unknown-type"}
    with pytest.raises(ValidationError, match="note_type"):
        NoteContentInput.model_validate(data, context=_taxonomy_ctx())


def test_taxonomy_valid_source_type():
    data = {**_base(), "source_type": "youtube"}
    note = NoteContentInput.model_validate(data, context=_taxonomy_ctx())
    assert note.source_type == "youtube"


def test_taxonomy_invalid_source_type():
    data = {**_base(), "source_type": "telegram"}
    with pytest.raises(ValidationError, match="source_type"):
        NoteContentInput.model_validate(data, context=_taxonomy_ctx())


def test_taxonomy_none_values_skipped():
    # note_type=None and source_type=None should not be validated
    data = {**_base(), "note_type": None, "source_type": None}
    note = NoteContentInput.model_validate(data, context=_taxonomy_ctx())
    assert note.note_type is None
    assert note.source_type is None


def test_taxonomy_skipped_without_context():
    # When no context is provided, taxonomy validation is skipped
    data = {**_base(), "note_type": "totally-unknown"}
    note = NoteContentInput(**data)  # no model_validate, no context
    assert note.note_type == "totally-unknown"
