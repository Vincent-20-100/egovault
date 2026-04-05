from fastapi import APIRouter, Request
from core.schemas import PurgeResult
from tools.vault.purge import purge

router = APIRouter(prefix="/vault", tags=["vault"])


@router.post("/purge", response_model=PurgeResult)
def purge_endpoint(request: Request):
    return purge(request.app.state.settings)
