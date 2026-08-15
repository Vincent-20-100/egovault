"""
Disk-backed embedding cache for notebooks.

Ollama embedding is a real network round-trip per text. Notebooks re-run the
same corpus (e.g. 293 Marcus Aurelius chunks) repeatedly during iteration; this
cache makes every run after the first free and keeps the real provider as the
only source of vectors (no mock fallback).
"""

import hashlib
import json
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / ".cache"


def _cache_path(text: str, model: str, dims: int) -> Path:
    key = hashlib.sha256(f"{model}:{dims}:{text}".encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{key}.json"


def get_or_embed(texts: list[str], ctx, progress_every: int = 50) -> list[list[float]]:
    """
    Return one embedding per text, using infrastructure's real embedding
    provider (ctx.embed) on a cache miss. Raises whatever ctx.embed raises on
    the first miss (e.g. RuntimeError if Ollama is unreachable) — no silent
    mock fallback.
    """
    model = ctx.settings.system.embedding.model
    dims = ctx.settings.system.embedding.dims
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    vectors: list[list[float]] = []
    misses = 0
    for i, text in enumerate(texts):
        path = _cache_path(text, model, dims)
        if path.exists():
            vectors.append(json.loads(path.read_text(encoding="utf-8")))
            continue
        vector = ctx.embed(text)
        path.write_text(json.dumps(vector), encoding="utf-8")
        vectors.append(vector)
        misses += 1
        if progress_every and misses % progress_every == 0:
            print(f"    ...embedded {misses} new texts so far ({i + 1}/{len(texts)} processed)")

    print(f"Embedding cache: {len(texts) - misses} hits, {misses} misses (model={model}, dims={dims}).")
    return vectors


def wrap_ctx_embed(ctx) -> None:
    """
    Replace ctx.embed with a disk-cached version, in place. Use this before
    passing ctx into engine functions (ingest, curate, segment_chunks) that
    call ctx.embed internally per-chunk — they get caching for free without
    any change to engine code.
    """
    real_embed = ctx.embed
    model = ctx.settings.system.embedding.model
    dims = ctx.settings.system.embedding.dims
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def cached_embed(text: str) -> list[float]:
        path = _cache_path(text, model, dims)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        vector = real_embed(text)
        path.write_text(json.dumps(vector), encoding="utf-8")
        return vector

    ctx.embed = cached_embed


def probe_provider(ctx) -> None:
    """Fail fast with a clear message if the embedding provider is unreachable."""
    try:
        ctx.embed("ping")
    except Exception as e:
        raise RuntimeError(
            "Embedding provider unreachable. This notebook requires real embeddings "
            f"(provider={ctx.settings.system.embedding.provider}, model={ctx.settings.system.embedding.model}). "
            "Start Ollama and run `ollama pull nomic-embed-text`, then re-run this cell.\n"
            f"Underlying error: {e}"
        ) from e
