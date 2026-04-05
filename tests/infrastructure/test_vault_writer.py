import pytest
from pathlib import Path
from core.schemas import Note


def _make_note(**overrides):
    data = {
        "uid": "note-uid-1",
        "source_uid": "src-uid-abc",
        "slug": "test-note",
        "note_type": "synthese",
        "source_type": "youtube",
        "generation_template": "standard",
        "rating": 4,
        "sync_status": "synced",
        "title": "Test Note Title",
        "docstring": "What, why, thesis.",
        "body": "## Section\n\nBody content here.",
        "url": None,
        "date_created": "2026-03-26",
        "date_modified": "2026-03-26",
        "tags": ["bitcoin", "decentralisation"],
    }
    data.update(overrides)
    return Note(**data)


def test_write_note_creates_file(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    path = write_note(note, tmp_path)
    assert path.exists()
    assert path.name == "test-note.md"


def test_frontmatter_system_zone(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    path = write_note(note, tmp_path)
    content = path.read_text(encoding="utf-8")

    assert "uid: note-uid-1" in content
    assert "date_created: 2026-03-26" in content
    assert "source_uid: src-uid-abc" in content
    assert "generation_template: standard" in content
    assert "DO NOT EDIT" in content


def test_frontmatter_content_zone(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    path = write_note(note, tmp_path)
    content = path.read_text(encoding="utf-8")

    assert "date_modified: 2026-03-26" in content
    assert "note_type: synthese" in content
    assert "source_type: youtube" in content
    assert "rating: 4" in content
    assert "bitcoin" in content
    assert "decentralisation" in content


def test_frontmatter_system_before_content(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    content = write_note(note, tmp_path).read_text()
    uid_pos = content.index("uid:")
    date_mod_pos = content.index("date_modified:")
    assert uid_pos < date_mod_pos  # SYSTEM before CONTENT


def test_body_contains_h1_title(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    content = write_note(note, tmp_path).read_text()
    assert "# Test Note Title" in content


def test_body_contains_docstring_quote(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    content = write_note(note, tmp_path).read_text()
    assert "> What, why, thesis." in content


def test_body_contains_note_body(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    content = write_note(note, tmp_path).read_text()
    assert "## Section" in content
    assert "Body content here." in content


def test_null_fields_not_in_frontmatter(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note(
        source_uid=None, generation_template=None, rating=None, url=None, source_type=None
    )
    content = write_note(note, tmp_path).read_text()
    assert "source_uid:" not in content
    assert "generation_template:" not in content
    assert "rating:" not in content
    assert "url:" not in content


def test_write_note_overwrites_existing(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    write_note(note, tmp_path)
    note2 = _make_note(title="Updated Title", body="New body content here.")
    write_note(note2, tmp_path)
    content = (tmp_path / "test-note.md").read_text()
    assert "Updated Title" in content
    assert "New body content here." in content


def test_frontmatter_quotes_url_with_special_chars():
    """URLs with colons and special chars must be quoted in YAML frontmatter."""
    from infrastructure.vault_writer import build_frontmatter

    note = _make_note(url='https://example.com/path?q=hello&t=42#section"quoted')
    result = build_frontmatter(note)
    # URL should be quoted
    assert 'url: "' in result
    # Internal quotes should be escaped
    assert '\\"quoted' in result
