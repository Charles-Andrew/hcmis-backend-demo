from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.user import User
from app.schemas.user import UserProfileUpdateRequest, UserRead
from app.services.profile_photo_storage import (
    get_profile_photo_content_by_url,
)
from app.services.users import update_own_profile, upload_own_profile_photo

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


@router.post("/me/photo", response_model=UserRead)
async def upload_my_profile_photo(
    uploaded_file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> User:
    return await upload_own_profile_photo(
        session=session,
        user_id=current_user.id,
        uploaded_file=uploaded_file,
    )


@router.get("/me/photo")
async def read_my_profile_photo(
    current_user: User = Depends(get_current_user),
) -> Response:
    if not current_user.profile_picture_url:
        raise HTTPException(status_code=404, detail="Profile photo not found.")

    try:
        content, content_type = get_profile_photo_content_by_url(
            current_user.profile_picture_url
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Profile photo not found.") from exc

    return Response(content=content, media_type=content_type or "application/octet-stream")
