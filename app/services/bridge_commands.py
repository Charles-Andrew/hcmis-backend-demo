from uuid import UUID

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.time import utc_now
from app.models.attendance import BridgeCommand
from app.repositories.attendance import BridgeCommandRepository
from app.schemas.attendance import (
    BridgeCommandAckRequest,
    BridgeCommandScanUsersCreateRequest,
    BridgeCommandRead,
    BridgeCommandSyncUsersCreateRequest,
)
from app.services.notifications import create_notification_if_possible


def _to_read(command: BridgeCommand) -> BridgeCommandRead:
    payload = {}
    if command.payload_json:
        payload = json.loads(command.payload_json)
    return BridgeCommandRead(
        command_id=command.id,
        site_code=command.site_code,
        device_id=command.device_id,
        type=command.command_type,
        payload=payload,
        status=command.status,
        message=command.message,
        created_at=command.created_at,
        dispatched_at=command.dispatched_at,
        executed_at=command.executed_at,
    )


async def queue_sync_users_command(
    session: AsyncSession,
    *,
    payload: BridgeCommandSyncUsersCreateRequest,
    requested_by_user_id: UUID,
) -> BridgeCommandRead:
    command = await BridgeCommandRepository(session).create(
        site_code=payload.site_code,
        device_id=payload.device_id,
        command_type="sync_users",
        payload={},
        created_by_user_id=requested_by_user_id,
    )
    return _to_read(command)


async def queue_scan_users_command(
    session: AsyncSession,
    *,
    payload: BridgeCommandScanUsersCreateRequest,
    requested_by_user_id: UUID,
) -> BridgeCommandRead:
    command = await BridgeCommandRepository(session).create(
        site_code=payload.site_code,
        device_id=payload.device_id,
        command_type="scan_users",
        payload={},
        created_by_user_id=requested_by_user_id,
    )
    return _to_read(command)


async def dispatch_commands(
    session: AsyncSession,
    *,
    site_code: str,
    device_id: str,
    limit: int,
) -> list[BridgeCommandRead]:
    commands = await BridgeCommandRepository(session).dispatch_queued(
        site_code=site_code,
        device_id=device_id,
        limit=limit,
        dispatched_at=utc_now(),
    )
    return [_to_read(command) for command in commands]


async def ack_command(
    session: AsyncSession,
    *,
    command_id: int,
    payload: BridgeCommandAckRequest,
) -> BridgeCommandRead:
    repository = BridgeCommandRepository(session)
    command = await repository.get_by_id(command_id)
    if command is None:
        raise NotFoundError("Bridge command not found.")

    command.status = payload.status
    command.message = payload.message
    command.executed_at = payload.executed_at or utc_now()
    command.updated_at = utc_now()
    command = await repository.save(command)
    if command.created_by_user_id is not None:
        await create_notification_if_possible(
            session,
            recipient_id=command.created_by_user_id,
            content=(
                f"Biometric command '{command.command_type}' on device "
                f"{command.device_id} ({command.site_code}) is now {command.status}."
            ),
            url=(
                f"/hr/users/biometric-sync?site_code={command.site_code}"
                f"&device_id={command.device_id}"
            ),
        )
    return _to_read(command)


async def list_site_device_commands(
    session: AsyncSession,
    *,
    site_code: str,
    device_id: str,
    limit: int,
) -> list[BridgeCommandRead]:
    commands = await BridgeCommandRepository(session).list_for_site_device(
        site_code=site_code,
        device_id=device_id,
        limit=limit,
    )
    return [_to_read(command) for command in commands]
