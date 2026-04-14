from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, require_staff_user
from app.core.capabilities import is_staff_user
from app.models.user import User
from app.schemas.training import (
    TrainingCreateRequest,
    TrainingParticipantsReplaceRequest,
    TrainingRead,
    TrainingStatusUpdateRequest,
)
from app.services.trainings import (
    add_training_participant_attachment,
    create_training,
    get_training,
    list_completed_trainings_for_user,
    list_trainings,
    replace_training_participants,
    remove_training_participant_attachment,
    update_training_status,
)

router = APIRouter(prefix="/trainings", tags=["trainings"])


@router.get("", response_model=list[TrainingRead])
async def get_trainings(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[TrainingRead]:
    return await list_trainings(session)


@router.post("", response_model=TrainingRead, status_code=status.HTTP_201_CREATED)
async def post_training(
    payload: TrainingCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> TrainingRead:
    return await create_training(
        session,
        payload,
        created_by_id=current_user.id,
    )


@router.get("/{training_id}", response_model=TrainingRead)
async def get_training_by_id(
    training_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> TrainingRead:
    return await get_training(session, training_id)


@router.put("/{training_id}/participants", response_model=TrainingRead)
async def put_training_participants(
    training_id: int,
    payload: TrainingParticipantsReplaceRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> TrainingRead:
    return await replace_training_participants(session, training_id, payload)


@router.patch("/{training_id}/status", response_model=TrainingRead)
async def patch_training_status(
    training_id: int,
    payload: TrainingStatusUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> TrainingRead:
    return await update_training_status(session, training_id, payload)


@router.post(
    "/{training_id}/participants/{participant_id}/attachments",
    response_model=TrainingRead,
)
async def post_training_participant_attachment(
    training_id: int,
    participant_id: int,
    uploaded_file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> TrainingRead:
    return await add_training_participant_attachment(
        session,
        training_id=training_id,
        participant_id=participant_id,
        uploaded_file=uploaded_file,
    )


@router.delete(
    "/{training_id}/participants/{participant_id}/attachments/{attachment_id}",
    response_model=TrainingRead,
)
async def delete_training_participant_attachment(
    training_id: int,
    participant_id: int,
    attachment_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> TrainingRead:
    return await remove_training_participant_attachment(
        session,
        training_id=training_id,
        participant_id=participant_id,
        attachment_id=attachment_id,
    )


@router.get("/completed/me", response_model=list[TrainingRead])
async def get_my_completed_trainings(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[TrainingRead]:
    return await list_completed_trainings_for_user(
        session,
        target_user_id=current_user.id,
        current_user_id=current_user.id,
        is_staff=is_staff_user(current_user),
    )


@router.get("/completed/users/{user_id}", response_model=list[TrainingRead])
async def get_user_completed_trainings(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[TrainingRead]:
    return await list_completed_trainings_for_user(
        session,
        target_user_id=user_id,
        current_user_id=current_user.id,
        is_staff=True,
    )
