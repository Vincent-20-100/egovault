"""
Retrieval / curate() Strategy Benchmark — real embeddings, real vault.

Ingests a real slice of the Marcus Aurelius corpus into an isolated tmp vault,
converts several note candidates into notes (a deliberate mix of `reviewed` and
`unreviewed`, so confidence weighting is visible), then benchmarks
tools.vault.curate.curate() itself against a fixed Stoic-themed query set:

1. Pure cosine retrieval vs. hybrid RRF (cosine + BM25/FTS5) —
   `curate.use_hybrid_retrieval` on/off.
2. Escalation behavior — tier composition (notes-only vs. notes+chunks) per query,
   driven by `curate.escalation_min_notes` / `escalation_max_distance`.
3. Confidence weighting — reviewed vs. unreviewed note contribution to the
   final weighted confidence score.
4. RRF fusion mechanics for one query — cosine rank vs. BM25 rank vs. fused rank,
   using the real `infrastructure.db._rrf_fuse` / `_bm25_topk_uids`.

Requires a running Ollama server with `nomic-embed-text` pulled. No mock
fallback — this notebook exists specifically to show what curate() really does.

Usage:
    uv run python notebooks/demo_retrieval_curate_benchmark.py
"""
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pypdf

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_settings
from core.schemas import NoteContentInput
from infrastructure import db as vault_db_module
from infrastructure.context import build_context
from infrastructure.db import init_db, init_system_db
from infrastructure.vault_db import VaultDB
from infrastructure.vault_writer import write_note as _write_note
from notebooks._lib.embedding_cache import probe_provider, wrap_ctx_embed
from tools.vault.claim_note_candidate import claim_note_candidate
from tools.vault.create_note_from_candidate import create_note_from_candidate
from tools.vault.curate import curate
from tools.vault.list_note_candidates import list_note_candidates
from tools.vault.update_note import update_note
from workflows.ingest import ingest

ASSETS_DIR = PROJECT_ROOT / "notebooks" / "assets"

QUERY_SET = [
    "duty and virtue",
    "meditation on death",
    "self-discipline and reason",
    "the price of copper on the London Metal Exchange",  # deliberately out-of-corpus
]


def setup_vault(ctx):
    """Ingest a real corpus slice and convert several candidates to notes,
    alternating reviewed/unreviewed so confidence weighting is visible."""
    pdf_file = PROJECT_ROOT / "notebooks" / "assets" / "Marcus-Aurelius-Meditations.pdf"
    reader = pypdf.PdfReader(str(pdf_file))
    pages_text = [page.extract_text() for page in reader.pages[:30]]
    text = "\n\n".join(filter(None, pages_text))

    source = ingest("texte", text, ctx, title="Meditations of Marcus Aurelius")
    cands = list_note_candidates(ctx, source_uid=source.uid)
    total_chunks = sum(len(c.chunk_uids) for c in cands)
    print(f"    Ingested {total_chunks} chunks, {len(cands)} note candidates.")

    notes = []
    n_reviewed = 0
    for i, cand in enumerate(cands[:6]):
        claim_note_candidate(cand.uid, ctx, session_id="bench", is_human=True)
        first_chunk = next(c.content for c in ctx.db.get_chunks(cand.chunk_uids))
        content = NoteContentInput(
            title=cand.label[:80] or f"Passage {i + 1}",
            docstring=f"Stoic reflection excerpt #{i + 1} from Marcus Aurelius' Meditations.",
            body=first_chunk[:1000],
            tags=["stoicism", "marcus-aurelius"],
        )
        note_res = create_note_from_candidate(
            candidate_uid=cand.uid, content=content, ctx=ctx,
            session_id="bench", note_type="synthese", tags=["stoicism", "marcus-aurelius"],
        )
        # Alternate review status: even indices reviewed, odd left as AI drafts.
        if i % 2 == 0:
            update_note(note_res.note.uid, {"review_status": "reviewed"}, ctx)
            n_reviewed += 1
        notes.append(note_res.note)

    print(f"    Created {len(notes)} notes ({n_reviewed} reviewed, {len(notes) - n_reviewed} unreviewed).")
    return source, notes


