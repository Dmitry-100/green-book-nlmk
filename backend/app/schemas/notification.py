from datetime import datetime
from pydantic import BaseModel
from app.models.notification import NotificationType


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    observation_id: int | None
    type: NotificationType
    message: str
    is_read: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
