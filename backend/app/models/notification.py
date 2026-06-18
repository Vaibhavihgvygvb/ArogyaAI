from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.enums import NotificationType, NotificationPriority, NotificationStatus


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    priority: Mapped[NotificationPriority] = mapped_column(Enum(NotificationPriority), nullable=False, default=NotificationPriority.MEDIUM)
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.UNREAD)
    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_user_status", "user_id", "status"),
        Index("ix_notifications_user_type", "user_id", "notification_type"),
        Index("ix_notifications_user_priority", "user_id", "priority"),
        Index("ix_notifications_created_at", "created_at"),
    )