def run_query_both_modes(query: str, ctx):
    ctx.settings.system.curate.use_hybrid_retrieval = False
    cosine_result = curate(query, ctx, limit=5)
    ctx.settings.system.curate.use_hybrid_retrieval = True
    hybrid_result = curate(query, ctx, limit=5)
    ctx.settings.system.curate.use_hybrid_retrieval = False
    return cosine_result, hybrid_result


def plot_mode_comparison(query_results: dict, out_path: Path):
    """Confidence + tier composition, pure cosine vs hybrid RRF, per query."""
    queries = list(query_results.keys())
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=140)

    x = np.arange(len(queries))
    width = 0.35
    cosine_conf = [query_results[q][0].confidence or 0.0 for q in queries]
    hybrid_conf = [query_results[q][1].confidence or 0.0 for q in queries]
    ax1.bar(x - width / 2, cosine_conf, width, label="Pure cosine", color="#4c72b0")
    ax1.bar(x + width / 2, hybrid_conf, width, label="Hybrid RRF", color="#c44e52")
    ax1.set_xticks(x)
    ax1.set_xticklabels([q[:22] for q in queries], rotation=20, ha="right", fontsize=8)
    ax1.set_ylabel("curate() confidence score")
    ax1.set_title("Confidence: Pure Cosine vs. Hybrid RRF", fontsize=12, fontweight="bold")
    ax1.legend(fontsize=8)
    ax1.grid(True, linestyle="--", alpha=0.3, axis="y")

    for mode_idx, (label, color_note, color_chunk) in enumerate([
        ("cosine", "#55a868", "#8172b8"), ("hybrid", "#2ca02c", "#c44e52"),
    ]):
        n_notes = [sum(1 for s in query_results[q][mode_idx].sources if s.tier == "note") for q in queries]
        n_chunks = [sum(1 for s in query_results[q][mode_idx].sources if s.tier == "chunk") for q in queries]
        offset = (mode_idx - 0.5) * width
        ax2.bar(x + offset, n_notes, width, color=color_note, label=f"{label}: notes" if mode_idx == 0 else f"{label}: notes")
        ax2.bar(x + offset, n_chunks, width, bottom=n_notes, color=color_chunk, label=f"{label}: chunks" if mode_idx == 0 else f"{label}: chunks")

    ax2.set_xticks(x)
    ax2.set_xticklabels([q[:22] for q in queries], rotation=20, ha="right", fontsize=8)
    ax2.set_ylabel("Sources returned")
    ax2.set_title("Tier Composition — Escalation to Chunks", fontsize=12, fontweight="bold")
    ax2.legend(fontsize=7, ncol=2)
    ax2.grid(True, linestyle="--", alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_confidence_weighting(query: str, result, ctx, out_path: Path):
    """Break down the weighted-confidence formula for one query's sources."""
    conf_cfg = ctx.settings.system.curate.confidence
    labels, weights, sims = [], [], []
    for s in result.sources:
        sim = max(0.0, 1.0 - s.distance)
        if s.tier == "note":
            note = ctx.db.get_note(s.uid)
            w = conf_cfg.reviewed_note_weight if note.review_status == "reviewed" else conf_cfg.unreviewed_note_weight
            tag = "reviewed" if note.review_status == "reviewed" else "unreviewed"
        else:
            w = 0.5
            tag = "chunk"
        labels.append(f"[{s.tier[:4]}:{tag}] {s.title[:20]}")
        weights.append(w)
        sims.append(sim)

    contributions = [w * s for w, s in zip(weights, sims)]
    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    y = np.arange(len(labels))
    ax.barh(y, contributions, color="#4c72b0", alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("weight x similarity (contribution to confidence numerator)")
    ax.set_title(f"Confidence weighting breakdown — query: \"{query}\" (final confidence: {result.confidence})", fontsize=11, fontweight="bold")
    for i, (w, s) in enumerate(zip(weights, sims)):
        ax.text(contributions[i] + 0.005, i, f"w={w:.2f} x sim={s:.3f}", va="center", fontsize=7)
    ax.grid(True, linestyle="--", alpha=0.3, axis="x")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_rrf_fusion(query: str, ctx, out_path: Path):
    """Show the raw mechanics: cosine rank vs BM25 rank vs RRF-fused rank for one query."""
    query_embedding = ctx.embed(query)
    cosine_results = ctx.db.search_notes(query_embedding, None, 10)
    cosine_uids = [r.note_uid for r in cosine_results]
    conn = vault_db_module.get_vault_connection(ctx.db._db_path)
    bm25_uids = vault_db_module._bm25_topk_uids(conn, "notes_fts", query, 10)
    conn.close()
    fused_uids = vault_db_module._rrf_fuse(cosine_uids, bm25_uids, k=ctx.settings.system.curate.confidence.rrf_k, limit=10)

    all_uids = list(dict.fromkeys(fused_uids + cosine_uids + bm25_uids))
    titles = {r.note_uid: r.title[:30] for r in cosine_results}

    rows = []
    for uid in all_uids:
        c_rank = cosine_uids.index(uid) + 1 if uid in cosine_uids else None
        b_rank = bm25_uids.index(uid) + 1 if uid in bm25_uids else None
        f_rank = fused_uids.index(uid) + 1 if uid in fused_uids else None
        rows.append((titles.get(uid, uid[:8]), c_rank, b_rank, f_rank))
    rows.sort(key=lambda r: (r[3] is None, r[3]))

    fig, ax = plt.subplots(figsize=(9, max(2.5, 0.4 * len(rows))), dpi=140)
    ax.axis("off")
    table_data = [["Note", "Cosine rank", "BM25 rank", "RRF fused rank"]] + [
        [r[0], str(r[1]) if r[1] else "-", str(r[2]) if r[2] else "-", str(r[3]) if r[3] else "-"]
        for r in rows
    ]
    table = ax.table(cellText=table_data, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.6)
    ax.set_title(f"RRF Fusion Mechanics — query: \"{query}\"", fontsize=12, fontweight="bold", pad=20)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def main():
    print("=" * 80)
    print("  EGOVAULT RETRIEVAL / CURATE() STRATEGY BENCHMARK (real embeddings, real vault)")
    print("=" * 80)

    settings = load_settings()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        vault_db = tmp_path / "vault.db"
        sys_db = tmp_path / "system.db"
        vault_dir = tmp_path / "vault"
        media_dir = tmp_path / "media"
        vault_dir.mkdir()
        media_dir.mkdir()

        init_db(vault_db)
        init_system_db(sys_db)

        ctx = build_context(settings)
        ctx.db = VaultDB(vault_db)
        ctx.system_db_path = sys_db
        ctx.vault_path = vault_dir
        ctx.media_path = media_dir
        ctx.write_note = _write_note

        probe_provider(ctx)
        wrap_ctx_embed(ctx)

        print("\n[1] Setting up vault (ingest + note conversion, mixed review status)...")
        source, notes = setup_vault(ctx)

        print("\n[2] Running fixed query set through curate() in both retrieval modes...")
        query_results = {}
        for q in QUERY_SET:
            print(f"    - \"{q}\"")
            query_results[q] = run_query_both_modes(q, ctx)

        ASSETS_DIR.mkdir(parents=True, exist_ok=True)

        print("\n[3] Rendering mode comparison (confidence + tier composition)...")
        plot_mode_comparison(query_results, ASSETS_DIR / "curate_mode_comparison.png")

        rich_query = QUERY_SET[0]
        print(f"\n[4] Rendering confidence weighting breakdown for \"{rich_query}\"...")
        plot_confidence_weighting(rich_query, query_results[rich_query][0], ctx, ASSETS_DIR / "curate_confidence_weighting.png")

        print(f"\n[5] Rendering RRF fusion mechanics for \"{rich_query}\"...")
        plot_rrf_fusion(rich_query, ctx, ASSETS_DIR / "curate_rrf_fusion.png")

        print("\n" + "=" * 80)
        print("  BENCHMARK SUMMARY:")
        print("=" * 80)
        for q, (cosine_r, hybrid_r) in query_results.items():
            print(f"  \"{q}\"")
            print(f"      cosine  -> confidence={cosine_r.confidence}, sources={len(cosine_r.sources)} "
                  f"(notes={sum(1 for s in cosine_r.sources if s.tier=='note')}, chunks={sum(1 for s in cosine_r.sources if s.tier=='chunk')})")
            print(f"      hybrid  -> confidence={hybrid_r.confidence}, sources={len(hybrid_r.sources)} "
                  f"(notes={sum(1 for s in hybrid_r.sources if s.tier=='note')}, chunks={sum(1 for s in hybrid_r.sources if s.tier=='chunk')})")
        print("=" * 80)
        print("\n  DONE.")


if __name__ == "__main__":
    main()
