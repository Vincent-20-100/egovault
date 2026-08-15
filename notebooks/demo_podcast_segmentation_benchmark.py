"""
Spoken Discourse Stress Test — 4-Strategy Semantic Clustering Benchmark (real embeddings).

Runs the same 4-strategy benchmark as demo_marcus_aurelius_segmentation.py, but on a
real YouTube video transcript instead of book prose — spoken discourse has filler,
repetition, and topic drift without paragraph structure, which is a materially
different challenge for segmentation than clean written text.

Source video: https://www.youtube.com/watch?v=5JDrK7sP3gA (single video, not the
full playlist — kept small on purpose to bound ingest + embedding time).

Usage:
    uv run python notebooks/demo_podcast_segmentation_benchmark.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_settings
from infrastructure.context import build_context
from notebooks._lib.embedding_cache import get_or_embed, probe_provider
from notebooks._lib.segmentation_strategies import (
    plot_metrics_comparison, plot_size_distribution,
    plot_strategy_bands, print_metrics_table, run_benchmark,
)
from tools.media.fetch_subtitles import fetch_subtitles
from tools.text.chunk import chunk_text

VIDEO_URL = "https://www.youtube.com/watch?v=5JDrK7sP3gA"


def main():
    print("=" * 80)
    print("  SPOKEN DISCOURSE STRESS TEST — 4-STRATEGY SEGMENTATION BENCHMARK (real embeddings)")
    print("=" * 80)

    settings = load_settings()
    ctx = build_context(settings)
    probe_provider(ctx)

    print(f"\n[1] Fetching subtitles for {VIDEO_URL} ...")
    subs = fetch_subtitles(VIDEO_URL, ctx=ctx)
    print(f"    {len(subs.text.split())} words, language={subs.language}, source={subs.source}")

    chunks = chunk_text(subs.text, settings.system)
    print(f"[2] SOTA Chunking (size={settings.system.chunking.size}, overlap={settings.system.chunking.overlap}): {len(chunks)} chunks.")

    if len(chunks) < 6:
        print(f"\n    WARNING: only {len(chunks)} chunks — this transcript is too short for a "
              "meaningful 4-strategy comparison. Results below are illustrative only.")

    print("[3] Embedding via real provider (disk-cached)...")
    embeddings = get_or_embed([c.content for c in chunks], ctx)

    print("[4] Running 4-strategy benchmark with quantitative scoring...")
    results, raw_cosines = run_benchmark(chunks, embeddings, settings, baseline_k=settings.system.note_segmentation.sensitivity_k)

    print("\n" + "=" * 80)
    print(f"  BENCHMARK RESULTS ({len(chunks)} chunks, spoken discourse, real embeddings):")
    print("=" * 80)
    print_metrics_table(results)
    print("=" * 80)

    assets_dir = PROJECT_ROOT / "notebooks" / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    title = "Spoken Discourse (podcast transcript)"

    print("\n[5] Rendering 4-strategy band comparison figure...")
    plot_strategy_bands(chunks, results, title, assets_dir / "podcast_4_strategies_benchmark.png")

    print("[6] Rendering cohesion/separation/runtime metrics figure...")
    plot_metrics_comparison(results, title, assets_dir / "podcast_metrics_comparison.png")

    print("[7] Rendering segment-size-distribution figure (uniformity bias check)...")
    plot_size_distribution(results, title, assets_dir / "podcast_size_distribution.png")

    print("\n" + "=" * 80)
    print("  DONE — spoken discourse benchmark complete.")
    print("=" * 80)
    print("\n  Compare against demo_marcus_aurelius_segmentation.py's book-prose results:")
    print("  book prose has clean paragraph boundaries the cosine signal can lock onto;")
    print("  spoken discourse's boundaries are noisier — check whether contrast scores")
    print("  drop and whether strategies that looked good on the book still hold up here.")


if __name__ == "__main__":
    main()
