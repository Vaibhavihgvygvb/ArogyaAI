import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func as sa_func, or_
from sqlalchemy.orm import Session

from app.cache.service import CacheService
from app.core.config import settings
from app.models.notification import Notification
from app.models.user import User
from app.models.enums import NotificationType, NotificationPriority, NotificationStatus, UserRole
from app.schemas.notification import NotificationCreate, NotificationUpdate, NotificationFilters


class NotificationValidationError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        self.status_code = status_code
        super().__init__(message)


class NotificationService:

    @staticmethod
    def _validate_user_exists(db: Session, user_id: int) -> User:
        user = db.get(User, user_id)
        if not user:
            raise NotificationValidationError("User not found", status_code=404)
        return user

    @staticmethod
    def _validate_notification_exists(db: Session, notification_id: int) -> Notification | None:
        return db.get(Notification, notification_id)

    @staticmethod
    def _validate_not_archived(notification: Notification) -> None:
        if notification.status == NotificationStatus.ARCHIVED:
            raise NotificationValidationError(
                "Archived notifications cannot be modified", status_code=400
            )

    @staticmethod
    def _check_duplicate(
        db: Session, user_id: int, title: str, message: str, notification_type: NotificationType
    ) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        existing = db.scalar(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.title == title,
                Notification.message == message,
                Notification.notification_type == notification_type,
                Notification.created_at >= cutoff,
            )
        )
        if existing is not None:
            raise NotificationValidationError(
                "Duplicate notification detected", status_code=409
            )

    @staticmethod
    def create_notification(
        db: Session, notification_data: NotificationCreate
    ) -> Notification:
        NotificationService._validate_user_exists(db, notification_data.user_id)

        NotificationService._check_duplicate(
            db,
            notification_data.user_id,
            notification_data.title,
            notification_data.message,
            notification_data.notification_type,
        )

        notification = Notification(
            user_id=notification_data.user_id,
            title=notification_data.title,
            message=notification_data.message,
            notification_type=notification_data.notification_type,
            priority=notification_data.priority,
            metadata_json=notification_data.metadata_json,
            action_url=notification_data.action_url,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        CacheService.invalidate_key(
            CacheService.build_key(CacheService.NAMESPACE_NOTIFICATION, "unread", str(notification_data.user_id))
        )
        return notification

    @staticmethod
    def get_notification(db: Session, notification_id: int) -> Notification | None:
        return NotificationService._validate_notification_exists(db, notification_id)

    @staticmethod
    def list_notifications(
        db: Session,
        user_id: int | None = None,
        user_role: UserRole | None = None,
        filters: NotificationFilters | None = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Notification], int]:
        stmt = select(Notification)
        count_stmt = select(sa_func.count(Notification.id))

        if user_role != UserRole.ADMIN:
            if user_id is not None:
                stmt = stmt.where(Notification.user_id == user_id)
                count_stmt = count_stmt.where(Notification.user_id == user_id)

        if filters:
            if filters.notification_type is not None:
                stmt = stmt.where(Notification.notification_type == filters.notification_type)
                count_stmt = count_stmt.where(Notification.notification_type == filters.notification_type)
            if filters.priority is not None:
                stmt = stmt.where(Notification.priority == filters.priority)
                count_stmt = count_stmt.where(Notification.priority == filters.priority)
            if filters.status is not None:
                stmt = stmt.where(Notification.status == filters.status)
                count_stmt = count_stmt.where(Notification.status == filters.status)
            if filters.date_from is not None:
                stmt = stmt.where(Notification.created_at >= filters.date_from)
                count_stmt = count_stmt.where(Notification.created_at >= filters.date_from)
            if filters.date_to is not None:
                stmt = stmt.where(Notification.created_at <= filters.date_to)
                count_stmt = count_stmt.where(Notification.created_at <= filters.date_to)

        sort_column = getattr(Notification, sort_by, Notification.created_at)
        if sort_order == "asc":
            stmt = stmt.order_by(sort_column.asc())
        else:
            stmt = stmt.order_by(sort_column.desc())

        total = db.scalar(count_stmt) or 0
        stmt = stmt.offset(skip).limit(limit)
        notifications = list(db.scalars(stmt).all())
        return notifications, total

    @staticmethod
    def mark_as_read(db: Session, notification_id: int) -> Notification | None:
        notification = NotificationService._validate_notification_exists(db, notification_id)
        if not notification:
            return None
        NotificationService._validate_not_archived(notification)
        if notification.status != NotificationStatus.READ:
            notification.status = NotificationStatus.READ
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(notification)
        CacheService.invalidate_key(
            CacheService.build_key(CacheService.NAMESPACE_NOTIFICATION, "unread", str(notification.user_id))
        )
        return notification

    @staticmethod
    def mark_multiple_as_read(db: Session, notification_ids: list[int], user_id: int) -> int:
        now = datetime.now(timezone.utc)
        result = db.execute(
            select(Notification).where(
                Notification.id.in_(notification_ids),
                Notification.user_id == user_id,
                Notification.status != NotificationStatus.ARCHIVED,
                Notification.status != NotificationStatus.READ,
            )
        )
        notifications = result.scalars().all()
        for n in notifications:
            n.status = NotificationStatus.READ
            n.is_read = True
            n.read_at = now
        db.commit()
        CacheService.invalidate_key(
            CacheService.build_key(CacheService.NAMESPACE_NOTIFICATION, "unread", str(user_id))
        )
        return len(notifications)

    @staticmethod
    def mark_all_read(
        db: Session,
        user_id: int,
        notification_type: NotificationType | None = None,
    ) -> int:
        now = datetime.now(timezone.utc)
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.status != NotificationStatus.ARCHIVED,
            Notification.status != NotificationStatus.READ,
        )
        if notification_type is not None:
            stmt = stmt.where(Notification.notification_type == notification_type)

        result = db.execute(stmt)
        notifications = result.scalars().all()
        for n in notifications:
            n.status = NotificationStatus.READ
            n.is_read = True
            n.read_at = now
        db.commit()
        CacheService.invalidate_key(
            CacheService.build_key(CacheService.NAMESPACE_NOTIFICATION, "unread", str(user_id))
        )
        return len(notifications)

    @staticmethod
    def update_notification(
        db: Session, notification_id: int, update_data: NotificationUpdate
    ) -> Notification | None:
        notification = NotificationService._validate_notification_exists(db, notification_id)
        if not notification:
            return None
        NotificationService._validate_not_archived(notification)
        data = update_data.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(notification, key, value)
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def archive_notification(db: Session, notification_id: int) -> Notification | None:
        notification = NotificationService._validate_notification_exists(db, notification_id)
        if not notification:
            return None
        if notification.status == NotificationStatus.ARCHIVED:
            return notification
        notification.status = NotificationStatus.ARCHIVED
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def delete_notification(db: Session, notification_id: int) -> Notification | None:
        notification = NotificationService._validate_notification_exists(db, notification_id)
        if not notification:
            return None
        user_id = notification.user_id
        db.delete(notification)
        db.commit()
        CacheService.invalidate_key(
            CacheService.build_key(CacheService.NAMESPACE_NOTIFICATION, "unread", str(user_id))
        )
        return notification

    @staticmethod
    def get_unread_count(db: Session, user_id: int) -> int:
        cache_key = CacheService.build_key(CacheService.NAMESPACE_NOTIFICATION, "unread", str(user_id))
        cached = CacheService.get(cache_key)
        if cached is not None:
            return cached
        count = db.scalar(
            select(sa_func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.status == NotificationStatus.UNREAD,
            )
        )
        result = count or 0
        CacheService.set(cache_key, result, ttl=settings.CACHE_TTL_NOTIFICATION)
        return result

    @staticmethod
    def notify_appointment_created(db: Session, user_id: int, **kwargs) -> Notification:
        return NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=user_id,
                title="Appointment Created",
                message="Your appointment has been scheduled successfully.",
                notification_type=NotificationType.APPOINTMENT,
                priority=NotificationPriority.MEDIUM,
                metadata_json=json.dumps(kwargs) if kwargs else None,
            ),
        )

    @staticmethod
    def notify_appointment_cancelled(db: Session, user_id: int, **kwargs) -> Notification:
        return NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=user_id,
                title="Appointment Cancelled",
                message="Your appointment has been cancelled.",
                notification_type=NotificationType.APPOINTMENT,
                priority=NotificationPriority.HIGH,
                metadata_json=json.dumps(kwargs) if kwargs else None,
            ),
        )

    @staticmethod
    def notify_prescription_created(db: Session, user_id: int, **kwargs) -> Notification:
        return NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=user_id,
                title="Prescription Issued",
                message="A new prescription has been issued for you.",
                notification_type=NotificationType.PRESCRIPTION,
                priority=NotificationPriority.MEDIUM,
                metadata_json=json.dumps(kwargs) if kwargs else None,
            ),
        )

    @staticmethod
    def notify_lab_uploaded(db: Session, user_id: int, **kwargs) -> Notification:
        return NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=user_id,
                title="Lab Report Available",
                message="Your lab report has been uploaded.",
                notification_type=NotificationType.LAB_REPORT,
                priority=NotificationPriority.MEDIUM,
                metadata_json=json.dumps(kwargs) if kwargs else None,
            ),
        )

    @staticmethod
    def notify_record_created(db: Session, user_id: int, **kwargs) -> Notification:
        return NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=user_id,
                title="Medical Record Created",
                message="Your medical record has been created.",
                notification_type=NotificationType.MEDICAL_RECORD,
                priority=NotificationPriority.MEDIUM,
                metadata_json=json.dumps(kwargs) if kwargs else None,
            ),
        )

    @staticmethod
    def notify_ai_alert(db: Session, user_id: int, **kwargs) -> Notification:
        return NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=user_id,
                title="AI Alert",
                message=kwargs.get("message", "An AI-generated alert has been triggered."),
                notification_type=NotificationType.AI,
                priority=NotificationPriority.HIGH,
                metadata_json=json.dumps(kwargs) if kwargs else None,
            ),
        )
