import pytest
import time
from datetime import datetime, timezone
from core.schemas import Source, Note, NoteCandidate
from core.errors import CandidateClaimedError, ExpiredLockError


def _setup_source(ctx):
    src = Source(
        uid="s1", slug="src-1", source_type="texte", status="rag_ready", date_added="2026-08-15"
    )
    ctx.db.insert_source(src)
    return src


def test_note_candidates_crud(ctx):
    _setup_source(ctx)
    now = datetime.now(timezone.utc).isoformat()
    c1 = NoteCandidate(
        uid="cand1",
        source_uid="s1",
        sequence_index=0,
        chunk_uids=["c0", "c1"],
        label="Introduction",
        locator="chunk 0-1",
        status="queued",
        model_version="v2",
        created_at=now,
    )
    c2 = NoteCandidate(
        uid="cand2",
        source_uid="s1",
        sequence_index=1,
        chunk_uids=["c2", "c3"],
        label="Conclusion",
        locator="chunk 2-3",
        status="queued",
        model_version="v2",
        created_at=now,
    )
    ctx.db.insert_note_candidates([c1, c2])

    retrieved = ctx.db.get_note_candidate("cand1")
    assert retrieved is not None
    assert retrieved.uid == "cand1"
    assert retrieved.chunk_uids == ["c0", "c1"]
    assert retrieved.status == "queued"

    all_cands = ctx.db.list_note_candidates(source_uid="s1")
    assert len(all_cands) == 2
    assert all_cands[0].sequence_index == 0
    assert all_cands[1].sequence_index == 1


def test_claim_candidate_concurrency_and_ttl(ctx):
    _setup_source(ctx)
    now = datetime.now(timezone.utc).isoformat()
    cand = NoteCandidate(
        uid="cand_lock",
        source_uid="s1",
        sequence_index=0,
        chunk_uids=["c0"],
        label="Test Lock",
        status="queued",
        model_version="v2",
        created_at=now,
    )
    ctx.db.insert_note_candidates([cand])

    # Agent A claims candidate with 2s TTL
    claimed_a = ctx.db.claim_note_candidate("cand_lock", session_id="agent_a", ttl_seconds=2)
    assert claimed_a.status == "in_progress"
    assert claimed_a.claimed_by == "agent_a"

    # Agent B tries to claim concurrently -> raises CandidateClaimedError
    with pytest.raises(CandidateClaimedError) as exc_info:
        ctx.db.claim_note_candidate("cand_lock", session_id="agent_b", ttl_seconds=2)
    assert exc_info.value.context["claimed_by"] == "agent_a"

    # Agent A re-claims (idempotent / renew)
    claimed_a2 = ctx.db.claim_note_candidate("cand_lock", session_id="agent_a", ttl_seconds=2)
    assert claimed_a2.claimed_by == "agent_a"

    # Wait for TTL expiration (>2 seconds)
    time.sleep(2.1)

    # Now Agent B can steal the expired lock
    claimed_b = ctx.db.claim_note_candidate("cand_lock", session_id="agent_b", ttl_seconds=2)
    assert claimed_b.claimed_by == "agent_b"
    assert claimed_b.status == "in_progress"


def test_renew_and_release_candidate_lock(ctx):
    _setup_source(ctx)
    now = datetime.now(timezone.utc).isoformat()
    cand = NoteCandidate(
        uid="cand_rel",
        source_uid="s1",
        sequence_index=0,
        chunk_uids=["c0"],
        label="Test Release",
        status="queued",
        model_version="v2",
        created_at=now,
    )
    ctx.db.insert_note_candidates([cand])

    ctx.db.claim_note_candidate("cand_rel", session_id="agent_a", ttl_seconds=300)

    # Renew lock
    ctx.db.renew_candidate_lock("cand_rel", session_id="agent_a")

    # Renew from invalid session raises ExpiredLockError
    with pytest.raises(ExpiredLockError):
        ctx.db.renew_candidate_lock("cand_rel", session_id="agent_wrong")

    # Release lock
    ctx.db.release_note_candidate("cand_rel", session_id="agent_a")
    released = ctx.db.get_note_candidate("cand_rel")
    assert released.status == "queued"
    assert released.claimed_by is None


def test_atomic_create_note_from_candidate(ctx):
    _setup_source(ctx)
    now = datetime.now(timezone.utc).isoformat()
    cand = NoteCandidate(
        uid="cand_convert",
        source_uid="s1",
        sequence_index=0,
        chunk_uids=["c0", "c1"],
        label="Convert Me",
        status="queued",
        model_version="v2",
        created_at=now,
    )
    ctx.db.insert_note_candidates([cand])
    ctx.db.claim_note_candidate("cand_convert", session_id="agent_a", ttl_seconds=300)

    note = Note(
        uid="n_conv",
        source_uid="s1",
        slug="note-converted",
        note_type="synthese",
        source_type="texte",
        title="Converted Note Title",
        docstring="Docstring summary",
        body="Full converted body text exceeding minimum length.",
        date_created="2026-08-15",
        date_modified="2026-08-15",
        review_status="unreviewed",
        tags=["tag-conv"],
    )

    # Atomic creation succeeds
    created_note = ctx.db.create_note_from_candidate(note, "cand_convert", session_id="agent_a")
    assert created_note.candidate_uid == "cand_convert"

    # Candidate status is now converted
    cand_after = ctx.db.get_note_candidate("cand_convert")
    assert cand_after.status == "converted"
    assert cand_after.converted_note_uid == "n_conv"

    # Note exists in DB with candidate_uid and review_status
    note_in_db = ctx.db.get_note("n_conv")
    assert note_in_db is not None
    assert note_in_db.candidate_uid == "cand_convert"
    assert note_in_db.review_status == "unreviewed"
    assert "tag-conv" in note_in_db.tags


def test_atomic_create_note_with_lost_lock_aborts(ctx):
    _setup_source(ctx)
    now = datetime.now(timezone.utc).isoformat()
    cand = NoteCandidate(
        uid="cand_lost",
        source_uid="s1",
        sequence_index=0,
        chunk_uids=["c0"],
        label="Lost Lock",
        status="queued",
        model_version="v2",
        created_at=now,
    )
    ctx.db.insert_note_candidates([cand])
    ctx.db.claim_note_candidate("cand_lost", session_id="agent_a", ttl_seconds=300)

    note = Note(
        uid="n_lost",
        source_uid="s1",
        slug="note-lost",
        note_type="synthese",
        source_type="texte",
        title="Lost Lock Note",
        docstring="Docstring",
        body="Body text of adequate length for testing.",
        date_created="2026-08-15",
        date_modified="2026-08-15",
        tags=["tag-lost"],
    )

    # Attempting to convert with wrong session raises ExpiredLockError
    with pytest.raises(ExpiredLockError):
        ctx.db.create_note_from_candidate(note, "cand_lost", session_id="agent_wrong")

    # Verify Note was NOT created
    assert ctx.db.get_note("n_lost") is None
    # Candidate remains in_progress held by agent_a
    assert ctx.db.get_note_candidate("cand_lost").status == "in_progress"
