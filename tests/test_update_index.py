from tests.conftest import make_note
from scripts.update_index import build_index, write_index


def test_index_liste_tags_depuis_frontmatter(vault):
    make_note(vault, "notes", "2026-03-19-bitcoin.md",
              tags=["bitcoin", "investissement"])
    result = build_index(vault)
    assert "bitcoin" in result["tags"]
    assert "investissement" in result["tags"]


def test_index_note_sans_liens_est_orpheline(vault):
    make_note(vault, "notes", "2026-03-19-idee.md",
              tags=["python"])
    result = build_index(vault)
    assert "2026-03-19-idee.md" in result["orphelines"]


def test_index_note_avec_lien_nest_pas_orpheline(vault):
    make_note(vault, "notes", "2026-03-19-note.md",
              tags=["bitcoin"],
              links=["notes/2026-03-19-idee"])
    result = build_index(vault)
    assert "2026-03-19-note.md" not in result["orphelines"]


def test_index_plusieurs_notes_meme_tag(vault):
    make_note(vault, "notes", "2026-03-19-a.md", tags=["bitcoin"])
    make_note(vault, "notes", "2026-03-19-b.md", tags=["bitcoin"])
    result = build_index(vault)
    assert len(result["tags"]["bitcoin"]) == 2


def test_write_index_produit_fichier_markdown(vault):
    make_note(vault, "notes", "2026-03-19-note.md", tags=["test"])
    write_index(vault)
    index_path = vault / "_index.md"
    assert index_path.exists()
    content = index_path.read_text(encoding="utf-8")
    assert "`test`" in content
    assert "Dernière mise à jour" in content
