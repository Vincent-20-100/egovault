from pathlib import Path
from tests.conftest import make_note
from scripts.clean_sources import find_unreferenced_sources, list_archive


def _make_source(vault, slug):
    d = vault / "sources" / slug
    d.mkdir(parents=True)
    (d / "source.md").write_text("---\nnote_creee: ''\n---\n", encoding="utf-8")


def test_source_referencee_nest_pas_orpheline(vault):
    _make_source(vault, "2026-03-19-bitcoin")
    make_note(vault, "notes", "2026-03-19-note.md", tags=["bitcoin"])
    note = vault / "notes" / "2026-03-19-note.md"
    content = note.read_text(encoding="utf-8").replace(
        "tags: ['bitcoin']",
        "tags: ['bitcoin']\nsource: \"[[sources/2026-03-19-bitcoin/source.md]]\""
    )
    note.write_text(content, encoding="utf-8")
    orphans = find_unreferenced_sources(vault)
    assert "2026-03-19-bitcoin" not in orphans


def test_source_non_referencee_est_orpheline(vault):
    _make_source(vault, "2026-03-19-orphan")
    orphans = find_unreferenced_sources(vault)
    assert "2026-03-19-orphan" in orphans


def test_liste_archive(vault):
    archive_dir = vault / "sources" / "raw-sources" / "_archive" / "2026-03-19-old"
    archive_dir.mkdir(parents=True)
    items = list_archive(vault)
    assert "2026-03-19-old" in items
