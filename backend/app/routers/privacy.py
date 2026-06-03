from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


class PrivacyNoticeResponse(BaseModel):
    version: str
    operator_name: str
    processing_purpose: str
    data_categories: list[str]
    retention_text: str
    contact_text: str


@router.get("/notice", response_model=PrivacyNoticeResponse)
def get_privacy_notice():
    return PrivacyNoticeResponse(
        version=settings.privacy_notice_version,
        operator_name=settings.privacy_operator_name,
        processing_purpose=settings.privacy_processing_purpose,
        data_categories=[
            "логин",
            "отображаемое имя или псевдоним",
            "хеш пароля",
            "наблюдения, комментарии, фото и координаты места наблюдения",
            "служебные события входа, модерации и администрирования",
        ],
        retention_text=settings.privacy_retention_text,
        contact_text=settings.privacy_contact_text,
    )
