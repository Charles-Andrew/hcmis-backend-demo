from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.core.security import create_access_token, hash_password, verify_password
from app.models.department import Department
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.auth import AuthLoginRequest, AuthRegisterRequest, AuthResponse
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: AuthRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> UserRead:
    repository = UserRepository(session)
    existing_user = await repository.get_by_email(payload.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered.",
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
    payload: AuthLoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    repository = UserRepository(session)
    user = await repository.get_by_email(payload.email.lower())
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    access_token = create_access_token(subject=str(user.id))
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
