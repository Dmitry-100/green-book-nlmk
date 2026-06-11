from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from jose import jwt
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_optional_user
from app.config import settings
from app.database import get_db
from app.models.user import User, UserApprovalStatus, UserRole
from app.schemas.auth import (
    AuthTokenResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from app.services.audit import audit_event
from app.services.passwords import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

INVALID_CREDENTIALS_DETAIL = "Неверный логин или пароль"


def _create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.auth_access_token_expire_minutes)
    payload = {
        "sub": user.external_id,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, settings.auth_secret_key, algorithm=settings.auth_algorithm)


def _login_lookup(login: str, db: Session) -> User | None:
    return db.query(User).filter(User.login == login).first()


def _ensure_registration_is_unique(data: RegisterRequest, db: Session) -> None:
    existing = db.query(User.id).filter(User.login == data.login).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким логином уже существует",
        )


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if not data.personal_data_notice_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо подтвердить уведомление об обработке персональных данных",
        )
    if data.privacy_notice_version != settings.privacy_notice_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Версия уведомления об обработке данных устарела. Обновите страницу.",
        )

    _ensure_registration_is_unique(data, db)
    now = datetime.now(timezone.utc)
    user = User(
        external_id=f"local:{data.login}",
        login=data.login,
        password_hash=hash_password(data.password),
        display_name=data.display_name,
        email=None,
        role=UserRole.employee,
        approval_status=UserApprovalStatus.approved,
        is_active=True,
        must_change_password=False,
        approved_at=now,
        approved_by_id=None,
        privacy_notice_version=data.privacy_notice_version,
        privacy_notice_accepted_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit_event(
        action="auth.register",
        actor=user,
        target_type="user",
        target_id=user.id,
        details={"login": user.login, "privacy_notice_version": data.privacy_notice_version},
        db=db,
    )
    return RegisterResponse(
        user=UserResponse.from_user(user),
        message="Регистрация завершена. Можно войти.",
    )


@router.post("/login", response_model=AuthTokenResponse)
def login(
    data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    user = _login_lookup(data.login, db)
    if user is None or not user.password_hash or not verify_password(data.password, user.password_hash):
        audit_event(
            action="auth.login",
            actor=None,
            target_type="user",
            outcome="failure",
            details={
                "login": data.login,
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

    now = datetime.now(timezone.utc)
    if user.approval_status == UserApprovalStatus.pending:
        user.approval_status = UserApprovalStatus.approved
        user.approved_at = now
        user.approved_by_id = None

    user.last_login_at = now
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
    response.set_cookie(
        "gb_session",
        token,
        max_age=settings.auth_access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.app_env not in {"development", "test"},
        samesite="lax",
    )
    return AuthTokenResponse(
        access_token=token,
        token=token,
        user=UserResponse.from_user(user),
    )


@router.post("/logout")
def logout(
    response: Response,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    audit_event(
        action="auth.logout",
        actor=user,
        target_type="user",
        target_id=user.id if user else None,
        db=db,
    )
    response.delete_cookie(
        "gb_session",
        httponly=True,
        secure=settings.app_env not in {"development", "test"},
        samesite="lax",
    )
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse.from_user(user)
