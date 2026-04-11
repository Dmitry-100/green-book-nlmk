from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.observability import user_id_ctx_var

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


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


def _get_or_create_user(payload: dict, db: Session) -> User:
    external_id = payload["sub"]
    user = db.query(User).filter(User.external_id == external_id).first()

    if user is None:
        role = _resolve_role(payload, fallback=UserRole.employee)
        user = User(
            external_id=external_id,
            display_name=payload.get("name", "Unknown"),
            email=payload.get("email", f"{external_id}@nlmk.com"),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # In development we keep DB role aligned with selected dev token role.
    desired_role = _resolve_role(payload, fallback=user.role)
    if desired_role != user.role:
        user.role = desired_role
        db.commit()
        db.refresh(user)
    return user


def _set_user_context(user: User) -> User:
    user_id_ctx_var.set(str(user.id))
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = _decode_token(credentials.credentials)
    user = _get_or_create_user(payload, db)
    return _set_user_context(user)


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    payload = _decode_token(credentials.credentials)
    user = _get_or_create_user(payload, db)
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
