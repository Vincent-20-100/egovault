"""Health check router — DB connectivity and service status."""

from fastapi import APIRouter, Request
import requests

from api.models import HealthResponse

router = APIRouter(tags=["health"])


def _ping_ollama(base_url: str) -> bool:
    try:
        r = requests.get(base_url, timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _ping_db(db) -> bool:
    # Delegate to VaultDB.ping() — avoids a direct infrastructure.db import
    try:
        return db.ping()
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    ctx = request.app.state.ctx
    ollama_up = _ping_ollama(ctx.settings.install.providers.ollama_base_url)
    db_ok = _ping_db(ctx.db)
    return HealthResponse(
        api="ok",
        ollama="up" if ollama_up else "down",
        db="ok" if db_ok else "error",
    )
