import anyio
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.time import utc_now
from app.models.notification import Notification
from app.services import notifications as notification_service


class FakeNotificationRepository:
    notifications: dict[int, Notification] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list_for_recipient(
        self,
        recipient_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ):
        items = [
            notification
            for notification in sorted(
                self.notifications.values(), key=lambda item: (item.read, -item.id)
            )
            if notification.recipient_id == recipient_id
        ]
        if unread_only:
            items = [notification for notification in items if not notification.read]
        return items[offset : offset + limit]

    async def get_for_recipient(self, notification_id: int, recipient_id: UUID):
        notification = self.notifications.get(notification_id)
        if notification and notification.recipient_id == recipient_id:
            return notification
        return None

    async def save(self, notification: Notification):
        notification.updated_at = utc_now()
        self.notifications[notification.id] = notification
        return notification

    async def create(self, notification: Notification):
        notification.id = self.next_id
        self.next_id += 1
        notification.created_at = utc_now()
        notification.updated_at = notification.created_at
        self.notifications[notification.id] = notification
        return notification

    async def mark_all_read_for_recipient(self, recipient_id: UUID):
        updated_count = 0
        for notification in self.notifications.values():
            if notification.recipient_id == recipient_id and not notification.read:
                notification.read = True
                notification.updated_at = utc_now()
                updated_count += 1
        return updated_count

    async def count_unread_for_recipient(self, recipient_id: UUID):
        return len(
            [
                notification
                for notification in self.notifications.values()
                if notification.recipient_id == recipient_id and not notification.read
            ]
        )


async def _list_notifications(
    recipient_id: UUID,
    *,
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
):
    return await notification_service.list_notifications(
        session=cast(AsyncSession, object()),
        recipient_id=recipient_id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )


async def _mark_read(notification_id: int, recipient_id: UUID):
    return await notification_service.mark_notification_read(
        session=cast(AsyncSession, object()),
        notification_id=notification_id,
        recipient_id=recipient_id,
    )


async def _mark_all_read(recipient_id: UUID):
    return await notification_service.mark_all_notifications_read(
        session=cast(AsyncSession, object()),
        recipient_id=recipient_id,
    )


async def _count_unread(recipient_id: UUID):
    return await notification_service.count_unread_notifications(
        session=cast(AsyncSession, object()),
        recipient_id=recipient_id,
    )


async def _create_notification(recipient_id: UUID, content: str):
    return await notification_service.create_notification(
        session=cast(AsyncSession, object()),
        recipient_id=recipient_id,
        content=content,
        sender_id=UUID(int=99),
        url="/test",
    )


def setup_function():
    FakeNotificationRepository.notifications = {}
    FakeNotificationRepository.next_id = 1


def _make_notification(notification_id: int, recipient_id: UUID, read: bool = False):
    notification = Notification(
        id=notification_id,
        recipient_id=recipient_id,
        sender_id=None,
        content=f"Notification {notification_id}",
        url="/test",
        read=read,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    return notification


def test_list_notifications_returns_only_recipient_notifications(monkeypatch):
    first = _make_notification(1, UUID(int=10), read=False)
    second = _make_notification(2, UUID(int=10), read=True)
    third = _make_notification(3, UUID(int=20), read=False)
    FakeNotificationRepository.notifications = {
        first.id: first,
        second.id: second,
        third.id: third,
    }

    monkeypatch.setattr(notification_service, "NotificationRepository", FakeNotificationRepository)

    response = anyio.run(_list_notifications, UUID(int=10))

    assert [notification.id for notification in response] == [1, 2]


def test_mark_notification_read_marks_notification(monkeypatch):
    notification = _make_notification(1, UUID(int=10), read=False)
    FakeNotificationRepository.notifications = {notification.id: notification}

    monkeypatch.setattr(notification_service, "NotificationRepository", FakeNotificationRepository)

    response = anyio.run(_mark_read, 1, UUID(int=10))

    assert response.read is True


def test_mark_notification_read_raises_for_missing_notification(monkeypatch):
    monkeypatch.setattr(notification_service, "NotificationRepository", FakeNotificationRepository)

    try:
        anyio.run(_mark_read, 1, UUID(int=10))
    except NotFoundError as exc:
        assert exc.detail == "Notification not found."
    else:
        raise AssertionError("Expected NotFoundError to be raised")


def test_mark_all_read_marks_unread_notifications(monkeypatch):
    first = _make_notification(1, UUID(int=10), read=False)
    second = _make_notification(2, UUID(int=10), read=True)
    third = _make_notification(3, UUID(int=10), read=False)
    FakeNotificationRepository.notifications = {
        first.id: first,
        second.id: second,
        third.id: third,
    }

    monkeypatch.setattr(notification_service, "NotificationRepository", FakeNotificationRepository)

    updated_count = anyio.run(_mark_all_read, UUID(int=10))

    assert updated_count == 2
    assert FakeNotificationRepository.notifications[1].read is True
    assert FakeNotificationRepository.notifications[3].read is True


def test_count_unread_returns_total(monkeypatch):
    first = _make_notification(1, UUID(int=10), read=False)
    second = _make_notification(2, UUID(int=10), read=True)
    third = _make_notification(3, UUID(int=10), read=False)
    FakeNotificationRepository.notifications = {
        first.id: first,
        second.id: second,
        third.id: third,
    }

    monkeypatch.setattr(notification_service, "NotificationRepository", FakeNotificationRepository)

    unread_count = anyio.run(_count_unread, UUID(int=10))

    assert unread_count == 2


def test_create_notification_persists_record(monkeypatch):
    monkeypatch.setattr(notification_service, "NotificationRepository", FakeNotificationRepository)

    created = anyio.run(_create_notification, UUID(int=10), "Hello")

    assert created.id == 1
    assert created.recipient_id == UUID(int=10)
    assert created.content == "Hello"
    assert created.read is False
