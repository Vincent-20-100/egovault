from pathlib import Path
from tests.conftest import make_note
from scripts.vault_status import get_status, write_status


def test_compte_notes_par_dossier(vault):
    make_note(vault, "notes", "2026-03-19-a.md", tags=["bitcoin"])
    make_note(vault, "notes", "2026-03-19-b.md", tags=["python"])
    status = get_status(vault)
    assert status["notes"]["notes"] == 2


def test_detecte_raw_sources_en_attente(vault):
    raw = vault / "sources" / "raw-sources" / "2026-03-20-test"
    raw.mkdir(parents=True)
    (raw / "source.md").write_text("---\nnote_creee: ''\n---\n", encoding="utf-8")
    status = get_status(vault)
    assert any(s["name"] == "2026-03-20-test" for s in status["raw_pending"])


def test_archive_ignoree_dans_pending(vault):
    archive = vault / "sources" / "raw-sources" / "_archive" / "2026-03-19-old"
    archive.mkdir(parents=True)
    status = get_status(vault)
    assert len(status["raw_pending"]) == 0


def test_status_drop_off_distingue_ready_et_pending(vault):
    raw = vault / "sources" / "raw-sources" / "2026-03-20-test-ready"
    raw.mkdir(parents=True)
    (raw / "source.md").write_text(
        "---\nnote_creee: ''\nstatus: ready\n---\n", encoding="utf-8"
    )
    raw2 = vault / "sources" / "raw-sources" / "2026-03-20-test-pending"
    raw2.mkdir(parents=True)
    (raw2 / "source.md").write_text(
        "---\nnote_creee: ''\nstatus: pending\n---\n", encoding="utf-8"
    )
    status = get_status(vault)
    ready = [s for s in status["raw_pending"] if s.get("status") == "ready"]
    pending = [s for s in status["raw_pending"] if s.get("status") == "pending"]
    assert len(ready) == 1
    assert len(pending) == 1


def test_produit_fichier_status_md(vault):
    write_status(vault)
    assert (vault.parent / "_status.md").exists()
    content = (vault.parent / "_status.md").read_text(encoding="utf-8")
    assert "VAULT STATUS" in content
