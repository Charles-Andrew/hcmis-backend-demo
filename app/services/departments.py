from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.department import Department
from app.repositories.departments import DepartmentRepository
from app.schemas.department import DepartmentCreateRequest, DepartmentUpdateRequest


async def list_departments(session: AsyncSession) -> list[Department]:
    repository = DepartmentRepository(session)
    return await repository.list()


async def create_department(
    session: AsyncSession, payload: DepartmentCreateRequest
) -> Department:
    repository = DepartmentRepository(session)
    if await repository.get_by_name(payload.name):
        raise ConflictError("Department name already exists.")
    if await repository.get_by_code(payload.code):
        raise ConflictError("Department code already exists.")

    department = Department(
        name=payload.name,
        code=payload.code,
        is_active=payload.is_active,
    )
    return await repository.create(department)


async def update_department(
    session: AsyncSession, department_id: int, payload: DepartmentUpdateRequest
) -> Department:
    repository = DepartmentRepository(session)
    department = await repository.get_by_id(department_id)
    if department is None:
        raise NotFoundError("Department not found.")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        existing = await repository.get_by_name(data["name"])
        if existing is not None and existing.id != department.id:
            raise ConflictError("Department name already exists.")
        department.name = data["name"]
    if "code" in data and data["code"] is not None:
        existing = await repository.get_by_code(data["code"])
        if existing is not None and existing.id != department.id:
            raise ConflictError("Department code already exists.")
        department.code = data["code"]
    if "is_active" in data:
        department.is_active = data["is_active"]

    return await repository.save(department)


async def delete_department(session: AsyncSession, department_id: int) -> str:
    repository = DepartmentRepository(session)
    department = await repository.get_by_id(department_id)
    if department is None:
        raise NotFoundError("Department not found.")

    department_name = department.name
    try:
        await repository.delete(department)
    except IntegrityError as exc:
        raise ConflictError("Department cannot be deleted while it is in use.") from exc
    return department_name

