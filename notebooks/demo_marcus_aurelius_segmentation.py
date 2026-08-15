"""
Marcus Aurelius Meditations — 4-Strategy Semantic Clustering Benchmark (real embeddings).

Parses all 128 pages (293 SOTA chunks) of 'notebooks/assets/Marcus-Aurelius-Meditations.pdf'
and compares 4 semantic clustering strategies side-by-side, using the real embedding
provider (Ollama nomic-embed-text, disk-cached — see notebooks/_lib/embedding_cache.py):

1. Baseline: Single-Pass TextTiling — the production engine function, unmodified.
2. Strategy 1: Two-Stage Hierarchical TextTiling (Fine Cut -> Centroid Cosine Merging)
3. Strategy 2: Contiguity-Constrained Agglomerative Clustering (Scikit-Learn AHC)
4. Strategy 3: Gaussian Kernel Smoothed TextTiling (Noise-filtered valley minima)

Scoring targets semantic coherence, not uniform size: a single powerful one-chunk
idea and a 50-chunk passage about one central idea are equally valid note candidates.
Cohesion/separation/contrast score boundary quality; size_min/size_max/size_std expose
which strategies structurally force uniform-ish segments instead of letting size
emerge from the content (see notebooks/_lib/segmentation_strategies.py).

Generates the 4-strategy band comparison, cohesion/separation/runtime metrics,
segment-size-distribution, and 2D/3D PCA topology figures in notebooks/assets/.

Usage:
    uv run python notebooks/demo_marcus_aurelius_segmentation.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import pypdf

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_settings
from infrastructure.context import build_context
from notebooks._lib.embedding_cache import get_or_embed, probe_provider
from notebooks._lib.segmentation_strategies import (
    plot_metrics_comparison, plot_pca_topology, plot_size_distribution,
    plot_strategy_bands, print_metrics_table, run_benchmark,
)
from tools.text.chunk import chunk_text


def extract_pdf_text(pdf_path: Path) -> str:
    reader = pypdf.PdfReader(str(pdf_path))
    pages_text = [page.extract_text() for page in reader.pages]
    return "\n\n".join(filter(None, pages_text))


def main():
    print("=" * 80)
    print("  MARCUS AURELIUS — 4-STRATEGY SEMANTIC CLUSTERING BENCHMARK (real embeddings)")
    print("=" * 80)

    pdf_file = PROJECT_ROOT / "notebooks" / "assets" / "Marcus-Aurelius-Meditations.pdf"
    full_text = extract_pdf_text(pdf_file)
    print(f"\n[1] Extracted {len(full_text.split())} words from 128 pages.")

    settings = load_settings()
    ctx = build_context(settings)
    probe_provider(ctx)

    chunks = chunk_text(full_text, settings.system)
    print(f"[2] SOTA Chunking (size={settings.system.chunking.size}, overlap={settings.system.chunking.overlap}): {len(chunks)} chunks.")

    print("[3] Embedding via real provider (disk-cached)...")
    embeddings = get_or_embed([c.content for c in chunks], ctx)

    print("[4] Running 4-strategy benchmark with quantitative scoring...")
    results, raw_cosines = run_benchmark(chunks, embeddings, settings, baseline_k=settings.system.note_segmentation.sensitivity_k)

    print("\n" + "=" * 80)
    print(f"  BENCHMARK RESULTS ({len(chunks)} chunks across 128 pages, real embeddings):")
    print("=" * 80)
    print_metrics_table(results)
    best_contrast = max(results, key=lambda k: results[k][1]["contrast"])
    widest_range = max(results, key=lambda k: results[k][1]["size_range"])
    narrowest_range = min(results, key=lambda k: results[k][1]["size_range"])
    print(f"\n  Highest boundary contrast: {best_contrast}")
    print(f"  Widest size range (most tolerant of small-idea/big-idea asymmetry): {widest_range}")
    print(f"  Narrowest size range (most likely imposing artificial uniformity): {narrowest_range}")
    print("=" * 80)

    assets_dir = PROJECT_ROOT / "notebooks" / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    title = "Marcus Aurelius (book prose)"

    print("\n[5] Rendering 4-strategy band comparison figure...")
    plot_strategy_bands(chunks, results, title, assets_dir / "clustering_4_strategies_benchmark.png")

    print("[6] Rendering cohesion/separation/runtime metrics figure...")
    plot_metrics_comparison(results, title, assets_dir / "clustering_metrics_comparison.png")

    print("[7] Rendering segment-size-distribution figure (uniformity bias check)...")
    plot_size_distribution(results, title, assets_dir / "clustering_size_distribution.png")

    two_stage_cands = results["Two-Stage Hierarchical Merging"][0]
    print("[8] Rendering 2D vector topology PCA plot...")
    plot_pca_topology(chunks, embeddings, two_stage_cands, 2, title, assets_dir / "clustering_2d_pca_topology.png")

    print("[9] Rendering 3D vector topology PCA plot...")
    plot_pca_topology(chunks, embeddings, two_stage_cands, 3, title, assets_dir / "clustering_3d_pca_topology.png")

    print("\n" + "=" * 80)
    print("  DONE — 4-strategy benchmark with real embeddings and quantitative scoring.")
    print("=" * 80)


if __name__ == "__main__":
    main()
