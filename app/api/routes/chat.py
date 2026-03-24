from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.chat import Message
from app.models.user import User
from app.schemas.chat import ChatContactRead, ConversationRead, MessageCreateRequest, MessageRead
from app.schemas.user import UserRead
from app.services.chat import (
    get_conversation,
    list_chat_users,
    list_unseen_contacts,
    mark_conversation_seen,
    send_message,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/users", response_model=list[UserRead])
async def read_chat_users(
    query: str | None = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[User]:
    return await list_chat_users(session, current_user, query=query)


@router.get("/conversations/{other_user_id}", response_model=ConversationRead)
async def read_conversation(
    other_user_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ConversationRead:
    return await get_conversation(session, current_user, other_user_id)


@router.post("/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def post_message(
    payload: MessageCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Message:
    return await send_message(session, current_user, payload)


@router.post("/conversations/{other_user_id}/seen", status_code=status.HTTP_204_NO_CONTENT)
async def mark_seen(
    other_user_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    await mark_conversation_seen(session, current_user, other_user_id)


@router.get("/unseen", response_model=list[ChatContactRead])
async def read_unseen_contacts(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ChatContactRead]:
    return await list_unseen_contacts(session, current_user)
