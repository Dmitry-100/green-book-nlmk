from fastapi import APIRouter, HTTPException
from jose import jwt

from app.config import settings

router = APIRouter(prefix="/api/dev", tags=["dev-auth"])


@router.post("/token")
def generate_dev_token(
    name: str = "Сотрудник Тестовый",
    email: str = "test@nlmk.com",
    role: str = "employee",
):
    """Generate a dev JWT token. Only available in development mode."""
    if settings.app_env != "development" or not settings.enable_dev_auth:
        raise HTTPException(status_code=403, detail="Dev endpoints are disabled")

    external_id = f"dev-{role}-{email.split('@')[0]}"
    payload = {
        "sub": external_id,
        "name": name,
        "email": email,
        "role": role,
    }
    token = jwt.encode(payload, settings.auth_secret_key, algorithm=settings.auth_algorithm)
    return {
        "access_token": token,
        "token_type": "bearer",
        "token": token,  # Backward-compatible alias for existing clients.
        "user": payload,
    }
