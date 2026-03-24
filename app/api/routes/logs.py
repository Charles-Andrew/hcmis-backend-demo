from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_staff_user, get_db_session
from app.models.app_log import AppLog
from app.models.user import User
from app.schemas.app_log import AppLogRead
from app.services.logs import list_app_logs

router = APIRouter(prefix="/app-logs", tags=["app-logs"])


@router.get("", response_model=list[AppLogRead])
async def get_app_logs(
    selected_date: date | None = Query(default=None),
    user_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[AppLog]:
    return await list_app_logs(
        session,
        selected_date=selected_date or date.today(),
        user_id=user_id,
    )
