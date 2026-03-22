import re
from pathlib import Path
from scripts.ingest._core import slug, make_drop_off, set_status, find_duplicate
from scripts.ingest._core import STATUS_PENDING, STATUS_READY, STATUS_FAILED


def test_slug_supprime_accents():
    assert slug("l'indicateur ultime pour Bitcoin") == "l-indicateur-ultime-pour-bitcoin"


def test_slug_respecte_max_len():
    assert len(slug("a" * 100)) <= 50


def test_slug_minuscules():
    assert slug("Bitcoin MVRV") == "bitcoin-mvrv"


def test_make_drop_off_cree_dossier(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.ingest._core.RAW_SOURCES", tmp_path)
    folder = make_drop_off("Test Titre", "video", url="https://example.com")
    assert folder.exists()
    assert (folder / "source.md").exists()


def test_make_drop_off_source_md_contient_status(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.ingest._core.RAW_SOURCES", tmp_path)
    folder = make_drop_off("Test", "video", url="https://example.com")
    content = (folder / "source.md").read_text(encoding="utf-8")
    assert f"status: {STATUS_PENDING}" in content
    assert "note_creee" in content


def test_set_status_met_a_jour_source_md(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.ingest._core.RAW_SOURCES", tmp_path)
    folder = make_drop_off("Test", "video")
    set_status(folder, STATUS_READY)
    content = (folder / "source.md").read_text(encoding="utf-8")
    assert f"status: {STATUS_READY}" in content
    assert STATUS_PENDING not in content


def test_find_duplicate_detecte_url_existante(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.ingest._core.RAW_SOURCES", tmp_path)
    url = "https://youtube.com/watch?v=abc123"
    make_drop_off("Test", "video", url=url)
    result = find_duplicate(url, tmp_path)
    assert result is not None


def test_find_duplicate_retourne_none_si_absent(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.ingest._core.RAW_SOURCES", tmp_path)
    result = find_duplicate("https://youtube.com/watch?v=xyz", tmp_path)
    assert result is None


def test_find_duplicate_ignore_archive(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.ingest._core.RAW_SOURCES", tmp_path)
    url = "https://youtube.com/watch?v=abc123"
    archive = tmp_path / "_archive" / "2026-03-19-old"
    archive.mkdir(parents=True)
    (archive / "source.md").write_text(f"---\nurl: \"{url}\"\n---\n", encoding="utf-8")
    result = find_duplicate(url, tmp_path)
    assert result is None
