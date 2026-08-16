"""
Engine Benchmarks & R&D Visualizer — real embeddings.

Combines TextTiling signal inspection, 4-strategy segmentation comparison across
heterogeneous sources (book prose vs spoken discourse podcast), and retrieval / curate()
benchmark (Pure Cosine vs Hybrid RRF).

Corpora:
1. Marcus Aurelius Meditations (128p PDF — clean structured book prose)
2. YouTube Podcast transcript (URL: https://youtu.be/Pef22g53zsg — spoken discourse)

Usage:
    uv run python notebooks/demo_engine_benchmarks.py
"""
import math
import sys
import tempfile
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
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
from notebooks._lib.embedding_cache import get_or_embed, probe_provider, wrap_ctx_embed
from notebooks._lib.segmentation_strategies import (
    plot_metrics_comparison, plot_pca_topology, plot_size_distribution,
    plot_strategy_bands, print_metrics_table, run_benchmark,
)
from tools.media.fetch_subtitles import fetch_subtitles
from tools.text.chunk import chunk_text
from tools.text.segment import segment_chunks, _cosine_similarity
from tools.vault.claim_note_candidate import claim_note_candidate
from tools.vault.create_note_from_candidate import create_note_from_candidate
from tools.vault.query_vault import query_vault
from tools.vault.list_note_candidates import list_note_candidates
from tools.vault.update_note import update_note
from workflows.ingest import ingest

ASSETS_DIR = PROJECT_ROOT / "notebooks" / "assets"
PODCAST_URL = "https://youtu.be/Pef22g53zsg"


def compute_valley_depths(similarities: list[float]) -> list[float]:
    """Mirror tools.text.segment's Step 2-3: peak-relative valley depth per boundary."""
    depths = []
    for i in range(len(similarities)):
        max_left = max(similarities[: i + 1])
        max_right = max(similarities[i:])
        depths.append((max_left + max_right) / 2.0 - similarities[i])
    return depths


def compute_threshold(depths: list[float], k_sens: float) -> float:
    """Mirror tools.text.segment's Step 4: mean + k * stddev adaptive threshold."""
    mean_d = sum(depths) / len(depths)
    variance_d = sum((d - mean_d) ** 2 for d in depths) / len(depths)
    std_d = math.sqrt(variance_d)
    return mean_d + k_sens * std_d if std_d > 1e-6 else mean_d + 0.05


def plot_texttiling_signal(label: str, chunks, similarities, depths, threshold, candidates, out_path: Path):
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 9), dpi=140, sharex=True)

    x = np.arange(len(similarities))
    ax1.plot(x, similarities, color="#4c72b0", linewidth=1.6, marker="o", markersize=3)
    ax1.set_ylabel("Cosine Similarity", fontsize=10, fontweight="bold")
    ax1.set_title(f"{label} — TextTiling Consecutive Chunk Trajectory", fontsize=12, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.3)

    ax2.bar(x, depths, color="#c44e52", alpha=0.75, width=0.7)
    ax2.axhline(threshold, color="black", linestyle="--", linewidth=1.4, label=f"Adaptive Threshold (mean + k·std) = {threshold:.4f}")
    ax2.set_ylabel("Valley Depth Score", fontsize=10, fontweight="bold")
    ax2.legend(loc="upper right", fontsize=9)
    ax2.grid(True, linestyle="--", alpha=0.3)

    boundary_positions = [0]
    running = 0
    for cand in candidates:
        running += len(cand.chunk_uids)
        boundary_positions.append(running)
    cmap = plt.get_cmap("tab20")
    ax3.set_xlim(0, len(chunks))
    ax3.set_ylim(0, 1)
    ax3.set_yticks([])
    for i in range(len(boundary_positions) - 1):
        start, end = boundary_positions[i], boundary_positions[i + 1]
        ax3.axvspan(start, end, color=cmap(i % 20), alpha=0.65, ec="black", lw=0.8)
        ax3.text((start + end) / 2, 0.5, f"#{i + 1} ({end - start}c)", ha="center", va="center", fontsize=8, fontweight="bold")
    ax3.set_xlabel("Chunk Position Index", fontsize=10, fontweight="bold")
    ax3.set_ylabel("Segments", fontsize=10, fontweight="bold")

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f"    Saved signal plot: {out_path.name}")


