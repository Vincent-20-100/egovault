"""Monitoring router — read-only access to workflow runs and tool logs."""

from fastapi import APIRouter, HTTPException, Request, Query

from api.models import (
    WorkflowRunResponse,
    WorkflowRunDetailResponse,
    WorkflowRunCostResponse,
)
from infrastructure.db import get_workflow_runs, get_workflow_run_detail, get_workflow_run_cost

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/runs", response_model=list[WorkflowRunResponse])
def list_runs(
    request: Request,
    status: str | None = Query(None),
    workflow: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    ctx = request.app.state.ctx
    runs = get_workflow_runs(ctx.system_db_path, status=status, workflow=workflow, limit=limit)
    return runs


@router.get("/runs/{run_id}", response_model=WorkflowRunDetailResponse)
def get_run_detail(run_id: str, request: Request):
    ctx = request.app.state.ctx
    detail = get_workflow_run_detail(ctx.system_db_path, run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return detail


@router.get("/runs/{run_id}/cost", response_model=WorkflowRunCostResponse)
def get_run_cost(run_id: str, request: Request):
    ctx = request.app.state.ctx
    cost = get_workflow_run_cost(ctx.system_db_path, run_id)
    if cost is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return cost
