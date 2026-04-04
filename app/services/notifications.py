from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notifications import NotificationRepository


async def list_notifications(
    session: AsyncSession,
    recipient_id: UUID,
    *,
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
) -> list[Notification]:
    repository = NotificationRepository(session)
    return await repository.list_for_recipient(
        recipient_id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )


async def mark_notification_read(
    session: AsyncSession, notification_id: int, recipient_id: UUID
) -> Notification:
    repository = NotificationRepository(session)
    notification = await repository.get_for_recipient(notification_id, recipient_id)
    if notification is None:
        raise NotFoundError("Notification not found.")
    notification.read = True
    return await repository.save(notification)


async def mark_all_notifications_read(session: AsyncSession, recipient_id: UUID) -> int:
    repository = NotificationRepository(session)
    return await repository.mark_all_read_for_recipient(recipient_id)


async def count_unread_notifications(session: AsyncSession, recipient_id: UUID) -> int:
    repository = NotificationRepository(session)
    return await repository.count_unread_for_recipient(recipient_id)


async def create_notification(
    session: AsyncSession,
    *,
    recipient_id: UUID,
    content: str,
    sender_id: UUID | None = None,
    url: str | None = None,
) -> Notification:
    repository = NotificationRepository(session)
    notification = Notification(
        recipient_id=recipient_id,
        sender_id=sender_id,
        content=content,
        url=url,
        read=False,
    )
    return await repository.create(notification)


def notifications_supported(session: AsyncSession) -> bool:
    return all(hasattr(session, attr) for attr in ("add", "commit", "execute"))


async def create_notification_if_possible(
    session: AsyncSession,
    *,
    recipient_id: UUID | None,
    content: str,
    sender_id: UUID | None = None,
    url: str | None = None,
    skip_sender: bool = True,
) -> Notification | None:
    if recipient_id is None:
        return None
    if skip_sender and sender_id is not None and recipient_id == sender_id:
        return None
    if not notifications_supported(session):
        return None
    return await create_notification(
        session,
        recipient_id=recipient_id,
        content=content,
        sender_id=sender_id,
        url=url,
    )


async def create_notifications_if_possible(
    session: AsyncSession,
    *,
    recipient_ids: list[UUID],
    content: str,
    sender_id: UUID | None = None,
    url: str | None = None,
    skip_sender: bool = True,
) -> int:
    if not recipient_ids:
        return 0
    if not notifications_supported(session):
        return 0

    created_count = 0
    for recipient_id in sorted(set(recipient_ids)):
        created = await create_notification_if_possible(
            session,
            recipient_id=recipient_id,
            content=content,
            sender_id=sender_id,
            url=url,
            skip_sender=skip_sender,
        )
        if created is not None:
            created_count += 1
    return created_count


async def list_active_user_ids(session: AsyncSession) -> list[UUID]:
    if not notifications_supported(session):
        return []
    statement = select(User.id).where(
        User.is_active.is_(True),
        User.is_superuser.is_(False),
    )
    result = await session.execute(statement)
    return list(result.scalars().all())