def run_texttiling_inspection(ctx):
    print("\n" + "=" * 80)
    print("  SECTION 1: TEXTTILING INTERNAL SIGNAL INSPECTION (MARCUS AURELIUS)")
    print("=" * 80)
    pdf_file = PROJECT_ROOT / "notebooks" / "assets" / "Marcus-Aurelius-Meditations.pdf"
    reader = pypdf.PdfReader(str(pdf_file))
    pages_text = [page.extract_text() for page in reader.pages[:20]]
    text = "\n\n".join(filter(None, pages_text))

    chunks = chunk_text(text, ctx.settings.system)
    embeddings = get_or_embed([c.content for c in chunks], ctx)
    similarities = [_cosine_similarity(embeddings[i], embeddings[i + 1]) for i in range(len(embeddings) - 1)]
    depths = compute_valley_depths(similarities)
    threshold = compute_threshold(depths, ctx.settings.system.note_segmentation.sensitivity_k)

    candidates = segment_chunks(chunks, embeddings, ctx.settings)
    print(f"    Generated {len(candidates)} candidate segments across {len(chunks)} chunks.")
    plot_texttiling_signal(
        "Marcus Aurelius (First 20 Pages)", chunks, similarities, depths, threshold, candidates,
        ASSETS_DIR / "texttiling_signal_marcus.png"
    )


def run_heterogeneous_segmentation_benchmarks(ctx):
    print("\n" + "=" * 80)
    print("  SECTION 2: 4-STRATEGY BENCHMARK ON HETEROGENEOUS SOURCES")
    print("=" * 80)

    # Corpus A: Marcus Aurelius (128p PDF)
    pdf_file = PROJECT_ROOT / "notebooks" / "assets" / "Marcus-Aurelius-Meditations.pdf"
    reader = pypdf.PdfReader(str(pdf_file))
    book_text = "\n\n".join(filter(None, [page.extract_text() for page in reader.pages]))
    book_chunks = chunk_text(book_text, ctx.settings.system)
    book_embeddings = get_or_embed([c.content for c in book_chunks], ctx)

    print(f"\n  [Corpus A — Book Prose] {len(book_chunks)} chunks from 128 PDF pages.")
    results_book, _ = run_benchmark(book_chunks, book_embeddings, ctx.settings, baseline_k=ctx.settings.system.note_segmentation.sensitivity_k)
    print_metrics_table(results_book)
    plot_strategy_bands(book_chunks, results_book, "Marcus Aurelius Book Prose", ASSETS_DIR / "bench_4_strategies_book.png")
    plot_metrics_comparison(results_book, "Marcus Aurelius Book Prose", ASSETS_DIR / "bench_metrics_book.png")
    plot_size_distribution(results_book, "Marcus Aurelius Book Prose", ASSETS_DIR / "bench_size_dist_book.png")

    # Corpus B: Spoken Discourse Podcast (YouTube Pef22g53zsg)
    print(f"\n  [Corpus B — Spoken Discourse] Fetching transcript for {PODCAST_URL} ...")
    subs = fetch_subtitles(PODCAST_URL, ctx=ctx)
    print(f"    Fetched {len(subs.text.split())} words (source={subs.source}, lang={subs.language}).")
    podcast_chunks = chunk_text(subs.text, ctx.settings.system)
    podcast_embeddings = get_or_embed([c.content for c in podcast_chunks], ctx)

    print(f"  [Corpus B — Spoken Discourse] {len(podcast_chunks)} chunks.")
    results_podcast, _ = run_benchmark(podcast_chunks, podcast_embeddings, ctx.settings, baseline_k=ctx.settings.system.note_segmentation.sensitivity_k)
    print_metrics_table(results_podcast)
    plot_strategy_bands(podcast_chunks, results_podcast, "Spoken Discourse Podcast", ASSETS_DIR / "bench_4_strategies_podcast.png")
    plot_metrics_comparison(results_podcast, "Spoken Discourse Podcast", ASSETS_DIR / "bench_metrics_podcast.png")
    plot_size_distribution(results_podcast, "Spoken Discourse Podcast", ASSETS_DIR / "bench_size_dist_podcast.png")


