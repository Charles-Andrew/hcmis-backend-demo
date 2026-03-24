from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, require_staff_user
from app.models.department import Department
from app.models.user import User
from app.schemas.department import (
    DepartmentCreateRequest,
    DepartmentRead,
    DepartmentUpdateRequest,
)
from app.services.departments import (
    create_department,
    delete_department,
    list_departments,
    update_department,
)

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentRead])
async def get_departments(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[Department]:
    return await list_departments(session)


@router.post("", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
async def post_department(
    payload: DepartmentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Department:
    return await create_department(session, payload)


@router.patch("/{department_id}", response_model=DepartmentRead)
async def patch_department(
    department_id: int,
    payload: DepartmentUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Department:
    return await update_department(session, department_id, payload)


@router.delete("/{department_id}", response_model=str)
async def remove_department(
    department_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> str:
    return await delete_department(session, department_id)
