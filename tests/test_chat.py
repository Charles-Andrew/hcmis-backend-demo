import anyio
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.department import Department
from app.models.chat import Message
from app.models.user import User
from app.schemas.chat import MessageCreateRequest
from app.services import chat as chat_service


class FakeChatUserRepository:
    users: dict[UUID, User] = {}

    def __init__(self, session):
        self.session = session

    async def get_by_id(self, user_id: UUID):
        return self.users.get(user_id)

    async def list_accessible(self, current_user: User, query: str | None = None):
        users = [user for user in self.users.values() if user.id != current_user.id and user.is_active]
        role = (current_user.role or "EMP").upper()
        if role in {"", "EMP"}:
            users = [user for user in users if user.role == "HR" or (user.role == "DH" and user.department_id == current_user.department_id)]
        elif role == "DH":
            users = [
                user
                for user in users
                if user.role in {"HR", "DIR"} or user.department_id == current_user.department_id
            ]
        elif role == "DIR":
            users = [user for user in users if user.role in {"HR", "DH", "PRES"}]
        elif role == "PRES":
            users = [user for user in users if user.role in {"HR", "DIR"}]
        if query:
            lowered = query.lower()
            users = [
                user
                for user in users
                if lowered in user.first_name.lower()
                or lowered in user.last_name.lower()
                or lowered in user.email.lower()
                or (user.department and lowered in user.department.name.lower())
                or (user.department and lowered in user.department.code.lower())
            ]
        return sorted(users, key=lambda user: (user.first_name, user.last_name))


class FakeMessageRepository:
    items: dict[int, Message] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list_between(self, user_a_id: UUID, user_b_id: UUID):
        return [
            item
            for item in sorted(self.items.values(), key=lambda item: (item.created_at, item.id))
            if {item.sender_id, item.receiver_id} == {user_a_id, user_b_id}
        ]

    async def list_unseen_counts_for_receiver(self, receiver_id: UUID):
        counts: dict[UUID, int] = {}
        for item in self.items.values():
            if item.receiver_id == receiver_id and not item.seen:
                counts[item.sender_id] = counts.get(item.sender_id, 0) + 1
        return list(counts.items())

    async def create(self, message: Message):
        message.id = self.next_id
        self.next_id += 1
        message.created_at = message.created_at or utc_now()
        message.updated_at = message.updated_at or utc_now()
        message.sender = FakeChatUserRepository.users[message.sender_id]
        message.receiver = FakeChatUserRepository.users[message.receiver_id]
        self.items[message.id] = message
        return message

    async def save(self, message: Message):
        self.items[message.id] = message
        return message

    async def mark_seen_between(self, sender_id: UUID, receiver_id: UUID):
        count = 0
        for item in self.items.values():
            if item.sender_id == sender_id and item.receiver_id == receiver_id and not item.seen:
                item.seen = True
                count += 1
        return count


def _reset():
    FakeChatUserRepository.users = {}
    FakeMessageRepository.items = {}
    FakeMessageRepository.next_id = 1


def _seed():
    dept = Department(id=1, name="Operations", code="OPS", is_active=True, workweek=[])
    hr = User(
        id=UUID(int=1),
        email="hr@example.com",
        password_hash="hashed",
        first_name="Harriet",
        last_name="Resource",
        role="HR",
        department_id=1,
        is_active=True,
        is_superuser=False,
        can_modify_shift=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    hr.department = dept
    employee = User(
        id=UUID(int=2),
        email="employee@example.com",
        password_hash="hashed",
        first_name="Eddie",
        last_name="Worker",
        role="EMP",
        department_id=1,
        is_active=True,
        is_superuser=False,
        can_modify_shift=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    employee.department = dept
    director = User(
        id=UUID(int=3),
        email="director@example.com",
        password_hash="hashed",
        first_name="Dana",
        last_name="Director",
        role="DIR",
        department_id=1,
        is_active=True,
        is_superuser=False,
        can_modify_shift=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    director.department = dept
    FakeChatUserRepository.users = {hr.id: hr, employee.id: employee, director.id: director}


def test_chat_contact_search_and_message_flow(monkeypatch):
    _reset()
    _seed()
    monkeypatch.setattr(chat_service, "ChatUserRepository", FakeChatUserRepository)
    monkeypatch.setattr(chat_service, "MessageRepository", FakeMessageRepository)

    contacts = anyio.run(
        chat_service.list_chat_users,
        cast(AsyncSession, object()),
        FakeChatUserRepository.users[UUID(int=2)],
        "resource",
    )
    assert [user.id for user in contacts] == [UUID(int=1)]

    message = anyio.run(
        chat_service.send_message,
        cast(AsyncSession, object()),
        FakeChatUserRepository.users[UUID(int=1)],
        MessageCreateRequest(receiver_id=UUID(int=2), message="Hello"),
    )
    assert message.message == "Hello"

    conversation = anyio.run(
        chat_service.get_conversation,
        cast(AsyncSession, object()),
        FakeChatUserRepository.users[UUID(int=2)],
        UUID(int=1),
    )
    assert len(conversation.messages) == 1
    assert conversation.messages[0].seen is True


def test_chat_unseen_contacts(monkeypatch):
    _reset()
    _seed()
    monkeypatch.setattr(chat_service, "ChatUserRepository", FakeChatUserRepository)
    monkeypatch.setattr(chat_service, "MessageRepository", FakeMessageRepository)

    anyio.run(
        chat_service.send_message,
        cast(AsyncSession, object()),
        FakeChatUserRepository.users[UUID(int=1)],
        MessageCreateRequest(receiver_id=UUID(int=2), message="Ping"),
    )

    unseen = anyio.run(
        chat_service.list_unseen_contacts,
        cast(AsyncSession, object()),
        FakeChatUserRepository.users[UUID(int=2)],
    )
    assert len(unseen) == 1
    assert unseen[0].user.id == UUID(int=1)
    assert unseen[0].unseen_count == 1
