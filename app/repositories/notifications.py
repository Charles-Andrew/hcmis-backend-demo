from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_recipient(self, recipient_id: int) -> list[Notification]:
        statement = (
            select(Notification)
            .where(Notification.recipient_id == recipient_id)
            .order_by(Notification.read.asc(), Notification.id.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_for_recipient(
        self, notification_id: int, recipient_id: int
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

