import anyio
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.time import utc_now
from app.models.notification import Notification
from app.services import notifications as notification_service


class FakeNotificationRepository:
    notifications: dict[int, Notification] = {}

    def __init__(self, session):
        self.session = session

    async def list_for_recipient(self, recipient_id: int):
        return [
            notification
            for notification in sorted(
                self.notifications.values(), key=lambda item: (item.read, -item.id)
            )
            if notification.recipient_id == recipient_id
        ]

    async def get_for_recipient(self, notification_id: int, recipient_id: int):
        notification = self.notifications.get(notification_id)
        if notification and notification.recipient_id == recipient_id:
            return notification
        return None

    async def save(self, notification: Notification):
        notification.updated_at = utc_now()
        self.notifications[notification.id] = notification
        return notification


async def _list_notifications(recipient_id: int):
    return await notification_service.list_notifications(
        session=cast(AsyncSession, object()),
        recipient_id=recipient_id,
    )


async def _mark_read(notification_id: int, recipient_id: int):
    return await notification_service.mark_notification_read(
        session=cast(AsyncSession, object()),
        notification_id=notification_id,
        recipient_id=recipient_id,
    )


def setup_function():
    FakeNotificationRepository.notifications = {}


def _make_notification(notification_id: int, recipient_id: int, read: bool = False):
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
    first = _make_notification(1, 10, read=False)
    second = _make_notification(2, 10, read=True)
    third = _make_notification(3, 20, read=False)
    FakeNotificationRepository.notifications = {
        first.id: first,
        second.id: second,
        third.id: third,
    }

    monkeypatch.setattr(notification_service, "NotificationRepository", FakeNotificationRepository)

    response = anyio.run(_list_notifications, 10)

    assert [notification.id for notification in response] == [1, 2]


def test_mark_notification_read_marks_notification(monkeypatch):
    notification = _make_notification(1, 10, read=False)
    FakeNotificationRepository.notifications = {notification.id: notification}

    monkeypatch.setattr(notification_service, "NotificationRepository", FakeNotificationRepository)

    response = anyio.run(_mark_read, 1, 10)

    assert response.read is True


def test_mark_notification_read_raises_for_missing_notification(monkeypatch):
    monkeypatch.setattr(notification_service, "NotificationRepository", FakeNotificationRepository)

    try:
        anyio.run(_mark_read, 1, 10)
    except NotFoundError as exc:
        assert exc.detail == "Notification not found."
    else:
        raise AssertionError("Expected NotFoundError to be raised")
