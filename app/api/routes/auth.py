import logging
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.core.capabilities import resolve_user_capabilities
from app.core.security import create_access_token, hash_password, verify_password
from app.models.department import Department
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.auth import (
    AuthChangePasswordRequest,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResponse,
)
from app.schemas.user import UserRead, UserWithCapabilitiesRead

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _normalize_username(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized == "":
        return None
    return normalized


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: AuthRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> UserRead:
    repository = UserRepository(session)
    username = _normalize_username(payload.username)
    existing_user = await repository.get_by_email(payload.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered.",
        )
    if username is not None:
        existing_username = await repository.get_by_username(username)
        if existing_username is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username is already registered.",
            )

    department_id = None
    if payload.department_name and payload.department_code:
        department_result = await session.execute(
            select(Department).where(
                Department.code == payload.department_code,
                Department.name == payload.department_name,
            )
        )
        department = department_result.scalar_one_or_none()
        if department is None:
            department = Department(
                name=payload.department_name,
                code=payload.department_code,
            )
            session.add(department)
            await session.flush()
        department_id = department.id

    try:
        password_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    user = User(
        email=payload.email.lower(),
        username=username,
        password_hash=password_hash,
        first_name=payload.first_name,
        last_name=payload.last_name,
        employee_number=payload.employee_number,
        role=payload.role,
        department_id=department_id,
        can_modify_shift=False,
        is_active=True,
        is_superuser=False,
    )
    created_user = await repository.create(user)
    return UserRead.model_validate(created_user)


@router.post("/login", response_model=AuthResponse)
async def login(
    request: Request,
    payload: AuthLoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    request_id = request.headers.get("x-request-id", "")
    started = time.perf_counter()
    logger.info("auth_login_start request_id=%s", request_id)

    repository = UserRepository(session)
    identifier = (payload.identifier or (str(payload.email) if payload.email else "")).strip()
    user = await repository.get_by_login_identifier(identifier)
    if user is None or not verify_password(payload.password, user.password_hash):
        logger.warning(
            "auth_login_invalid_credentials request_id=%s duration_ms=%d",
            request_id,
            int((time.perf_counter() - started) * 1000),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password.",
        )
    if (
        user.must_change_password
        and user.temporary_password_expires_at is not None
        and user.temporary_password_expires_at < datetime.now(UTC)
    ):
        logger.warning(
            "auth_login_temporary_password_expired request_id=%s user_id=%s duration_ms=%d",
            request_id,
            str(user.id),
            int((time.perf_counter() - started) * 1000),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Temporary password has expired. Please contact HR for reset.",
        )

    access_token = create_access_token(subject=str(user.id))
    validated_user = UserWithCapabilitiesRead.model_validate(user).model_copy(
        update={"capabilities": resolve_user_capabilities(user)}
    )
    logger.info(
        "auth_login_success request_id=%s user_id=%s duration_ms=%d",
        request_id,
        str(user.id),
        int((time.perf_counter() - started) * 1000),
    )
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=validated_user,
    )


@router.get("/me", response_model=UserWithCapabilitiesRead)
async def me(current_user: User = Depends(get_current_user)) -> UserWithCapabilitiesRead:
    return UserWithCapabilitiesRead.model_validate(current_user).model_copy(
        update={"capabilities": resolve_user_capabilities(current_user)}
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: AuthChangePasswordRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    if current_user.must_change_password:
        if verify_password(payload.new_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password.",
            )
    else:
        if not payload.current_password or not verify_password(
            payload.current_password, current_user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )
        if payload.current_password == payload.new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password.",
            )

    try:
        current_user.password_hash = hash_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    current_user.must_change_password = False
    current_user.temporary_password_expires_at = None
    session.add(current_user)
    await session.commit()
