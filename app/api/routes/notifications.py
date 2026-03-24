from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationRead
from app.services.notifications import list_notifications, mark_notification_read

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
async def get_notifications(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[Notification]:
    return await list_notifications(session, current_user.id)


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def post_mark_notification_read(
    notification_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Notification:
    return await mark_notification_read(session, notification_id, current_user.id)
