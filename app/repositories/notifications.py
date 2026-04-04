from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_recipient(
        self,
        recipient_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[Notification]:
        statement = (
            select(Notification)
            .where(Notification.recipient_id == recipient_id)
            .order_by(Notification.read.asc(), Notification.id.desc())
            .offset(offset)
            .limit(limit)
        )
        if unread_only:
            statement = statement.where(Notification.read.is_(False))
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_for_recipient(
        self, notification_id: int, recipient_id: UUID
    ) -> Notification | None:
        statement = select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_id == recipient_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def save(self, notification: Notification) -> Notification:
        await self.session.commit()
        await self.session.refresh(notification)
        return notification

    async def create(self, notification: Notification) -> Notification:
        self.session.add(notification)
        await self.session.commit()
        await self.session.refresh(notification)
        return notification

    async def mark_all_read_for_recipient(self, recipient_id: UUID) -> int:
        unread_count = await self.count_unread_for_recipient(recipient_id)
        if unread_count == 0:
            return 0

        statement = (
            update(Notification)
            .where(Notification.recipient_id == recipient_id, Notification.read.is_(False))
            .values(read=True, updated_at=utc_now())
        )
        await self.session.execute(statement)
        await self.session.commit()
        return unread_count

    async def count_unread_for_recipient(self, recipient_id: UUID) -> int:
        statement = select(func.count()).select_from(Notification).where(
            Notification.recipient_id == recipient_id,
            Notification.read.is_(False),
        )
        result = await self.session.execute(statement)
        return int(result.scalar() or 0)
