from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: int
    action: str
    actor_user_id: int | None
    actor_role: str | None
    target_type: str
    target_id: int | None
    outcome: str
    details: dict[str, Any]
    request_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int | None = None


class AuditPurgeResponse(BaseModel):
    dry_run: bool
    older_than_days: int
    cutoff_iso: str
    candidates: int
    deleted: int
