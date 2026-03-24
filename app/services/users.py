from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.departments import DepartmentRepository
from app.repositories.users import UserRepository
from app.schemas.user import (
    UserBiometricUpdateRequest,
    UserProfileUpdateRequest,
    UserUpdateRequest,
)


async def list_users(
    session: AsyncSession,
    query: str | None = None,
    department_id: int | None = None,
    active_only: bool | None = None,
    include_superusers: bool = False,
) -> list[User]:
    repository = UserRepository(session)
    return await repository.list(
        query=query,
        department_id=department_id,
        active_only=active_only,
        include_superusers=include_superusers,
    )


async def get_user(session: AsyncSession, user_id: int) -> User:
    repository = UserRepository(session)
    user = await repository.get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


async def update_user(
    session: AsyncSession, user_id: int, payload: UserUpdateRequest
) -> User:
    user_repository = UserRepository(session)
    department_repository = DepartmentRepository(session)
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")

    data = payload.model_dump(exclude_unset=True)
    department_id = data.pop("department_id", None) if "department_id" in data else None
    if "department_id" in payload.model_fields_set:
        if department_id is None:
            user.department_id = None
        else:
            department = await department_repository.get_by_id(department_id)
            if department is None:
                raise NotFoundError("Department not found.")
            user.department_id = department.id

    for field_name, value in data.items():
        setattr(user, field_name, value)

    return await user_repository.save(user)


async def toggle_user_status(session: AsyncSession, user_id: int) -> User:
    user_repository = UserRepository(session)
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")

    user.is_active = not user.is_active
    return await user_repository.save(user)


async def update_own_profile(
    session: AsyncSession, user_id: int, payload: UserProfileUpdateRequest
) -> User:
    user_repository = UserRepository(session)
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")

    data = payload.model_dump(exclude_unset=True)
    for field_name, value in data.items():
        setattr(user, field_name, value)

    return await user_repository.save(user)


async def update_user_biometric_uid(
    session: AsyncSession, user_id: int, payload: UserBiometricUpdateRequest
) -> User:
    user_repository = UserRepository(session)
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")

    if payload.biometric_uid is None:
        user.biometric_uid = None
        return await user_repository.save(user)

    users = await user_repository.list(include_superusers=True)
    for other_user in users:
        if other_user.id != user_id and other_user.biometric_uid == payload.biometric_uid:
            raise NotFoundError("Biometric UID is already assigned to another user.")

    user.biometric_uid = payload.biometric_uid
    return await user_repository.save(user)
