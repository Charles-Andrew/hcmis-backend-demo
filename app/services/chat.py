from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.chat import Message
from app.models.user import User
from app.repositories.chat import ChatUserRepository, MessageRepository
from app.services.notifications import create_notification_if_possible
from app.schemas.chat import (
    ChatContactRead,
    ConversationRead,
    MessageCreateRequest,
    MessageRead,
)
from app.schemas.user import UserRead


async def list_chat_users(
    session: AsyncSession, current_user: User, query: str | None = None
) -> list[User]:
    return await ChatUserRepository(session).list_accessible(current_user, query=query)


async def get_conversation(
    session: AsyncSession, current_user: User, other_user_id: int
) -> ConversationRead:
    user_repository = ChatUserRepository(session)
    other_user = await user_repository.get_by_id(other_user_id)
    if other_user is None:
        raise NotFoundError("User not found.")
    await MessageRepository(session).mark_seen_between(other_user_id, current_user.id)
    messages = await MessageRepository(session).list_between(current_user.id, other_user_id)
    return ConversationRead(
        participants=[UserRead.model_validate(current_user), UserRead.model_validate(other_user)],
        messages=[MessageRead.model_validate(message) for message in messages],
    )


async def send_message(
    session: AsyncSession, current_user: User, payload: MessageCreateRequest
) -> Message:
    user_repository = ChatUserRepository(session)
    recipient = await user_repository.get_by_id(payload.receiver_id)
    if recipient is None:
        raise NotFoundError("User not found.")
    message = Message(
        sender_id=current_user.id,
        receiver_id=payload.receiver_id,
        message=payload.message.strip(),
        seen=False,
    )
    message = await MessageRepository(session).create(message)
    sender_name = " ".join(
        part for part in [current_user.first_name, current_user.last_name] if part
    ).strip() or current_user.email
    await create_notification_if_possible(
        session,
        recipient_id=payload.receiver_id,
        sender_id=current_user.id,
        content=f"New message from {sender_name}.",
        url="/dashboard",
    )
    return message


async def mark_conversation_seen(
    session: AsyncSession, current_user: User, other_user_id: int
) -> int:
    return await MessageRepository(session).mark_seen_between(other_user_id, current_user.id)


async def list_unseen_contacts(
    session: AsyncSession, current_user: User
) -> list[ChatContactRead]:
    user_repository = ChatUserRepository(session)
    contacts = await user_repository.list_accessible(current_user)
    unseen_counts = dict(
        await MessageRepository(session).list_unseen_counts_for_receiver(current_user.id)
    )
    return [
        ChatContactRead(
            user=UserRead.model_validate(contact),
            unseen_count=unseen_counts.get(contact.id, 0),
        )
        for contact in contacts
        if unseen_counts.get(contact.id, 0) > 0
    ]
