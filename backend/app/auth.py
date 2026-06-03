from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, UserApprovalStatus, UserRole
from app.observability import user_id_ctx_var

security = HTTPBearer(auto_error=False)
optional_security = HTTPBearer(auto_error=False)
DEMO_USER_DISPLAY_NAME = "Тестовый пользователь"
STALE_DEMO_DISPLAY_NAMES = {
    "Старое демо-имя",
    "Dev employee",
    "Dev ecologist",
    "Dev admin",
}


def _decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.auth_secret_key, algorithms=[settings.auth_algorithm]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    external_id: str | None = payload.get("sub")
    if external_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    return payload


def _resolve_role(payload: dict, fallback: UserRole = UserRole.employee) -> UserRole:
    if settings.app_env not in {"development", "test"}:
        return fallback

    role_raw = payload.get("role")
    if isinstance(role_raw, str) and role_raw in UserRole._value2member_map_:
        return UserRole(role_raw)
    return fallback


def _normalize_dev_display_name(value: str | None) -> str | None:
    if not value:
        return value

    normalized = value.strip()
    if normalized in STALE_DEMO_DISPLAY_NAMES:
        return DEMO_USER_DISPLAY_NAME
    return normalized


def _get_or_create_user(payload: dict, db: Session) -> User:
    external_id = payload["sub"]
    should_align_dev_identity = settings.app_env in {"development", "test"}
    claimed_email = payload.get("email")
    user = db.query(User).filter(User.external_id == external_id).first()

    if (
        user is None
        and should_align_dev_identity
        and isinstance(claimed_email, str)
        and claimed_email
    ):
        user = db.query(User).filter(User.email == claimed_email).first()

    if user is None and not should_align_dev_identity:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if user is None:
        role = _resolve_role(payload, fallback=UserRole.employee)
        user = User(
            external_id=external_id,
            display_name=_normalize_dev_display_name(payload.get("name")) or "Пользователь",
            email=claimed_email or None,
            role=role,
            approval_status=UserApprovalStatus.approved,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # In development we keep DB identity aligned with selected dev token.
    desired_role = _resolve_role(payload, fallback=user.role)
    claimed_name = payload.get("name")
    changed = False
    if should_align_dev_identity and isinstance(claimed_name, str):
        claimed_name = _normalize_dev_display_name(claimed_name)

    if should_align_dev_identity and user.external_id != external_id:
        user.external_id = external_id
        changed = True
    if desired_role != user.role:
        user.role = desired_role
        changed = True
    if (
        should_align_dev_identity
        and isinstance(claimed_name, str)
        and claimed_name
        and user.display_name != claimed_name
    ):
        user.display_name = claimed_name
        changed = True
    if (
        should_align_dev_identity
        and isinstance(claimed_email, str)
        and claimed_email
        and user.email != claimed_email
    ):
        user.email = claimed_email
        changed = True

    if changed:
        db.commit()
        db.refresh(user)
    return user


def _ensure_user_can_authenticate(user: User) -> None:
    if not user.is_active or user.approval_status == UserApprovalStatus.rejected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not active",
        )


def _set_user_context(user: User) -> User:
    user_id_ctx_var.set(str(user.id))
    return user


def _token_from_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    if credentials is not None:
        return credentials.credentials
    cookie_token = request.cookies.get("gb_session")
    if cookie_token:
        return cookie_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = _decode_token(_token_from_request(request, credentials))
    user = _get_or_create_user(payload, db)
    _ensure_user_can_authenticate(user)
    return _set_user_context(user)


def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
) -> User | None:
    token = credentials.credentials if credentials is not None else request.cookies.get("gb_session")
    if not token:
        return None
    payload = _decode_token(token)
    user = _get_or_create_user(payload, db)
    _ensure_user_can_authenticate(user)
    return _set_user_context(user)


def require_role(*roles: UserRole):
    def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user.role.value} not allowed",
            )
        return user

    return checker
