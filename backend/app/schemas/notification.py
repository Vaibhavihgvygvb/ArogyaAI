from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import NotificationType, NotificationPriority, NotificationStatus


class NotificationCreate(BaseModel):
    user_id: int
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    metadata_json: str | None = Field(default=None, max_length=5000)
    action_url: str | None = Field(default=None, max_length=500)


class NotificationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    message: str | None = Field(default=None, min_length=1)


class NotificationMarkReadRequest(BaseModel):
    notification_ids: list[int] = Field(min_length=1)


class NotificationMarkAllReadRequest(BaseModel):
    notification_type: NotificationType | None = None


class NotificationFilters(BaseModel):
    notification_type: NotificationType | None = None
    priority: NotificationPriority | None = None
    status: NotificationStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    notification_type: NotificationType
    priority: NotificationPriority
    status: NotificationStatus
    is_read: bool
    metadata_json: str | None
    action_url: str | None
    created_at: datetime
    updated_at: datetime | None
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    skip: int
    limit: int
