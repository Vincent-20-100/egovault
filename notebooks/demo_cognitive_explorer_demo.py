"""
Interactive End-to-End Cognitive Explorer Demo — Product Showcase.

Demonstrates the complete human/agent cognitive workflow in EgoVault:
1. Ingestion: Load PDF source (128 pages of Marcus Aurelius) into hippocampal chunks
2. Segmentation: Automatic TextTiling into semantic note_candidates
3. Synthesis: Lock claim & atomic conversion into an Obsidian Markdown Note
4. Review Lifecycle: Human validation (unreviewed -> reviewed)
5. Prefrontal Working Memory: Curate retrieval with review-weighted confidence
6. Verbatim Proof Drill-Down: Instant chunk proof via get_chunks() with locators
7. Visual Explorer: High-signal plots for pipeline flow, confidence, and vector space

Usage:
    uv run python notebooks/demo_cognitive_explorer_demo.py
"""
import sys
import pypdf
import tempfile
import numpy as np
import matplotlib
matplotlib.use("Agg")
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

ASSETS_DIR = PROJECT_ROOT / "notebooks" / "assets"


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from all pages of the PDF."""
    reader = pypdf.PdfReader(str(pdf_path))
    pages_text = [page.extract_text() for page in reader.pages]
    return "\n\n".join(filter(None, pages_text))


def main():
    print("=" * 80)
    print("  EGOVAULT END-TO-END COGNITIVE EXPLORER DEMO (PRODUCT SHOWCASE)")
    print("=" * 80)

    pdf_file = PROJECT_ROOT / "notebooks" / "assets" / "Marcus-Aurelius-Meditations.pdf"
    if not pdf_file.exists():
        print(f"Error: PDF file not found at {pdf_file}")
        return

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

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
        wrap_ctx_embed(ctx)

        # Step 1: Ingest source from PDF
        print(f"\n[Step 1: Ingestion] Ingesting {pdf_file.name} (128 pages)...")
        full_pdf_text = extract_pdf_text(pdf_file)
        source = ingest("texte", full_pdf_text, ctx, title="Meditations of Marcus Aurelius")
        print(f"         Source UID : {source.uid}")
        print(f"         Status     : {source.status}")

        # Step 2: List note candidates
        print("\n[Step 2: Segmentation] Reading segmented note_candidates queue...")
        cands = list_note_candidates(ctx, source_uid=source.uid)
        total_chunks = sum(len(c.chunk_uids) for c in cands)
        print(f"         Chunks     : {total_chunks}")
        print(f"         Total candidates generated: {len(cands)}")
        for c in cands[:5]:
            clean_lbl = c.label[:55].encode("ascii", "ignore").decode("ascii")
            print(f"         - Candidate #{c.sequence_index + 1} (UID: {c.uid[:8]}...): \"{clean_lbl}...\" ({len(c.chunk_uids)} chunks)")

        # Step 3: Claim candidate lock
        cand_to_convert = cands[0]
        print(f"\n[Step 3: Synthesis Claim] Claiming lock on Candidate #{cand_to_convert.sequence_index + 1}...")
        claimed = claim_note_candidate(cand_to_convert.uid, ctx, session_id="human_explorer", is_human=True)
        print(f"         Status     : {claimed.status}")
        print(f"         Claimed by : {claimed.claimed_by}")

        # Step 4: Atomic Note conversion
        print("\n[Step 4: Obsidian Compilation] Atomically compiling candidate to Markdown Note...")
        first_chunk_text = next(c.content for c in ctx.db.get_chunks(cand_to_convert.chunk_uids))
        content = NoteContentInput(
            title="Book I: Debt of Gratitude and Mentors",
            docstring="Reflections of Marcus Aurelius on virtues inherited from his ancestors and Stoic teachers.",
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
        print("\n[Step 5: Review Validation] Flipping review_status: unreviewed -> reviewed...")
        update_note(note.uid, {"review_status": "reviewed"}, ctx)
        reviewed_note = ctx.db.get_note(note.uid)
        print(f"         Updated Review Status: {reviewed_note.review_status}")

        # Step 6: Curate prefrontal working memory
        print("\n[Step 6: Prefrontal Working Memory] Querying curate() for 'duty, virtue and death'...")
        curated = curate("duty virtue and death", ctx, limit=5)
        print(f"         Query      : \"{curated.query}\"")
        print(f"         Confidence : {curated.confidence:.3f}")
        print(f"         Sources    : {len(curated.sources)} retrieved")
        for s in curated.sources:
            clean_title = s.title[:45].encode("ascii", "ignore").decode("ascii")
            print(f"         - [{s.tier}] {clean_title}... (distance: {s.distance:.4f})")

        # Step 7: Verbatim proof drill-down
        print(f"\n[Step 7: Verbatim Proof Drill-Down] Proof drill-down via get_chunks()...")
        proof_chunks = get_chunks(cand_to_convert.chunk_uids[:3], ctx)
        for ch in proof_chunks:
            preview = ch.content.strip().replace("\n", " ")[:90].encode("ascii", "ignore").decode("ascii")
            print(f"         - Chunk pos={ch.position} (UID: {ch.uid[:8]}...): \"{preview}...\"")

        # Step 8: Visual Plots
        print("\n[Step 8: Visual Visualizations] Rendering Matplotlib Explorer Graphs...")

        # Plot 1: Pipeline Breakdown
        fig, ax = plt.subplots(figsize=(10, 4.5), dpi=140)
        stages = ["Raw PDF Pages", "SOTA Chunks", "Note Candidates", "Active Notes"]
        page_count = len(pypdf.PdfReader(str(pdf_file)).pages)
        counts = [page_count, total_chunks, len(cands), 1]
        colors = ["#4c72b0", "#55a868", "#c44e52", "#8172b8"]
        bars = ax.bar(stages, counts, color=colors, width=0.55)
        ax.set_title("EgoVault Cognitive Architecture Data Flow", fontsize=13, fontweight="bold", pad=12)
        ax.set_ylabel("Entity Count", fontsize=11)
        ax.grid(True, linestyle="--", alpha=0.3, axis="y")
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2.0, yval + 0.5, f"{int(yval)}", ha="center", va="bottom", fontsize=10, fontweight="bold")
        fig.tight_layout()
        fig.savefig(ASSETS_DIR / "explorer_pipeline_overview.png")
        plt.close(fig)

        # Plot 2: Embedding space PCA
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
                        edgecolors="black", linewidth=0.8, alpha=0.85,
                        marker="*" if tier == "query" else "o")
            ax3.annotate(proj_labels[i], (x, y), fontsize=8, xytext=(6, 4), textcoords="offset points")

        ax3.set_title("Embedding Space Topology: Query vs Retrieved Sources", fontsize=11, fontweight="bold", pad=12)
        ax3.grid(True, linestyle="--", alpha=0.3)
        fig3.tight_layout()
        fig3.savefig(ASSETS_DIR / "explorer_embedding_space_projection.png")
        plt.close(fig3)

        print("\n" + "=" * 80)
        print("  END-TO-END COGNITIVE EXPLORER DEMO COMPLETED SUCCESSFULLY.")
        print("=" * 80)


if __name__ == "__main__":
    main()
