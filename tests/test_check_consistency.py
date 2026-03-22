from pathlib import Path
from scripts.check_consistency import run_checks


def test_detecte_tag_avec_accent(vault):
    note = vault / "notes" / "2026-03-19-test.md"
    note.write_text(
        "---\ndate_creation: 2026-03-19\ndate_modification: 2026-03-19\n"
        "note_type: synthese\nsource_type: personnel\ndepth: note\n"
        "tags: [économie]\n---\n# Test\n", encoding="utf-8"
    )
    issues = run_checks(vault)
    assert any("économie" in i for i in issues["bad_tags"])


def test_detecte_frontmatter_incomplet(vault):
    note = vault / "notes" / "2026-03-19-test.md"
    note.write_text("---\ntags: [bitcoin]\n---\n# Test\n", encoding="utf-8")
    issues = run_checks(vault)
    assert any("date_creation" in i for i in issues["missing_fields"])


def test_detecte_lien_vers_fichier_inexistant(vault):
    note = vault / "notes" / "2026-03-19-test.md"
    note.write_text(
        "---\ndate_creation: 2026-03-19\ndate_modification: 2026-03-19\n"
        "note_type: synthese\nsource_type: personnel\ndepth: note\n"
        "tags: [bitcoin]\n---\n\n[[inexistant/fichier-qui-nexiste-pas]]\n",
        encoding="utf-8"
    )
    issues = run_checks(vault)
    assert any("inexistant" in i for i in issues["broken_links"])


def test_pas_derreur_sur_note_valide(vault):
    note = vault / "notes" / "2026-03-19-valide.md"
    note.write_text(
        "---\ndate_creation: 2026-03-19\ndate_modification: 2026-03-19\n"
        "note_type: synthese\nsource_type: personnel\ndepth: note\n"
        "tags: [bitcoin]\n---\n# Valide\n", encoding="utf-8"
    )
    issues = run_checks(vault)
    assert issues.get("bad_tags", []) == []
    assert issues.get("missing_fields", []) == []


def test_invalid_note_type_detecte(tmp_path):
    (tmp_path / "notes").mkdir()
    note = tmp_path / "notes" / "2026-01-01-test.md"
    note.write_text(
        "---\ndate_creation: 2026-01-01\ndate_modification: 2026-01-01\n"
        "note_type: truc\nsource_type: personnel\ndepth: note\ntags: []\n---\n"
    )
    issues = run_checks(tmp_path)
    assert any("note_type" in i for i in issues.get("invalid_values", []))


def test_invalid_source_type_detecte(tmp_path):
    (tmp_path / "notes").mkdir()
    note = tmp_path / "notes" / "2026-01-01-test.md"
    note.write_text(
        "---\ndate_creation: 2026-01-01\ndate_modification: 2026-01-01\n"
        "note_type: idee\nsource_type: inconnu\ndepth: note\ntags: []\n---\n"
    )
    issues = run_checks(tmp_path)
    assert any("source_type" in i for i in issues.get("invalid_values", []))


def test_invalid_depth_detecte(tmp_path):
    (tmp_path / "notes").mkdir()
    note = tmp_path / "notes" / "2026-01-01-test.md"
    note.write_text(
        "---\ndate_creation: 2026-01-01\ndate_modification: 2026-01-01\n"
        "note_type: idee\nsource_type: personnel\ndepth: ultra-long\ntags: []\n---\n"
    )
    issues = run_checks(tmp_path)
    assert any("depth" in i for i in issues.get("invalid_values", []))
