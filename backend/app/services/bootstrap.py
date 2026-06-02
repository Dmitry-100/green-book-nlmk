from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User, UserApprovalStatus, UserRole
from app.schemas.auth import normalize_display_name, normalize_email, normalize_login
from app.services.audit import audit_event
from app.services.passwords import hash_password
from app.services.user_privacy import mask_email


def ensure_bootstrap_admin(db: Session) -> User | None:
    if not settings.bootstrap_admin_login:
        return None

    login = normalize_login(settings.bootstrap_admin_login)
    existing = db.query(User).filter(User.login == login).first()
    if existing is not None:
        return existing

    password = settings.bootstrap_admin_password
    if not password:
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD is required")

    display_name = normalize_display_name(
        settings.bootstrap_admin_display_name or "Администратор"
    )
    email = normalize_email(settings.bootstrap_admin_email)
    now = datetime.now(timezone.utc)
    admin = User(
        external_id=f"local:{login}",
        login=login,
        password_hash=hash_password(password),
        display_name=display_name,
        email=email,
        role=UserRole.admin,
        approval_status=UserApprovalStatus.approved,
        is_active=True,
        must_change_password=True,
        approved_at=now,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    audit_event(
        action="auth.bootstrap_admin",
        actor=admin,
        target_type="user",
        target_id=admin.id,
        details={"login": login, "email": mask_email(email)},
        db=db,
    )
    return admin
