"""
Shared 4-strategy semantic segmentation benchmark: strategies, metrics, plots.

Used by both the Marcus Aurelius (book prose) and podcast (spoken discourse)
benchmark notebooks, so the same scoring applies to both corpora.

Scoring deliberately does NOT reward uniform segment size. The goal is semantic
coherence, not uniform chunking — a single powerful one-chunk idea and a
50-chunk passage about one central idea are equally valid note candidates.
`size_min`/`size_max`/`size_std` are reported precisely to expose which
strategies structurally suppress that asymmetry (hard cluster/size caps) versus
which let segment size emerge purely from where the semantic signal breaks.
"""
import time
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.sparse import lil_matrix
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import PCA

from core.schemas import NoteCandidate
from tools.text.segment import segment_chunks, _cosine_similarity


# --- Strategy 1: Two-Stage Hierarchical TextTiling ---
def two_stage_hierarchical(chunks, embeddings, settings, min_chunks: int = 4, max_chunks: int = 25, sim_threshold: float = 0.65):
    settings.system.note_segmentation.sensitivity_k = 0.4
    stage1_cands = segment_chunks(chunks, embeddings, settings)

    uid_to_idx = {c.uid: i for i, c in enumerate(chunks)}

    def cand_centroid(uids):
        vecs = [embeddings[uid_to_idx[uid]] for uid in uids]
        c_vec = np.mean(vecs, axis=0)
        norm = np.linalg.norm(c_vec)
        return (c_vec / norm).tolist() if norm > 0 else c_vec.tolist()

    merged_groups = []
    curr_uids = list(stage1_cands[0].chunk_uids)
    curr_label = stage1_cands[0].label

    now = datetime.now(timezone.utc)
    for next_cand in stage1_cands[1:]:
        c1 = cand_centroid(curr_uids)
        c2 = cand_centroid(next_cand.chunk_uids)
        sim = _cosine_similarity(c1, c2)

        if (sim >= sim_threshold or len(curr_uids) < min_chunks) and (len(curr_uids) + len(next_cand.chunk_uids) <= max_chunks):
            curr_uids.extend(next_cand.chunk_uids)
        else:
            merged_groups.append((curr_label, curr_uids))
            curr_uids = list(next_cand.chunk_uids)
            curr_label = next_cand.label

    merged_groups.append((curr_label, curr_uids))

    results = []
    for idx, (lbl, uids) in enumerate(merged_groups):
        first_idx = uid_to_idx[uids[0]]
        last_idx = uid_to_idx[uids[-1]]
        results.append(NoteCandidate(
            uid=f"stage2_{idx}",
            source_uid="source_demo",
            label=lbl,
            locator=f"chunk {first_idx}-{last_idx}",
            chunk_uids=uids,
            sequence_index=idx,
            model_version="1.0",
            created_at=now.isoformat(),
        ))
    return results


# --- Strategy 2: Contiguity-Constrained Agglomerative Clustering ---
def constrained_agglomerative(chunks, embeddings, target_clusters: int = 16):
    n = len(chunks)
    adj = lil_matrix((n, n), dtype=int)
    for i in range(n - 1):
        adj[i, i + 1] = 1
        adj[i + 1, i] = 1

    model = AgglomerativeClustering(n_clusters=target_clusters, connectivity=adj, metric='cosine', linkage='average')
    labels = model.fit_predict(embeddings)

    clusters = []
    curr_label = labels[0]
    curr_uids = [chunks[0].uid]
    curr_first = 0

    for i in range(1, n):
        if labels[i] == curr_label:
            curr_uids.append(chunks[i].uid)
        else:
            clusters.append((curr_first, i - 1, curr_uids))
            curr_label = labels[i]
            curr_uids = [chunks[i].uid]
            curr_first = i
    clusters.append((curr_first, n - 1, curr_uids))

    now = datetime.now(timezone.utc)
    results = []
    for idx, (f_idx, l_idx, uids) in enumerate(clusters):
        first_chunk = chunks[f_idx]
        results.append(NoteCandidate(
            uid=f"ahc_{idx}",
            source_uid="source_demo",
            label=first_chunk.content[:100],
            locator=f"chunk {f_idx}-{l_idx}",
            chunk_uids=uids,
            sequence_index=idx,
            model_version="1.0",
            created_at=now.isoformat(),
        ))
    return results


