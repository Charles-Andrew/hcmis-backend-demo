from uuid import UUID

from datetime import UTC, date, datetime, time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_log import AppLog


class AppLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _build_filtered_statement(
        self,
        selected_date: date | None,
        user_id: UUID | None,
    ):
        statement = select(AppLog)
        if selected_date is not None:
            start = datetime.combine(selected_date, time.min, tzinfo=UTC)
            end = datetime.combine(selected_date, time.max, tzinfo=UTC)
            statement = statement.where(
                AppLog.created_at >= start,
                AppLog.created_at <= end,
            )
        if user_id is not None:
            statement = statement.where(AppLog.user_id == user_id)
        return statement

    async def list_for_date(
        self, selected_date: date | None, user_id: UUID | None = None
    ) -> list[AppLog]:
        statement = self._build_filtered_statement(selected_date, user_id)
        statement = statement.order_by(AppLog.id.desc())
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_page_for_date(
        self,
        selected_date: date | None,
        user_id: UUID | None,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[AppLog], int]:
        filtered_statement = self._build_filtered_statement(selected_date, user_id)

        count_statement = select(func.count()).select_from(filtered_statement.subquery())
        total = (await self.session.execute(count_statement)).scalar_one()

        offset = (page - 1) * page_size
        statement = filtered_statement.order_by(AppLog.id.desc()).offset(offset).limit(page_size)
        result = await self.session.execute(statement)
        return list(result.scalars().all()), total

    async def create(self, log: AppLog) -> AppLog:
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log
