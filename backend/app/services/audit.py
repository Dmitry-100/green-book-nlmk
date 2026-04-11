import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User
from app.observability import request_id_ctx_var

logger = logging.getLogger("app.audit")


def audit_event(
    *,
    action: str,
    actor: User | None,
    target_type: str,
    target_id: int | None = None,
    outcome: str = "success",
    details: dict[str, Any] | None = None,
    db: Session | None = None,
) -> None:
    normalized_details = details or {}
    actor_user_id = actor.id if actor else None
    actor_role = actor.role.value if actor else None
    request_id = request_id_ctx_var.get()

    logger.info(
        "audit_event",
        extra={
            "audit_action": action,
            "audit_actor_user_id": actor_user_id,
            "audit_actor_role": actor_role,
            "target_type": target_type,
            "target_id": target_id,
            "outcome": outcome,
            "details": normalized_details,
            "request_id": request_id,
        },
    )

    if db is None:
        return

    try:
        db.add(
            AuditLog(
                action=action,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                target_type=target_type,
                target_id=target_id,
                outcome=outcome,
                details=normalized_details,
                request_id=request_id,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "audit_event_persist_failed",
            extra={
                "audit_action": action,
                "audit_actor_user_id": actor_user_id,
                "target_type": target_type,
                "target_id": target_id,
            },
        )
