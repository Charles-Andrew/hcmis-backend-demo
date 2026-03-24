from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.notification import Notification
from app.repositories.notifications import NotificationRepository


async def list_notifications(session: AsyncSession, recipient_id: int) -> list[Notification]:
    repository = NotificationRepository(session)
    return await repository.list_for_recipient(recipient_id)


async def mark_notification_read(
    session: AsyncSession, notification_id: int, recipient_id: int
) -> Notification:
    repository = NotificationRepository(session)
    notification = await repository.get_for_recipient(notification_id, recipient_id)
    if notification is None:
        raise NotFoundError("Notification not found.")
    notification.read = True
    return await repository.save(notification)

