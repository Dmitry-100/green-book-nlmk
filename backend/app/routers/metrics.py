from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.auth import require_role
from app.models.user import User, UserRole
from app.services.metrics import (
    request_metrics_prometheus_text,
    request_metrics_snapshot,
)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("")
def metrics_snapshot(user: User = Depends(require_role(UserRole.admin))):
    del user
    return request_metrics_snapshot()


@router.get("/prometheus")
def metrics_prometheus(user: User = Depends(require_role(UserRole.admin))):
    del user
    return PlainTextResponse(
        content=request_metrics_prometheus_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
