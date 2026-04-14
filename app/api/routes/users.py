from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_staff_user, get_db_session
from app.core.capabilities import normalize_role
from app.models.user import User
from app.schemas.auth import UserPasswordResetResponse
from app.schemas.user import (
    UserCreateRequest,
    UserBiometricUpdateRequest,
    UserEmploymentMovementRead,
    UserRead,
    UserUpdateRequest,
)
from app.services.users import (
    create_user,
    get_user,
    list_user_employment_movements,
    list_users,
    reset_user_password,
    toggle_user_status,
    update_user,
    update_user_biometric_uid,
)

router = APIRouter(prefix="/users", tags=["users"])


def ensure_hr_can_modify_employment_fields(
    *,
    current_user: User,
    fields_set: set[str],
) -> None:
    requested_fields = {"employee_type", "employment_status"}
    if not requested_fields.intersection(fields_set):
        return
    if normalize_role(current_user.role) == "HR":
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only HR can modify employee type and employment status.",
    )


@router.get("", response_model=list[UserRead])
async def get_users(
    q: str | None = Query(default=None, alias="q"),
    department_id: int | None = Query(default=None),
    active_only: bool | None = Query(default=None),
    include_superusers: bool = Query(default=False),
    exclude_hr: bool = Query(default=False),
    exclude_self: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[User]:
    return await list_users(
        session,
        query=q,
        department_id=department_id,
        active_only=active_only,
        include_superusers=include_superusers,
        exclude_hr=exclude_hr,
        exclude_user_id=current_user.id if exclude_self else None,
    )


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def post_user(
    payload: UserCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> User:
    ensure_hr_can_modify_employment_fields(
        current_user=current_user,
        fields_set=payload.model_fields_set,
    )
    try:
        return await create_user(session, payload, actor_user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{user_id}", response_model=UserRead)
async def get_user_by_id(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> User:
    return await get_user(session, user_id)


@router.get("/{user_id}/employment-movements", response_model=list[UserEmploymentMovementRead])
async def get_user_employment_movements(
    user_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[UserEmploymentMovementRead]:
    return await list_user_employment_movements(session, user_id, limit=limit)


@router.patch("/{user_id}", response_model=UserRead)
async def patch_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> User:
    ensure_hr_can_modify_employment_fields(
        current_user=current_user,
        fields_set=payload.model_fields_set,
    )
    return await update_user(session, user_id, payload, actor_user_id=current_user.id)


@router.post("/{user_id}/toggle-status", response_model=UserRead)
async def post_toggle_user_status(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> User:
    return await toggle_user_status(session, user_id)


@router.patch("/{user_id}/biometric", response_model=UserRead)
async def patch_user_biometric_uid(
    user_id: UUID,
    payload: UserBiometricUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> User:
    return await update_user_biometric_uid(session, user_id, payload)


@router.post("/{user_id}/reset-password", response_model=UserPasswordResetResponse)
async def post_reset_user_password(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> UserPasswordResetResponse:
    _, temporary_password = await reset_user_password(session, user_id)
    return UserPasswordResetResponse(temporary_password=temporary_password)
