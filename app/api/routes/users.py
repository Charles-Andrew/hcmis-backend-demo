from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_staff_user, get_db_session
from app.models.user import User
from app.schemas.user import (
    UserBiometricUpdateRequest,
    UserRead,
    UserUpdateRequest,
)
from app.services.users import (
    get_user,
    list_users,
    toggle_user_status,
    update_user,
    update_user_biometric_uid,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
async def get_users(
    q: str | None = Query(default=None, alias="q"),
    department_id: int | None = Query(default=None),
    active_only: bool | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[User]:
    return await list_users(
        session,
        query=q,
        department_id=department_id,
        active_only=active_only,
    )


@router.get("/{user_id}", response_model=UserRead)
async def get_user_by_id(
    user_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> User:
    return await get_user(session, user_id)


@router.patch("/{user_id}", response_model=UserRead)
async def patch_user(
    user_id: int,
    payload: UserUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> User:
    return await update_user(session, user_id, payload)


@router.post("/{user_id}/toggle-status", response_model=UserRead)
async def post_toggle_user_status(
    user_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> User:
    return await toggle_user_status(session, user_id)


@router.patch("/{user_id}/biometric", response_model=UserRead)
async def patch_user_biometric_uid(
    user_id: int,
    payload: UserBiometricUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> User:
    return await update_user_biometric_uid(session, user_id, payload)
