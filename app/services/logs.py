from uuid import UUID

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_log import AppLog
from app.repositories.app_logs import AppLogRepository


async def list_app_logs(
    session: AsyncSession, selected_date: date, user_id: UUID | None = None
) -> list[AppLog]:
    repository = AppLogRepository(session)
    return await repository.list_for_date(selected_date, user_id=user_id)


async def create_app_log(
    session: AsyncSession, user_id: UUID, details: str
) -> AppLog:
    repository = AppLogRepository(session)
    log = AppLog(user_id=user_id, details=details)
    return await repository.create(log)

