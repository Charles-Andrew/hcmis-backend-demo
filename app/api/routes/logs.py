from uuid import UUID

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_staff_user, get_db_session
from app.models.user import User
from app.schemas.app_log import AppLogPageRead
from app.services.logs import list_app_logs_page

router = APIRouter(prefix="/app-logs", tags=["app-logs"])


@router.get("", response_model=AppLogPageRead)
async def get_app_logs(
    selected_date: date | None = Query(default=None),
    user_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> AppLogPageRead:
    return await list_app_logs_page(
        session,
        selected_date=selected_date,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )
