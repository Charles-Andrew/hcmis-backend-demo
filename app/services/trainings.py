from __future__ import annotations

from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models.training import Training, TrainingParticipant, TrainingParticipantAttachment
from app.models.user import User
from app.schemas.training import (
    TrainingCreateRequest,
    TrainingParticipantCreateRequest,
    TrainingParticipantRead,
    TrainingParticipantsReplaceRequest,
    TrainingRead,
    TrainingStatusUpdateRequest,
)
from app.services.training_attachments_storage import (
    delete_training_attachment_file,
    save_uploaded_training_attachment,
)


def _user_display_name(user: User | None) -> str:
    if user is None:
        return "Unknown User"
    full_name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
    return full_name or user.email


def _to_training_read(item: Training) -> TrainingRead:
    participants = sorted(item.participants, key=lambda participant: participant.created_at)
    return TrainingRead(
        id=item.id,
        title=item.title,
        description=item.description,
        training_date=item.training_date,
        status=item.status,  # type: ignore[arg-type]
        created_by_id=item.created_by_id,
        participants=[
            TrainingParticipantRead(
                id=participant.id,
                user_id=participant.user_id,
                user_name=_user_display_name(participant.user),
                attachments=list(participant.attachments),
            )
            for participant in participants
        ],
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _trainings_with_related_query():
    return select(Training).options(
        selectinload(Training.participants)
        .selectinload(TrainingParticipant.user),
        selectinload(Training.participants)
        .selectinload(TrainingParticipant.attachments),
    )


async def _validate_participants(
    session: AsyncSession, participants: list[TrainingParticipantCreateRequest]
) -> None:
    participant_user_ids = [participant.user_id for participant in participants]
    if len(participant_user_ids) != len(set(participant_user_ids)):
        raise ConflictError("Participants must be unique per training.")

    requested_user_ids = sorted({participant.user_id for participant in participants})
    existing_user_ids = set()
    if requested_user_ids:
        user_result = await session.execute(select(User.id).where(User.id.in_(requested_user_ids)))
        existing_user_ids = set(user_result.scalars().all())

    missing = [user_id for user_id in requested_user_ids if user_id not in existing_user_ids]
    if missing:
        raise NotFoundError(f"User not found: {missing[0]}")


async def list_trainings(session: AsyncSession) -> list[TrainingRead]:
    result = await session.execute(
        _trainings_with_related_query().order_by(Training.updated_at.desc(), Training.id.desc())
    )
    items = list(result.scalars().unique().all())
    return [_to_training_read(item) for item in items]


async def create_training(
    session: AsyncSession,
    payload: TrainingCreateRequest,
    *,
    created_by_id: UUID,
) -> TrainingRead:
    await _validate_participants(session, payload.participants)

    item = Training(
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        training_date=payload.training_date,
        status="pending",
        created_by_id=created_by_id,
    )
    session.add(item)
    await session.flush()

    for participant_payload in payload.participants:
        participant = TrainingParticipant(
            training_id=item.id,
            user_id=participant_payload.user_id,
        )
        session.add(participant)

    await session.commit()
    return await get_training(session, item.id)


async def get_training(session: AsyncSession, training_id: int) -> TrainingRead:
    result = await session.execute(
        _trainings_with_related_query().where(Training.id == training_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFoundError("Training not found.")
    return _to_training_read(item)


async def update_training_status(
    session: AsyncSession,
    training_id: int,
    payload: TrainingStatusUpdateRequest,
) -> TrainingRead:
    result = await session.execute(select(Training).where(Training.id == training_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFoundError("Training not found.")

    item.status = payload.status
    await session.commit()
    return await get_training(session, training_id)


async def replace_training_participants(
    session: AsyncSession,
    training_id: int,
    payload: TrainingParticipantsReplaceRequest,
) -> TrainingRead:
    await _validate_participants(session, payload.participants)
    result = await session.execute(
        _trainings_with_related_query().where(Training.id == training_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFoundError("Training not found.")

    keys_to_delete: list[str] = []
    for existing_participant in item.participants:
        for attachment in existing_participant.attachments:
            if attachment.storage_key:
                keys_to_delete.append(attachment.storage_key)

    for existing_participant in list(item.participants):
        await session.delete(existing_participant)
    await session.flush()

    for participant_payload in payload.participants:
        participant = TrainingParticipant(
            training_id=item.id,
            user_id=participant_payload.user_id,
        )
        session.add(participant)

    await session.commit()
    for storage_key in keys_to_delete:
        delete_training_attachment_file(storage_key)
    return await get_training(session, training_id)


async def add_training_participant_attachment(
    session: AsyncSession,
    training_id: int,
    participant_id: int,
    uploaded_file: UploadFile,
) -> TrainingRead:
    result = await session.execute(
        _trainings_with_related_query().where(Training.id == training_id)
    )
    training = result.scalar_one_or_none()
    if training is None:
        raise NotFoundError("Training not found.")

    participant = next(
        (item for item in training.participants if item.id == participant_id),
        None,
    )
    if participant is None:
        raise NotFoundError("Participant not found.")

    stored = await save_uploaded_training_attachment(
        user_id=participant.user_id,
        uploaded_file=uploaded_file,
    )
    attachment = TrainingParticipantAttachment(
        participant_id=participant.id,
        storage_key=stored.storage_key,
        file_name=stored.original_filename,
        file_size=stored.size_bytes,
        content_type=stored.content_type,
    )
    session.add(attachment)
    await session.commit()
    return await get_training(session, training_id)


async def remove_training_participant_attachment(
    session: AsyncSession,
    training_id: int,
    participant_id: int,
    attachment_id: int,
) -> TrainingRead:
    result = await session.execute(
        _trainings_with_related_query().where(Training.id == training_id)
    )
    training = result.scalar_one_or_none()
    if training is None:
        raise NotFoundError("Training not found.")

    participant = next(
        (item for item in training.participants if item.id == participant_id),
        None,
    )
    if participant is None:
        raise NotFoundError("Participant not found.")

    attachment = next(
        (item for item in participant.attachments if item.id == attachment_id),
        None,
    )
    if attachment is None:
        raise NotFoundError("Attachment not found.")

    storage_key = attachment.storage_key
    await session.delete(attachment)
    await session.commit()
    if storage_key:
        delete_training_attachment_file(storage_key)
    return await get_training(session, training_id)


async def list_completed_trainings_for_user(
    session: AsyncSession,
    *,
    target_user_id: UUID,
    current_user_id: UUID,
    is_staff: bool,
) -> list[TrainingRead]:
    if not is_staff and target_user_id != current_user_id:
        raise PermissionDeniedError("Not enough permissions.")

    result = await session.execute(
        _trainings_with_related_query()
        .join(TrainingParticipant, TrainingParticipant.training_id == Training.id)
        .where(
            Training.status == "completed",
            TrainingParticipant.user_id == target_user_id,
        )
        .order_by(Training.updated_at.desc(), Training.id.desc())
    )
    items = list(result.scalars().unique().all())
    return [_to_training_read(item) for item in items]
