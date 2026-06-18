from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.enums import UserRole, NotificationType, NotificationPriority, NotificationStatus
from app.schemas.notification import (
    NotificationCreate,
    NotificationUpdate,
    NotificationResponse,
    NotificationListResponse,
    NotificationFilters,
    NotificationMarkReadRequest,
    NotificationMarkAllReadRequest,
)
from app.services.notification_service import NotificationService, NotificationValidationError
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post(
    "",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a notification",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Admin access required"},
        status.HTTP_404_NOT_FOUND: {"description": "User not found"},
        status.HTTP_409_CONFLICT: {"description": "Duplicate notification"},
    },
)
def create_notification(
    notification_data: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    try:
        return NotificationService.create_notification(db, notification_data)
    except NotificationValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List notifications",
    description="Returns notifications filtered by role. Admins see all. Others see only their own.",
)
def list_notifications(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    sort_by: str = Query(default="created_at", pattern="^(created_at|priority|notification_type|status)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    notification_type: NotificationType | None = Query(default=None),
    priority: NotificationPriority | None = Query(default=None),
    status: NotificationStatus | None = Query(default=None),
    date_from: str | None = Query(default=None, description="ISO datetime filter start"),
    date_to: str | None = Query(default=None, description="ISO datetime filter end"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime as dt

    filter_obj = NotificationFilters(
        notification_type=notification_type,
        priority=priority,
        status=status,
        date_from=dt.fromisoformat(date_from) if date_from else None,
        date_to=dt.fromisoformat(date_to) if date_to else None,
    )

    notifications, total = NotificationService.list_notifications(
        db,
        user_id=current_user.id,
        user_role=current_user.role,
        filters=filter_obj,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return NotificationListResponse(
        items=notifications,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/unread-count",
    response_model=dict,
    summary="Get unread notification count",
)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = NotificationService.get_unread_count(db, current_user.id)
    return {"unread_count": count}


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get a notification by ID",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Notification not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
    },
)
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = NotificationService.get_notification(db, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if current_user.role != UserRole.ADMIN and notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return notification


@router.patch(
    "/read-all",
    response_model=dict,
    summary="Mark all notifications as read",
)
def mark_all_read(
    request: NotificationMarkAllReadRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification_type = request.notification_type if request else None
    count = NotificationService.mark_all_read(db, current_user.id, notification_type)
    return {"marked_read": count}


@router.patch(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Update a notification (title/message)",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Notification not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
        status.HTTP_400_BAD_REQUEST: {"description": "Archived notifications cannot be modified"},
    },
)
def update_notification(
    notification_id: int,
    update_data: NotificationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    notification = NotificationService.get_notification(db, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    try:
        updated = NotificationService.update_notification(db, notification_id, update_data)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        return updated
    except NotificationValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a notification as read",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Notification not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
        status.HTTP_400_BAD_REQUEST: {"description": "Archived notifications cannot be modified"},
    },
)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = NotificationService.get_notification(db, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if current_user.role != UserRole.ADMIN and notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        result = NotificationService.mark_as_read(db, notification_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        return result
    except NotificationValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.patch(
    "/{notification_id}/archive",
    response_model=NotificationResponse,
    summary="Archive a notification",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Notification not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
    },
)
def archive_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = NotificationService.get_notification(db, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if current_user.role != UserRole.ADMIN and notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    result = NotificationService.archive_notification(db, notification_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return result


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a notification",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Notification not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Admin access required"},
    },
)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    notification = NotificationService.get_notification(db, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    NotificationService.delete_notification(db, notification_id)
