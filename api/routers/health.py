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


def _ping_db(db_path) -> bool:
    try:
        from infrastructure.db import get_vault_connection
        conn = get_vault_connection(db_path)
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    ollama_up = _ping_ollama(settings.install.providers.ollama_base_url)
    db_ok = _ping_db(settings.vault_db_path)
    return HealthResponse(
        api="ok",
        ollama="up" if ollama_up else "down",
        db="ok" if db_ok else "error",
    )
