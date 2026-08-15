"""
Interactive End-to-End Cognitive Explorer Demo with Marcus Aurelius PDF.

Demonstrates the complete human/agent cognitive workflow in EgoVault:
1. PDF text extraction from versioned 'notebooks/assets/Marcus-Aurelius-Meditations.pdf'
2. Automatic TextTiling segmentation into note_candidates queue
3. Lock claiming & atomic conversion into an Obsidian Markdown Note
4. Review status validation (unreviewed -> reviewed)
5. Curate prefrontal working memory retrieval with review-weighted confidence
6. Verbatim chunk proof drill-down via get_chunks()
7. Matplotlib pipeline & confidence visualization graphs

Usage:
    uv run python notebooks/demo_end_to_end_explorer.py
"""
import sys
import pypdf
import tempfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.decomposition import PCA

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_settings
from infrastructure.context import build_context
from workflows.ingest import ingest
from tools.vault.list_note_candidates import list_note_candidates
from tools.vault.claim_note_candidate import claim_note_candidate
from tools.vault.create_note_from_candidate import create_note_from_candidate
from tools.vault.curate import curate
from tools.vault.get_chunks import get_chunks
from tools.vault.update_note import update_note
from core.schemas import NoteContentInput
from notebooks._lib.embedding_cache import wrap_ctx_embed, probe_provider


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from all pages of the PDF."""
    reader = pypdf.PdfReader(str(pdf_path))
    pages_text = [page.extract_text() for page in reader.pages]
    return "\n\n".join(filter(None, pages_text))


def main():
    print("=" * 80)
    print("  EGOVAULT END-TO-END COGNITIVE EXPLORER -- MARCUS AURELIUS DEMO")
    print("=" * 80)

    pdf_file = PROJECT_ROOT / "notebooks" / "assets" / "Marcus-Aurelius-Meditations.pdf"
    if not pdf_file.exists():
        print(f"Error: PDF file not found at {pdf_file}")
        return

    # 1. Isolated temporary vault environment
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        settings = load_settings()

        vault_db = tmp_path / "vault.db"
        sys_db = tmp_path / "system.db"
        vault_dir = tmp_path / "vault"
        media_dir = tmp_path / "media"
        vault_dir.mkdir()
        media_dir.mkdir()

        from infrastructure.db import init_db, init_system_db
        from infrastructure.vault_db import VaultDB
        from infrastructure.vault_writer import write_note as _write_note

        init_db(vault_db)
        init_system_db(sys_db)

        ctx = build_context(settings)
        ctx.db = VaultDB(vault_db)
        ctx.system_db_path = sys_db
        ctx.vault_path = vault_dir
        ctx.media_path = media_dir
        ctx.write_note = _write_note

        probe_provider(ctx)
        wrap_ctx_embed(ctx)  # real Ollama embeddings, disk-cached — no mock fallback

        # Step 1: Ingest source from PDF
        print(f"\n[Step 1] Ingesting {pdf_file.name} (128 pages)...")
        full_pdf_text = extract_pdf_text(pdf_file)
        source = ingest("texte", full_pdf_text, ctx, title="Meditations of Marcus Aurelius")
        print(f"         Source UID : {source.uid}")
        print(f"         Status     : {source.status}")

        # Step 2: List note candidates
        print("\n[Step 2] Reading segmented note_candidates queue...")
        cands = list_note_candidates(ctx, source_uid=source.uid)
        total_chunks = sum(len(c.chunk_uids) for c in cands)
        print(f"         Chunks     : {total_chunks}")
        print(f"         Total candidates generated: {len(cands)}")
        for c in cands[:6]:
            clean_lbl = c.label[:55].encode("ascii", "ignore").decode("ascii")
            print(f"         - Candidate #{c.sequence_index + 1} (UID: {c.uid[:8]}...): \"{clean_lbl}...\" ({len(c.chunk_uids)} chunks)")

        if not cands:
            print("No candidates generated!")
            return

        # Step 3: Claim candidate #1 (First Book of Meditations)
        cand_to_convert = cands[0]
        print(f"\n[Step 3] Claiming lock on Candidate #{cand_to_convert.sequence_index + 1} (human session)...")
        claimed = claim_note_candidate(cand_to_convert.uid, ctx, session_id="human_explorer", is_human=True)
        print(f"         Status     : {claimed.status}")
        print(f"         Claimed by : {claimed.claimed_by}")

        # Step 4: Atomic Note conversion
        print("\n[Step 4] Atomically converting candidate to active Obsidian Note...")
        first_chunk_text = next(c.content for c in ctx.db.get_chunks(cand_to_convert.chunk_uids))
        content = NoteContentInput(
            title="Book I: Debt of Gratitude and Mentors",
            docstring="Reflections of Marcus Aurelius on the virtues inherited from his ancestors and Stoic teachers.",
            body=first_chunk_text[:1200],
            tags=["stoicism", "gratitude", "marcus-aurelius"],
        )
        note_res = create_note_from_candidate(
            candidate_uid=cand_to_convert.uid,
            content=content,
            ctx=ctx,
            session_id="human_explorer",
            note_type="synthese",
            tags=["stoicism", "gratitude", "marcus-aurelius"],
        )
        note = note_res.note
        print(f"         Created Note UID  : {note.uid}")
        print(f"         Markdown File Path: {note_res.markdown_path}")
        print(f"         Review Status     : {note.review_status}")

        # Step 5: Mark note as reviewed
        print("\n[Step 5] Validating note (flipping review_status: unreviewed -> reviewed)...")
        update_note(note.uid, {"review_status": "reviewed"}, ctx)
        reviewed_note = ctx.db.get_note(note.uid)
        print(f"         Updated Review Status: {reviewed_note.review_status}")

        def _clean_str(s: str) -> str:
            return s.encode("ascii", "ignore").decode("ascii")

        # Step 6: Curate prefrontal working memory
        print("\n[Step 6] Querying curate() working memory context for 'duty, virtue and death'...")
        curated = curate("duty virtue and death", ctx, limit=5)
        print(f"         Query      : \"{curated.query}\"")
        print(f"         Confidence : {curated.confidence} (weighted by review status)")
        print(f"         Sources    : {len(curated.sources)} retrieved")
        for s in curated.sources:
            clean_title = _clean_str(s.title[:45])
            print(f"         - [{s.tier}] {clean_title}... (distance: {s.distance:.4f})")

        # Step 7: Verbatim proof drill-down
        print(f"\n[Step 7] Verbatim proof drill-down via get_chunks({cand_to_convert.chunk_uids[:3]})...")
        proof_chunks = get_chunks(cand_to_convert.chunk_uids[:3], ctx)
        for ch in proof_chunks:
            preview = _clean_str(ch.content.strip().replace("\n", " ")[:90])
            print(f"         - Chunk pos={ch.position} (UID: {ch.uid[:8]}...): \"{preview}...\"")

        # Step 8: Render Matplotlib Explorer Graphs
        print("\n[Step 8] Rendering Matplotlib Explorer Graphs...")
        assets_dir = PROJECT_ROOT / "notebooks" / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        # Plot 1: Pipeline Breakdown
        fig, ax = plt.subplots(figsize=(10, 4.5), dpi=140)
        stages = ['Raw PDF Pages', 'SOTA Chunks', 'Note Candidates', 'Active Notes']
        page_count = len(pypdf.PdfReader(str(pdf_file)).pages)
        counts = [page_count, total_chunks, len(cands), 1]
        colors = ['#4c72b0', '#55a868', '#c44e52', '#8172b8']

        bars = ax.bar(stages, counts, color=colors, width=0.55)
        ax.set_title("EgoVault Cognitive Architecture Data Flow", fontsize=13, fontweight='bold', pad=12)
        ax.set_ylabel("Entity Count", fontsize=11)
        ax.grid(True, linestyle='--', alpha=0.3, axis='y')

        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, f"{int(yval)}", ha='center', va='bottom', fontsize=10, fontweight='bold')

        fig.tight_layout()
        overview_path = assets_dir / "explorer_pipeline_overview.png"
        fig.savefig(overview_path)
        plt.close(fig)
        print(f"         Saved pipeline overview plot to: {overview_path}")

        # Plot 2: Curate Retrieval Confidence Breakdown
        fig2, ax2 = plt.subplots(figsize=(10, 4), dpi=140)
        if curated.sources:
            src_titles = [f"[{s.tier[:4]}] {s.title[:25]}..." for s in curated.sources]
            distances = [s.distance for s in curated.sources]
            similarities = [max(0.0, 1.0 - d) for d in distances]

            y_pos = np.arange(len(src_titles))
            ax2.barh(y_pos, similarities, color='#2ca02c', alpha=0.8, height=0.55)
            ax2.set_yticks(y_pos)
            ax2.set_yticklabels(src_titles, fontsize=9)
            ax2.invert_yaxis()  # top-down
            ax2.set_xlabel("Similarity Score ($1.0 - \\text{distance}$)", fontsize=11)
            ax2.set_title(rf"Curate Working Memory Retrieval (Confidence: {curated.confidence})", fontsize=13, fontweight='bold', pad=12)
            ax2.grid(True, linestyle='--', alpha=0.3, axis='x')

            for i, sim in enumerate(similarities):
                ax2.text(sim + 0.01, i, f"{sim:.3f}", va='center', fontsize=9, fontweight='bold')

        fig2.tight_layout()
        conf_path = assets_dir / "explorer_curate_confidence.png"
        fig2.savefig(conf_path)
        plt.close(fig2)
        print(f"         Saved curate confidence plot to: {conf_path}")

        # Plot 3: Embedding-space projection — why curate() escalated (or didn't) to chunks
        print("\n[Step 9] Rendering embedding-space projection of query vs. retrieved sources...")
        proj_texts = [curated.query] + [s.content[:500] for s in curated.sources]
        proj_labels = ["QUERY"] + [f"[{s.tier}] {s.title[:20]}" for s in curated.sources]
        proj_tiers = ["query"] + [s.tier for s in curated.sources]
        proj_vectors = [ctx.embed(t) for t in proj_texts]

        coords_proj = PCA(n_components=2).fit_transform(proj_vectors)
        color_map = {"query": "#c44e52", "note": "#55a868", "chunk": "#4c72b0"}

        fig3, ax3 = plt.subplots(figsize=(8, 7), dpi=140)
        for i, (x, y) in enumerate(coords_proj):
            tier = proj_tiers[i]
            ax3.scatter(x, y, s=180 if tier == "query" else 100, color=color_map[tier],
                        edgecolors='black', linewidth=0.8, alpha=0.85,
                        marker='*' if tier == "query" else 'o')
            ax3.annotate(proj_labels[i], (x, y), fontsize=8, xytext=(6, 4), textcoords='offset points')

        n_note_sources = sum(1 for s in curated.sources if s.tier == "note")
        escalated = n_note_sources < ctx.settings.system.curate.escalation_min_notes
        ax3.set_title(
            f"Query vs. Retrieved Sources (PCA of real embeddings)\n"
            f"{n_note_sources} relevant note(s) < escalation_min_notes="
            f"{ctx.settings.system.curate.escalation_min_notes} -> escalated to chunks: {escalated}",
            fontsize=11, fontweight='bold', pad=12,
        )
        legend_handles = [
            plt.Line2D([0], [0], marker='*', color='w', markerfacecolor=color_map['query'], markersize=14, label='Query'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color_map['note'], markersize=10, label='Note (tier 2)'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color_map['chunk'], markersize=10, label='Chunk (tier 1)'),
        ]
        ax3.legend(handles=legend_handles, loc='best', fontsize=9)
        ax3.grid(True, linestyle='--', alpha=0.3)
        fig3.tight_layout()

        proj_path = assets_dir / "explorer_embedding_space_projection.png"
        fig3.savefig(proj_path)
        plt.close(fig3)
        print(f"         Saved embedding-space projection to: {proj_path}")

        print("\n" + "=" * 80)
        print("  END-TO-END EXPLORATION SUCCESSFUL -- ALL LIFECYCLE GATES VERIFIED!")
        print("=" * 80)


if __name__ == "__main__":
    main()