# --- Strategy 3: Gaussian Kernel Smoothed TextTiling ---
def gaussian_smoothed_texttiling(chunks, embeddings, settings, sigma: float = 2.0):
    now = datetime.now(timezone.utc)
    cosines = [
        _cosine_similarity(embeddings[i], embeddings[i + 1])
        for i in range(len(embeddings) - 1)
    ]
    smoothed = gaussian_filter1d(cosines, sigma=sigma)

    mean_sim = float(np.mean(smoothed))
    std_sim = float(np.std(smoothed))
    threshold = mean_sim - settings.system.note_segmentation.sensitivity_k * std_sim

    valleys = []
    for i in range(1, len(smoothed) - 1):
        if smoothed[i] < smoothed[i - 1] and smoothed[i] < smoothed[i + 1] and smoothed[i] <= threshold:
            valleys.append(i + 1)

    boundaries = [0] + valleys + [len(chunks)]
    results = []
    for idx in range(len(boundaries) - 1):
        f_idx = boundaries[idx]
        l_idx = boundaries[idx + 1] - 1
        sub_chunks = chunks[f_idx:l_idx + 1]
        results.append(NoteCandidate(
            uid=f"gauss_{idx}",
            source_uid="source_demo",
            label=sub_chunks[0].content[:100],
            locator=f"chunk {f_idx}-{l_idx}",
            chunk_uids=[c.uid for c in sub_chunks],
            sequence_index=idx,
            model_version="1.0",
            created_at=now.isoformat(),
        ))
    return results, cosines, smoothed, valleys


def compute_metrics(candidates: list[NoteCandidate], raw_cosines: list[float], runtime_s: float) -> dict:
    """
    Score a segmentation against the method-independent consecutive-cosine signal:
    cohesion = mean similarity strictly inside segments, separation = mean similarity
    AT the chosen boundaries. A good segmentation has high cohesion and low separation
    (a real semantic drop at every cut). Size stats are reported, not optimized —
    a narrow size range signals the method is imposing uniformity rather than
    following the semantic signal.
    """
    boundary_idxs = set()
    running = 0
    for cand in candidates[:-1]:
        running += len(cand.chunk_uids)
        if running - 1 < len(raw_cosines):
            boundary_idxs.add(running - 1)

    cohesion_vals = [raw_cosines[i] for i in range(len(raw_cosines)) if i not in boundary_idxs]
    separation_vals = [raw_cosines[i] for i in boundary_idxs]
    cohesion = float(np.mean(cohesion_vals)) if cohesion_vals else float("nan")
    separation = float(np.mean(separation_vals)) if separation_vals else float("nan")

    sizes = [len(c.chunk_uids) for c in candidates]
    return {
        "n_candidates": len(candidates),
        "cohesion": cohesion,
        "separation": separation,
        "contrast": cohesion - separation,
        "sizes": sizes,
        "size_min": min(sizes),
        "size_max": max(sizes),
        "size_range": max(sizes) - min(sizes),
        "size_mean": float(np.mean(sizes)),
        "size_std": float(np.std(sizes)),
        "runtime_s": runtime_s,
    }


