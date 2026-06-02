from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.user import User, UserApprovalStatus, UserRole
from app.schemas.auth import (
    AuthTokenResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
    normalize_email,
)
from app.services.audit import audit_event
from app.services.passwords import hash_password, verify_password
from app.services.user_privacy import mask_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

INVALID_CREDENTIALS_DETAIL = "Неверный логин или пароль"


def _create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.auth_access_token_expire_minutes)
    payload = {
        "sub": user.external_id,
        "name": user.display_name,
        "email": user.email,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.auth_secret_key, algorithm=settings.auth_algorithm)


def _login_lookup(login: str, db: Session) -> User | None:
    normalized_email = normalize_email(login)
    return (
        db.query(User)
        .filter(or_(User.login == login, User.email == normalized_email))
        .first()
    )


def _ensure_registration_is_unique(data: RegisterRequest, db: Session) -> None:
    filters = [User.login == data.login]
    if data.email:
        filters.append(User.email == data.email)
    existing = db.query(User.id).filter(or_(*filters)).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким логином или email уже существует",
        )


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if not data.personal_data_notice_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо подтвердить уведомление об обработке персональных данных",
        )

    _ensure_registration_is_unique(data, db)
    user = User(
        external_id=f"local:{data.login}",
        login=data.login,
        password_hash=hash_password(data.password),
        display_name=data.display_name,
        email=data.email,
        role=UserRole.employee,
        approval_status=UserApprovalStatus.pending,
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit_event(
        action="auth.register",
        actor=user,
        target_type="user",
        target_id=user.id,
        details={"login": user.login, "email": mask_email(user.email)},
        db=db,
    )
    return RegisterResponse(
        user=UserResponse.from_user(user),
        message="Заявка создана и ожидает подтверждения экологом или администратором.",
    )


@router.post("/login", response_model=AuthTokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = _login_lookup(data.login, db)
    if user is None or not verify_password(data.password, user.password_hash):
        audit_event(
            action="auth.login",
            actor=None,
            target_type="user",
            outcome="failure",
            details={
                "login": mask_email(data.login) if "@" in data.login else data.login,
                "reason": "invalid_credentials",
            },
            db=db,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_DETAIL,
        )

    if not user.is_active or user.approval_status == UserApprovalStatus.rejected:
        audit_event(
            action="auth.login",
            actor=user,
            target_type="user",
            target_id=user.id,
            outcome="failure",
            details={"reason": "inactive_or_rejected"},
            db=db,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учетная запись отключена или отклонена.",
        )

    if user.approval_status == UserApprovalStatus.pending:
        audit_event(
            action="auth.login",
            actor=user,
            target_type="user",
            target_id=user.id,
            outcome="failure",
            details={"reason": "pending_approval"},
            db=db,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Заявка ожидает подтверждения экологом или администратором.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    audit_event(
        action="auth.login",
        actor=user,
        target_type="user",
        target_id=user.id,
        details={"login": user.login},
        db=db,
    )
    token = _create_access_token(user)
    return AuthTokenResponse(
        access_token=token,
        token=token,
        user=UserResponse.from_user(user),
    )


@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audit_event(
        action="auth.logout",
        actor=user,
        target_type="user",
        target_id=user.id,
        db=db,
    )
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse.from_user(user)
