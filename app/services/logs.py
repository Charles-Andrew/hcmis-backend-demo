from uuid import UUID

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_log import AppLog
from app.repositories.app_logs import AppLogRepository
from app.schemas.app_log import AppLogPageRead, AppLogRead


async def list_app_logs(
    session: AsyncSession,
    selected_date: date | None = None,
    user_id: UUID | None = None,
) -> list[AppLog]:
    repository = AppLogRepository(session)
    return await repository.list_for_date(selected_date, user_id=user_id)


async def list_app_logs_page(
    session: AsyncSession,
    *,
    selected_date: date | None = None,
    user_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> AppLogPageRead:
    repository = AppLogRepository(session)
    items, total = await repository.list_page_for_date(
        selected_date,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return AppLogPageRead(
        items=[AppLogRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


async def create_app_log(
    session: AsyncSession, user_id: UUID, details: str
) -> AppLog:
    repository = AppLogRepository(session)
    log = AppLog(user_id=user_id, details=details)
    return await repository.create(log)
