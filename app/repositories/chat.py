from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Message
from app.models.department import Department
from app.models.user import User


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_between(self, user_a_id: UUID, user_b_id: UUID) -> list[Message]:
        statement = (
            select(Message)
            .options(
                selectinload(Message.sender).selectinload(User.department),
                selectinload(Message.receiver).selectinload(User.department),
            )
            .where(
                (
                    (Message.sender_id == user_a_id)
                    & (Message.receiver_id == user_b_id)
                )
                | (
                    (Message.sender_id == user_b_id)
                    & (Message.receiver_id == user_a_id)
                )
            )
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_unseen_counts_for_receiver(self, receiver_id: UUID) -> list[tuple[UUID, int]]:
        statement = (
            select(Message.sender_id, func.count(Message.id))
            .where(Message.receiver_id == receiver_id, Message.seen.is_(False))
            .group_by(Message.sender_id)
        )
        result = await self.session.execute(statement)
        return [(sender_id, int(count)) for sender_id, count in result.all()]

    async def create(self, message: Message) -> Message:
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def save(self, message: Message) -> Message:
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def mark_seen_between(self, sender_id: UUID, receiver_id: UUID) -> int:
        statement = select(Message).where(
            Message.sender_id == sender_id,
            Message.receiver_id == receiver_id,
            Message.seen.is_(False),
        )
        result = await self.session.execute(statement)
        messages = list(result.scalars().all())
        for message in messages:
            message.seen = True
        if messages:
            await self.session.commit()
        return len(messages)


class ChatUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(
            select(User).options(selectinload(User.department)).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_accessible(self, current_user: User, query: str | None = None) -> list[User]:
        statement = (
            select(User)
            .options(selectinload(User.department))
            .where(User.is_active.is_(True), User.id != current_user.id)
        )

        role = (current_user.role or "EMP").upper()
        if role in {"", "EMP"}:
            statement = statement.where(
                (
                    (User.role == "HR")
                    | (
                        (User.role == "DH")
                        & (User.department_id == current_user.department_id)
                    )
                )
            )
        elif role == "DH":
            statement = statement.where(
                (User.role == "HR")
                | (User.role == "DIR")
                | (User.department_id == current_user.department_id)
            )
        elif role == "DIR":
            statement = statement.where(
                (User.role == "HR")
                | (User.role == "DH")
                | (User.role == "PRES")
            )
        elif role == "PRES":
            statement = statement.where((User.role == "HR") | (User.role == "DIR"))

        if query:
            lowered = f"%{query.lower()}%"
            statement = statement.join(Department, Department.id == User.department_id).where(
                func.lower(User.first_name).like(lowered)
                | func.lower(User.last_name).like(lowered)
                | func.lower(User.email).like(lowered)
                | func.lower(Department.name).like(lowered)
                | func.lower(Department.code).like(lowered)
            )

        statement = statement.order_by(User.first_name.asc(), User.last_name.asc())
        result = await self.session.execute(statement)
        return list(result.scalars().all())
