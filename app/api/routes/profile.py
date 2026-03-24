from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.user import User
from app.schemas.user import UserProfileUpdateRequest, UserRead
from app.services.users import update_own_profile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=UserRead)
async def get_my_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
async def patch_my_profile(
    payload: UserProfileUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> User:
    return await update_own_profile(session, current_user.id, payload)

