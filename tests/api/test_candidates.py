import pytest
from datetime import datetime, timezone
from tests.conftest import make_embedding
from core.schemas import Source, NoteCandidate, ChunkResult
from infrastructure.db import insert_source, insert_note_candidates, insert_chunks


def _seed_candidate_data(tmp_settings):
    db_path = tmp_settings.vault_db_path
    src = Source(
        uid="src-api-1",
        slug="src-api-1",
        source_type="texte",
        status="rag_ready",
        date_added="2026-08-15",
    )
    insert_source(db_path, src)

    chunks = [
        ChunkResult(uid="chk-1", position=0, content="Content 1", token_count=5),
        ChunkResult(uid="chk-2", position=1, content="Content 2", token_count=5),
    ]
    insert_chunks(db_path, "src-api-1", chunks)

    now = datetime.now(timezone.utc).isoformat()
    cand = NoteCandidate(
        uid="cand-api-1",
        source_uid="src-api-1",
        sequence_index=0,
        chunk_uids=["chk-1", "chk-2"],
        label="API Candidate Label",
        locator="chunk 0-1",
        status="queued",
        model_version="v2",
        created_at=now,
    )
    insert_note_candidates(db_path, [cand])


def test_candidates_api_lifecycle(client, tmp_settings):
    ctx = client.app.state.ctx
    orig_embed = ctx.embed
    ctx.embed = lambda t: make_embedding(0.1)

    try:
        _seed_candidate_data(tmp_settings)

        # 1. GET /candidates
        res = client.get("/candidates")
        assert res.status_code == 200
        cands = res.json()
        assert len(cands) >= 1
        target = next((c for c in cands if c["uid"] == "cand-api-1"), None)
        assert target is not None
        assert target["status"] == "queued"

        # 2. GET /candidates/{uid}
        res = client.get("/candidates/cand-api-1")
        assert res.status_code == 200
        assert res.json()["label"] == "API Candidate Label"

        # 3. POST /candidates/{uid}/claim
        res = client.post("/candidates/cand-api-1/claim", json={"session_id": "test_agent", "is_human": False})
        assert res.status_code == 200
        assert res.json()["status"] == "in_progress"
        assert res.json()["claimed_by"] == "test_agent"

        # 4. POST /candidates/{uid}/convert
        res = client.post(
            "/candidates/cand-api-1/convert",
            json={
                "title": "Synthesized Note from API",
                "docstring": "Summary line",
                "body": "Long body content with enough length.",
                "tags": ["tag-api"],
                "session_id": "test_agent",
            },
        )
        assert res.status_code == 200
        note_data = res.json()
        assert note_data["candidate_uid"] == "cand-api-1"
        assert note_data["review_status"] == "unreviewed"
        note_uid = note_data["uid"]

        # 5. POST /notes/{uid}/review
        res = client.post(f"/notes/{note_uid}/review?review_status=reviewed")
        assert res.status_code == 200
        assert res.json()["review_status"] == "reviewed"

        # 6. GET /chunks
        res = client.get("/chunks?uids=chk-1&uids=chk-2")
        assert res.status_code == 200
        chunks = res.json()
        assert len(chunks) == 2
        assert chunks[0]["uid"] == "chk-1"

        # 7. POST /candidates/{uid}/skip
        cand2 = NoteCandidate(
            uid="cand-api-skip",
            source_uid="src-api-1",
            sequence_index=1,
            chunk_uids=["chk-1"],
            label="Skip candidate",
            status="queued",
            model_version="v2",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        insert_note_candidates(tmp_settings.vault_db_path, [cand2])
        res_skip = client.post("/candidates/cand-api-skip/skip")
        assert res_skip.status_code == 200
        assert res_skip.json()["status"] == "skipped"

    finally:
        ctx.embed = orig_embed