def run_retrieval_benchmark(ctx):
    print("\n" + "=" * 80)
    print("  SECTION 3: RETRIEVAL & CURATE() BENCHMARK (HYBRID RRF VS PURE COSINE)")
    print("=" * 80)

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

        test_ctx = build_context(ctx.settings)
        test_ctx.db = VaultDB(vault_db)
        test_ctx.system_db_path = sys_db
        test_ctx.vault_path = vault_dir
        test_ctx.media_path = media_dir
        test_ctx.write_note = _write_note
        wrap_ctx_embed(test_ctx)

        pdf_file = PROJECT_ROOT / "notebooks" / "assets" / "Marcus-Aurelius-Meditations.pdf"
        reader = pypdf.PdfReader(str(pdf_file))
        text = "\n\n".join(filter(None, [page.extract_text() for page in reader.pages[:30]]))
        source = ingest("texte", text, test_ctx, title="Meditations of Marcus Aurelius")
        cands = list_note_candidates(test_ctx, source_uid=source.uid)

        for i, cand in enumerate(cands[:6]):
            claim_note_candidate(cand.uid, test_ctx, session_id="bench", is_human=True)
            first_chunk = next(c.content for c in test_ctx.db.get_chunks(cand.chunk_uids))
            content = NoteContentInput(
                title=cand.label[:80] or f"Passage {i + 1}",
                docstring=f"Stoic reflection excerpt #{i + 1}",
                body=first_chunk[:1000],
                tags=["stoicism", "marcus-aurelius"],
            )
            note_res = create_note_from_candidate(
                candidate_uid=cand.uid, content=content, ctx=test_ctx,
                session_id="bench", note_type="synthese", tags=["stoicism", "marcus-aurelius"],
            )
            if i % 2 == 0:
                update_note(note_res.note.uid, {"review_status": "reviewed"}, test_ctx)

        queries = ["duty and virtue", "meditation on death", "self-discipline and reason", "London Metal Exchange copper"]
        print(f"\n  Running {len(queries)} queries through query_vault()...")
        for q in queries:
            test_ctx.settings.system.query_vault.use_hybrid_retrieval = False
            r_cos = query_vault(q, test_ctx, limit=5)
            test_ctx.settings.system.query_vault.use_hybrid_retrieval = True
            r_hyb = query_vault(q, test_ctx, limit=5)
            print(f"    Query: \"{q}\"")
            print(f"      Cosine -> confidence={r_cos.confidence:.3f}, sources={len(r_cos.sources)}")
            print(f"      Hybrid -> confidence={r_hyb.confidence:.3f}, sources={len(r_hyb.sources)}")


def main():
    print("=" * 80)
    print("  EGOVAULT ENGINE BENCHMARKS & R&D VISUALIZER")
    print("=" * 80)

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    settings = load_settings()
    ctx = build_context(settings)
    probe_provider(ctx)

    run_texttiling_inspection(ctx)
    run_heterogeneous_segmentation_benchmarks(ctx)
    run_retrieval_benchmark(ctx)

    print("\n" + "=" * 80)
    print("  ALL BENCHMARKS COMPLETED SUCCESSFULLY.")
    print("=" * 80)


if __name__ == "__main__":
    main()