def run_benchmark(chunks, embeddings, settings, baseline_k: float = 1.2):
    raw_cosines = [_cosine_similarity(embeddings[i], embeddings[i + 1]) for i in range(len(embeddings) - 1)]

    results = {}

    settings.system.note_segmentation.sensitivity_k = baseline_k
    t0 = time.perf_counter()
    cands_baseline = segment_chunks(chunks, embeddings, settings)
    results["Baseline TextTiling"] = (cands_baseline, compute_metrics(cands_baseline, raw_cosines, time.perf_counter() - t0))

    t0 = time.perf_counter()
    cands_two_stage = two_stage_hierarchical(chunks, embeddings, settings, min_chunks=4, max_chunks=25, sim_threshold=0.65)
    results["Two-Stage Hierarchical Merging"] = (cands_two_stage, compute_metrics(cands_two_stage, raw_cosines, time.perf_counter() - t0))

    n_target = max(2, len(chunks) // 18)  # scale cluster target to corpus length instead of a fixed 16
    t0 = time.perf_counter()
    cands_ahc = constrained_agglomerative(chunks, embeddings, target_clusters=n_target)
    results[f"Constrained AHC ({n_target} clusters)"] = (cands_ahc, compute_metrics(cands_ahc, raw_cosines, time.perf_counter() - t0))

    t0 = time.perf_counter()
    cands_gaussian, _, _, _ = gaussian_smoothed_texttiling(chunks, embeddings, settings, sigma=2.0)
    results["Gaussian Smoothed Minima"] = (cands_gaussian, compute_metrics(cands_gaussian, raw_cosines, time.perf_counter() - t0))

    return results, raw_cosines


def plot_strategy_bands(chunks, results, title_prefix: str, out_path: Path):
    fig, axes = plt.subplots(len(results), 1, figsize=(14, 10), sharex=True, dpi=130)
    cmap = plt.get_cmap('tab20')
    for ax, (title, (cands_list, metrics)) in zip(axes, results.items()):
        ax.set_xlim(0, len(chunks))
        ax.set_ylim(0, 1)
        ax.set_yticks([])
        ax.set_title(
            f"{title} — {len(cands_list)} candidates, contrast={metrics['contrast']:.3f}, "
            f"size {metrics['size_min']}-{metrics['size_max']}, {metrics['runtime_s']*1000:.0f}ms",
            fontsize=11, fontweight='bold', pad=4,
        )
        curr = 0
        for idx, cand in enumerate(cands_list):
            num_c = len(cand.chunk_uids)
            ax.axvspan(curr, curr + num_c, color=cmap(idx % 20), alpha=0.6, ec='black', lw=0.8)
            if num_c >= 3:
                ax.text(curr + num_c / 2, 0.5, f"#{idx+1} ({num_c}c)", ha='center', va='center', fontsize=7, fontweight='bold')
            curr += num_c

    axes[-1].set_xlabel(f"Chunk position index (0 to {len(chunks)} chunks)", fontsize=11)
    fig.suptitle(f"{title_prefix} — 4 Strategies, Real Embeddings", fontsize=14, fontweight='bold')
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_metrics_comparison(results, title_prefix: str, out_path: Path):
    names = list(results.keys())
    cohesion = [m["cohesion"] for _, m in results.values()]
    separation = [m["separation"] for _, m in results.values()]
    contrast = [m["contrast"] for _, m in results.values()]
    runtime_ms = [m["runtime_s"] * 1000 for _, m in results.values()]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=140)

    x = np.arange(len(names))
    width = 0.35
    ax1.bar(x - width / 2, cohesion, width, label="Cohesion (higher=better)", color="#55a868")
    ax1.bar(x + width / 2, separation, width, label="Separation at boundaries (lower=better)", color="#c44e52")
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, rotation=20, ha="right", fontsize=8)
    ax1.set_ylabel("Mean cosine similarity")
    ax1.set_title(f"{title_prefix}: Cohesion vs. Separation", fontsize=12, fontweight="bold")
    ax1.legend(fontsize=8)
    ax1.grid(True, linestyle="--", alpha=0.3, axis="y")
    for i, c in enumerate(contrast):
        ax1.text(i, max(cohesion[i], separation[i]) + 0.01, f"Δ={c:.3f}", ha="center", fontsize=8, fontweight="bold")

    ax2.bar(x, runtime_ms, color="#4c72b0", width=0.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels(names, rotation=20, ha="right", fontsize=8)
    ax2.set_ylabel("Wall-clock runtime (ms)")
    ax2.set_title(f"{title_prefix}: Runtime per Strategy", fontsize=12, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_size_distribution(results, title_prefix: str, out_path: Path):
    """
    Exposes uniformity bias directly: a narrow box/whisker range means the
    strategy is forcing similarly-sized segments regardless of where the
    semantic signal actually breaks — a small powerful idea and a long
    single-idea passage should both be representable.
    """
    names = list(results.keys())
    sizes_per_strategy = [m["sizes"] for _, m in results.values()]

    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    bp = ax.boxplot(sizes_per_strategy, tick_labels=names, showmeans=True, patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor('#8172b8')
        patch.set_alpha(0.6)
    ax.set_ylabel("Segment size (chunks)")
    ax.set_title(f"{title_prefix}: Segment Size Distribution — Uniformity Bias Check", fontsize=12, fontweight="bold")
    ax.set_xticklabels(names, rotation=15, ha="right", fontsize=8)
    ax.grid(True, linestyle="--", alpha=0.3, axis="y")

    for i, (name, (_, m)) in enumerate(results.items()):
        ax.annotate(f"range={m['size_range']}", (i + 1, m['size_max']), textcoords="offset points",
                    xytext=(0, 8), ha='center', fontsize=8, fontweight='bold')

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_pca_topology(chunks, embeddings, candidates, n_components: int, title_prefix: str, out_path: Path):
    pca = PCA(n_components=n_components)
    coords = pca.fit_transform(embeddings)

    uid_map = {c.uid: i for i, c in enumerate(chunks)}
    cluster_ids = np.zeros(len(chunks), dtype=int)
    for cand_idx, cand in enumerate(candidates):
        for uid in cand.chunk_uids:
            cluster_ids[uid_map[uid]] = cand_idx

    if n_components == 2:
        fig, ax = plt.subplots(figsize=(10, 8), dpi=140)
        ax.plot(coords[:, 0], coords[:, 1], color='gray', linestyle='-', alpha=0.3, linewidth=1.0)
        ax.scatter(coords[:, 0], coords[:, 1], c=cluster_ids, cmap='tab20', s=45, edgecolors='black', linewidth=0.5, alpha=0.85)
        for cand_idx, cand in enumerate(candidates):
            indices = [uid_map[uid] for uid in cand.chunk_uids]
            c_x, c_y = np.mean(coords[indices, 0]), np.mean(coords[indices, 1])
            ax.annotate(f"#{cand_idx+1}", (c_x, c_y), fontsize=8, fontweight='bold', ha='center', va='center',
                        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="black", lw=1, alpha=0.8))
        ax.set_title(f"{title_prefix}: 2D Vector Topology (PCA)", fontsize=13, fontweight='bold', pad=12)
        ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% var)")
        ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% var)")
        ax.grid(True, linestyle='--', alpha=0.3)
        fig.tight_layout()
    else:
        fig = plt.figure(figsize=(10, 8), dpi=140)
        ax = fig.add_subplot(111, projection='3d')
        ax.plot(coords[:, 0], coords[:, 1], coords[:, 2], color='gray', linestyle='-', alpha=0.3, linewidth=1.0)
        ax.scatter(coords[:, 0], coords[:, 1], coords[:, 2], c=cluster_ids, cmap='tab20', s=45, edgecolors='black', linewidth=0.5, alpha=0.85)
        ax.set_title(f"{title_prefix}: 3D Vector Topology (PCA)", fontsize=13, fontweight='bold', pad=12)
        ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)", fontsize=9)
        ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)", fontsize=9)
        ax.set_zlabel(f"PC3 ({pca.explained_variance_ratio_[2]*100:.1f}%)", fontsize=9)
        ax.view_init(elev=25, azim=45)
        fig.tight_layout()

    fig.savefig(out_path)
    plt.close(fig)


def print_metrics_table(results: dict):
    header = f"{'Strategy':<32} {'#Cand':>6} {'Cohesion':>9} {'Separation':>11} {'Contrast':>9} {'Size (min-max)':>15} {'Runtime':>9}"
    print(header)
    print("-" * len(header))
    for name, (_, m) in results.items():
        size_range = f"{m['size_min']}-{m['size_max']}"
        print(
            f"{name:<32} {m['n_candidates']:>6} {m['cohesion']:>9.4f} {m['separation']:>11.4f} "
            f"{m['contrast']:>9.4f} {size_range:>15} {m['runtime_s']*1000:>8.0f}ms"
        )
