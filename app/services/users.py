from uuid import UUID

from datetime import UTC, datetime, timedelta

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError
from app.core.exceptions import NotFoundError
from app.core.security import generate_temporary_password, hash_password
from app.models.user import User
from app.repositories.departments import DepartmentRepository
from app.repositories.users import UserRepository
from app.services.notifications import create_notification_if_possible
from app.services.profile_photo_storage import (
    delete_profile_photo_by_url,
    save_profile_photo,
)
from app.schemas.user import UserCreateRequest
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
    exclude_hr: bool = False,
    exclude_user_id: UUID | None = None,
) -> list[User]:
    repository = UserRepository(session)
    return await repository.list(
        query=query,
        department_id=department_id,
        active_only=active_only,
        include_superusers=include_superusers,
        exclude_hr=exclude_hr,
        exclude_user_id=exclude_user_id,
    )


async def create_user(session: AsyncSession, payload: UserCreateRequest) -> User:
    user_repository = UserRepository(session)
    department_repository = DepartmentRepository(session)
    email = payload.email.lower()

    existing_user = await user_repository.get_by_email(email)
    if existing_user is not None:
        raise ConflictError("Email is already registered.")

    if payload.employee_number:
        existing_employee = await user_repository.get_by_employee_number(
            payload.employee_number
        )
        if existing_employee is not None:
            raise ConflictError("Employee number already exists.")

    if payload.biometric_uid is not None:
        existing_biometric = await user_repository.get_by_biometric_uid(
            payload.biometric_uid
        )
        if existing_biometric is not None:
            raise ConflictError("Biometric UID is already assigned to another user.")

    if payload.department_id is not None:
        department = await department_repository.get_by_id(payload.department_id)
        if department is None:
            raise NotFoundError("Department not found.")

    password_hash = hash_password(payload.password)
    user = User(
        email=email,
        password_hash=password_hash,
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
        gender=payload.gender,
        education=payload.education,
        civil_status=payload.civil_status,
        religion=payload.religion,
        rank=payload.rank,
        employee_number=payload.employee_number,
        biometric_uid=payload.biometric_uid,
        role=payload.role,
        department_id=payload.department_id,
        phone_number=payload.phone_number,
        address=payload.address,
        date_of_birth=payload.date_of_birth,
        date_of_hiring=payload.date_of_hiring,
        resignation_date=payload.resignation_date,
        profile_picture_url=payload.profile_picture_url,
        can_modify_shift=payload.can_modify_shift,
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
    )
    try:
        return await user_repository.create(user)
    except IntegrityError as exc:
        raise ConflictError("User already exists.") from exc


async def get_user(session: AsyncSession, user_id: UUID) -> User:
    repository = UserRepository(session)
    user = await repository.get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


async def update_user(
    session: AsyncSession, user_id: UUID, payload: UserUpdateRequest
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


async def toggle_user_status(session: AsyncSession, user_id: UUID) -> User:
    user_repository = UserRepository(session)
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")

    user.is_active = not user.is_active
    user = await user_repository.save(user)
    status_text = "activated" if user.is_active else "deactivated"
    await create_notification_if_possible(
        session,
        recipient_id=user.id,
        content=f"Your account was {status_text}.",
        url="/profile",
    )
    return user


async def update_own_profile(
    session: AsyncSession, user_id: UUID, payload: UserProfileUpdateRequest
) -> User:
    user_repository = UserRepository(session)
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")

    data = payload.model_dump(exclude_unset=True)
    for field_name, value in data.items():
        setattr(user, field_name, value)

    return await user_repository.save(user)


async def upload_own_profile_photo(
    session: AsyncSession,
    user_id: UUID,
    uploaded_file: UploadFile,
) -> User:
    user_repository = UserRepository(session)
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")

    previous_photo_url = user.profile_picture_url
    stored_photo = await save_profile_photo(
        user_id=user_id,
        uploaded_file=uploaded_file,
    )
    user.profile_picture_url = stored_photo.url

    try:
        saved_user = await user_repository.save(user)
    except Exception:
        delete_profile_photo_by_url(stored_photo.url)
        raise

    if previous_photo_url and previous_photo_url != stored_photo.url:
        delete_profile_photo_by_url(previous_photo_url)

    return saved_user


async def update_user_biometric_uid(
    session: AsyncSession, user_id: UUID, payload: UserBiometricUpdateRequest
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


async def reset_user_password(
    session: AsyncSession,
    user_id: UUID,
) -> tuple[User, str]:
    user_repository = UserRepository(session)
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")

    temporary_password = generate_temporary_password()
    user.password_hash = hash_password(temporary_password)
    user.must_change_password = True
    user.temporary_password_expires_at = datetime.now(UTC) + timedelta(hours=24)
    saved_user = await user_repository.save(user)
    await create_notification_if_possible(
        session,
        recipient_id=saved_user.id,
        content="Your password was reset by HR. Please change it on your next login.",
        url="/change-password",
    )
    return saved_user, temporary_password
