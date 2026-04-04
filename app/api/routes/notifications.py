from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    NotificationMarkAllReadResult,
    NotificationRead,
    NotificationUnreadCountRead,
)
from app.services.notifications import (
    count_unread_notifications,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
async def get_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[Notification]:
    return await list_notifications(
        session,
        current_user.id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )


@router.get("/unread-count", response_model=NotificationUnreadCountRead)
async def get_unread_notifications_count(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> NotificationUnreadCountRead:
    unread_count = await count_unread_notifications(session, current_user.id)
    return NotificationUnreadCountRead(unread_count=unread_count)


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def post_mark_notification_read(
    notification_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Notification:
    return await mark_notification_read(session, notification_id, current_user.id)


@router.post("/read-all", response_model=NotificationMarkAllReadResult)
async def post_mark_all_notifications_read(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> NotificationMarkAllReadResult:
    updated_count = await mark_all_notifications_read(session, current_user.id)
    return NotificationMarkAllReadResult(updated_count=updated_count)
