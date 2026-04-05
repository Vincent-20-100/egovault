"""
EgoVault FastAPI application.

Binds to 127.0.0.1:8000 (local only, no auth required).
Workflows run in a ThreadPoolExecutor — POST /ingest/* returns job_id immediately.
"""

import time as _time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import Settings, load_settings
from core.errors import IngestError
from infrastructure.context import build_context
from infrastructure.db import init_db, init_system_db, mark_orphan_jobs_failed

# ---------------------------------------------------------------------------
# In-memory rate limiting state.
# Module-level so the counter persists across requests within a process.
# ---------------------------------------------------------------------------
_ROUTE_LIMITS: dict[str, int] = {
    "/ingest": 10,
    "/search": 30,
    "/benchmark": 2,
}
_DEFAULT_LIMIT = 60
_request_counts: dict[str, list[float]] = defaultdict(list)


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Factory function — creates and configures the FastAPI app.
    Accepts optional settings for testing (uses load_settings() if not provided).
    """
    if settings is None:
        settings = load_settings()

    executor = ThreadPoolExecutor(max_workers=4)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: ensure DBs exist, mark orphan jobs failed
        init_db(
            settings.vault_db_path,
            dims=settings.system.embedding.dims,
            provider=settings.system.embedding.provider,
            model=settings.system.embedding.model,
        )
        init_system_db(settings.system_db_path)
        mark_orphan_jobs_failed(settings.system_db_path)

        # Configure tool logging callback.
        import core.logging as log_mod
        from infrastructure.db import get_system_connection
        from core.uid import generate_uid

        def _make_log_writer(system_db_path):
            def writer(uid, tool_name, input_json, output_json, duration_ms, status, error,
                       run_id=None, token_count=None, provider=None):
                conn = get_system_connection(system_db_path)
                conn.execute(
                    """INSERT INTO tool_logs
                       (uid, run_id, tool_name, input_json, output_json, duration_ms,
                        token_count, provider, status, error)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (uid, run_id, tool_name, input_json, output_json, duration_ms,
                     token_count, provider, status, error),
                )
                conn.commit()
                conn.close()
            return writer

        log_mod.configure(_make_log_writer(settings.system_db_path))

        yield

        # Shutdown: wait for running jobs to finish
        executor.shutdown(wait=False)

    app = FastAPI(title="EgoVault API", version="2.0.0", lifespan=lifespan)

    @app.exception_handler(IngestError)
    async def ingest_error_handler(request, exc: IngestError):
        return JSONResponse(status_code=exc.http_status, content={"error": exc.error_code, "message": exc.user_message})

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def rate_limit_middleware(request, call_next):
        from fastapi.responses import JSONResponse
        path = request.url.path
        now = _time.time()

        # Find matching rate limit (first prefix match wins)
        limit = _DEFAULT_LIMIT
        for prefix, max_req in _ROUTE_LIMITS.items():
            if path.startswith(prefix):
                limit = max_req
                break

        client = getattr(request.client, "host", "127.0.0.1")
        segment = path.split("/")[1] if len(path) > 1 else path
        key = f"{client}:{segment}"

        # Sliding window — keep only timestamps within the last 60 seconds
        _request_counts[key] = [t for t in _request_counts[key] if now - t < 60]

        if len(_request_counts[key]) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded"},
            )

        _request_counts[key].append(now)
        return await call_next(request)

    # Build the VaultContext (wires DB, embedding, LLM, vault writer providers).
    ctx = build_context(settings)
    app.state.ctx = ctx
    app.state.executor = executor

    # Mount routers
    from api.routers.health import router as health_router
    from api.routers.jobs import router as jobs_router
    from api.routers.ingest import router as ingest_router
    from api.routers.notes import router as notes_router
    from api.routers.sources import router as sources_router
    from api.routers.search import router as search_router
    from api.routers.vault import router as vault_router
    from api.routers.monitoring import router as monitoring_router

    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(ingest_router)
    app.include_router(notes_router)
    app.include_router(sources_router)
    app.include_router(search_router)
    app.include_router(vault_router)
    app.include_router(monitoring_router)

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="127.0.0.1", port=8000)
