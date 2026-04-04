from uuid import UUID

from datetime import UTC, date, datetime, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_log import AppLog


class AppLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_date(
        self, selected_date: date, user_id: UUID | None = None
    ) -> list[AppLog]:
        start = datetime.combine(selected_date, time.min, tzinfo=UTC)
        end = datetime.combine(selected_date, time.max, tzinfo=UTC)

        statement = select(AppLog).where(
            AppLog.created_at >= start,
            AppLog.created_at <= end,
        )
        if user_id is not None:
            statement = statement.where(AppLog.user_id == user_id)

        statement = statement.order_by(AppLog.id.desc())
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create(self, log: AppLog) -> AppLog:
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log
