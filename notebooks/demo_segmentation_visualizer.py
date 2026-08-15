"""
Topic Segmentation Visualizer (TextTiling) — real embeddings.

Runs EgoVault's actual segmentation engine (tools.text.segment.segment_chunks)
on two corpora: a synthetic 3-topic sample (clean boundary case) and a slice
of the real Marcus Aurelius corpus (hard, noisy case). Visualizes the hidden
internal signal — consecutive cosine similarity, valley depth score, and the
adaptive statistical threshold — that drives every boundary decision.

Requires a running Ollama server with `nomic-embed-text` pulled
(`infrastructure/embedding_provider.py`). No mock fallback: if the provider
is unreachable this fails loud with a setup hint.

Usage:
    uv run python notebooks/demo_segmentation_visualizer.py
"""
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pypdf

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_settings
from infrastructure.context import build_context
from tools.text.chunk import chunk_text
from tools.text.segment import segment_chunks, _cosine_similarity
from notebooks._lib.embedding_cache import get_or_embed, probe_provider

ASSETS_DIR = PROJECT_ROOT / "notebooks" / "assets"

SAMPLE_TEXT = """
# Section 1: Quantum Computing Fundamentals

Quantum computing harnesses the phenomena of quantum mechanics to solve problems too complex for classical computers. Superposition allows qubits to exist in states corresponding to 0, 1, or any linear combination of both. Entanglement creates strong correlations between qubits regardless of distance. Quantum gates manipulate these qubits to perform calculations through quantum interference, constructive interference amplifying correct paths and destructive interference canceling wrong paths. Shore's algorithm demonstrates exponential speedup for integer factorization, threatening RSA encryption. Grover's algorithm provides quadratic speedup for unstructured database search. Physical implementations include superconducting circuits, trapped ions, and neutral atoms.

# Section 2: Cognitive Neuroscience and Memory Consolidation

Human memory consolidation is the process by which temporary, labile memories are transformed into stable, long-term representations. The hippocampus acts as a fast-learning episodic buffer, rapidly encoding daily experiences into raw verbatim chunks. During slow-wave sleep, sharp-wave ripples replay these episodic traces to the neocortex. Over time, the neocortex extracts invariant conceptual structures, stripping away peripheral noise. This process, known as systems consolidation, transforms raw episodic events into structured semantic knowledge networks. Spreading activation through prefrontal working memory allows rapid retrieval of conceptual nuclei with 4 to 7 active working memory slots.

# Section 3: Game Theory and Strategic Equilibrium

Game theory studies strategic interactions between rational decision-makers. A Nash equilibrium occurs when no player has an incentive to deviate unilaterally from their chosen strategy given the strategies of all other players. In the Prisoner's Dilemma, mutual defection represents the unique Nash equilibrium despite mutual cooperation yielding higher collective payoffs. Evolutionary game theory applies these principles to biological populations, replacing rational choice with natural selection and strategy survival. Evolutionary Stable Strategies (ESS) describe behaviors that cannot be invaded by mutant strategies. Repeated games introduce the shadow of the future, allowing cooperation to emerge through strategies such as Tit-for-Tat.
"""


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


def plot_segmentation_signal(label: str, chunks, similarities, depths, threshold, candidates, out_path: Path):
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 9), dpi=140, sharex=True)

    x = np.arange(len(similarities))
    ax1.plot(x, similarities, color="#4c72b0", linewidth=1.6, marker="o", markersize=3)
    ax1.set_ylabel("Cosine similarity")
    ax1.set_title(f"{label} — Consecutive Chunk Similarity (real embeddings)", fontsize=12, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.3)

    ax2.bar(x, depths, color="#c44e52", alpha=0.75, width=0.7)
    ax2.axhline(threshold, color="black", linestyle="--", linewidth=1.4, label=f"adaptive threshold (mean + k·std) = {threshold:.4f}")
    ax2.set_ylabel("Valley depth score")
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
    ax3.set_xlabel("Chunk position")
    ax3.set_ylabel("Segments")

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f"    Saved: {out_path}")


def run_corpus(label: str, text: str, ctx, out_name: str, chunking_override: tuple[int, int] | None = None):
    print(f"\n{'=' * 80}\n  {label}\n{'=' * 80}")

    original_chunking = (ctx.settings.system.chunking.size, ctx.settings.system.chunking.overlap)
    if chunking_override:
        # Demo-only override: the production chunk size (300 words) collapses this
        # short sample into 1-2 chunks per section, hiding the boundary signal.
        ctx.settings.system.chunking.size, ctx.settings.system.chunking.overlap = chunking_override

    print("[1] Chunking...")
    chunks = chunk_text(text, ctx.settings.system)
    print(f"    {len(chunks)} chunks (size={ctx.settings.system.chunking.size}, overlap={ctx.settings.system.chunking.overlap})")

    print("[2] Embedding (real provider, disk-cached)...")
    embeddings = get_or_embed([c.content for c in chunks], ctx)

    print("[3] Computing similarity curve, valley depths, adaptive threshold...")
    similarities = [_cosine_similarity(embeddings[i], embeddings[i + 1]) for i in range(len(embeddings) - 1)]
    depths = compute_valley_depths(similarities)
    threshold = compute_threshold(depths, ctx.settings.system.note_segmentation.sensitivity_k)
    print(f"    threshold = {threshold:.4f} (sensitivity_k={ctx.settings.system.note_segmentation.sensitivity_k})")

    print("[4] Running segment_chunks() (the real engine function)...")
    candidates = segment_chunks(chunks, embeddings, ctx.settings)
    print(f"    {len(candidates)} candidate segments produced:")
    for c in candidates:
        preview = c.label[:60].encode("ascii", "ignore").decode("ascii")
        print(f"      - #{c.sequence_index + 1}: \"{preview}\" ({len(c.chunk_uids)} chunks)")

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    plot_segmentation_signal(label, chunks, similarities, depths, threshold, candidates, ASSETS_DIR / out_name)

    ctx.settings.system.chunking.size, ctx.settings.system.chunking.overlap = original_chunking
    return chunks, candidates


def main():
    print("=" * 80)
    print("  EGOVAULT TOPIC SEGMENTATION VISUALIZER (TextTiling, real embeddings)")
    print("=" * 80)

    settings = load_settings()
    ctx = build_context(settings)
    probe_provider(ctx)

    # Corpus A: synthetic, clean 3-topic boundaries (smaller chunk size for legibility)
    run_corpus(
        "Corpus A: Synthetic 3-Topic Sample (clean boundaries)",
        SAMPLE_TEXT, ctx, "segmentation_synthetic_signal.png",
        chunking_override=(100, 20),
    )

    # Corpus B: real, noisy 128-page book, production chunking config (first 20 pages for runtime)
    pdf_file = PROJECT_ROOT / "notebooks" / "assets" / "Marcus-Aurelius-Meditations.pdf"
    reader = pypdf.PdfReader(str(pdf_file))
    pages_text = [page.extract_text() for page in reader.pages[:20]]
    real_text = "\n\n".join(filter(None, pages_text))
    run_corpus(
        "Corpus B: Marcus Aurelius Meditations, first 20 pages (real, noisy)",
        real_text, ctx, "segmentation_real_signal.png",
    )

    print("\n" + "=" * 80)
    print("  DONE — segmentation signal visualized for both corpora.")
    print("=" * 80)


if __name__ == "__main__":
    main()
