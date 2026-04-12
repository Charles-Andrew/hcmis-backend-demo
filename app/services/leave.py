from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capabilities import is_staff_user
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.time import utc_now
from app.models.leave import (
    LeaveCredit,
    LeaveRequest,
    LeaveRequestApprover,
    LeaveRequestStatus,
    LeaveType,
)
from app.models.attendance import OvertimeRequest
from app.repositories.attendance import OvertimeRepository
from app.models.user import User
from app.repositories.leave import (
    LeaveCreditRepository,
    LeaveRequestRepository,
)
from app.repositories.users import UserRepository
from app.services.notifications import create_notification
from app.schemas.leave import LeaveCreditUpsertRequest, LeaveRequestCreateRequest, LeaveRequestReviewRequest


def list_leave_types() -> list[dict[str, str]]:
    return [
        {
            "value": leave_type.value,
            "label": leave_type.name.replace("_", " ").title(),
        }
        for leave_type in LeaveType
    ]


async def _ensure_leave_credit(session: AsyncSession, user_id: UUID) -> LeaveCredit:
    repository = LeaveCreditRepository(session)
    leave_credit = await repository.get_by_user_id(user_id)
    if leave_credit is None:
        leave_credit = LeaveCredit(user_id=user_id, credits=0, used_credits=0)
        return await repository.create(leave_credit)
    return leave_credit


async def _get_approval_pool(session: AsyncSession, user: User) -> list[UUID]:
    if user.level_1_approver_id is None:
        raise NotFoundError("No Level 1 approver is configured for this user.")
    user_repository = UserRepository(session)
    primary_approver = await user_repository.get_by_id(user.level_1_approver_id)
    if primary_approver is None or not primary_approver.is_active:
        raise NotFoundError("Level 1 approver is not available for this user.")
    if primary_approver.id == user.id:
        raise ConflictError("Level 1 approver cannot be the same as the requester.")
    return [primary_approver.id]


async def _get_backup_approver_id(session: AsyncSession, user: User) -> UUID | None:
    if user.level_2_approver_id is not None:
        user_repository = UserRepository(session)
        backup = await user_repository.get_by_id(user.level_2_approver_id)
        if backup is None or not backup.is_active:
            raise NotFoundError("Level 2 approver is not available for this user.")
        if backup.id == user.id:
            raise ConflictError("Level 2 approver cannot be the same as the requester.")
        if user.level_1_approver_id is not None and backup.id == user.level_1_approver_id:
            raise ConflictError("Level 2 approver must be different from Level 1 approver.")
        return backup.id

    return None


def _leave_type_label(leave_type: str) -> str:
    for item in list_leave_types():
        if item["value"] == leave_type:
            return item["label"]
    return leave_type


def _user_display_name(user: User) -> str:
    full_name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
    return full_name or user.email


async def _notify_user(
    session: AsyncSession,
    *,
    recipient_id: UUID | None,
    sender_id: UUID | None,
    content: str,
    url: str | None,
) -> None:
    if recipient_id is None:
        return
    if recipient_id == sender_id:
        return

    # Service tests use cast(object()) instead of an actual AsyncSession.
    if not hasattr(session, "add") or not hasattr(session, "commit"):
        return

    await create_notification(
        session,
        recipient_id=recipient_id,
        sender_id=sender_id,
        content=content,
        url=url,
    )


async def list_leave_requests(
    session: AsyncSession,
    user_id: UUID | None = None,
    department_id: int | None = None,
    approver_id: UUID | None = None,
    status: str | None = None,
    year: int | None = None,
    month: int | None = None,
) -> list[LeaveRequest]:
    return await LeaveRequestRepository(session).list(
        user_id=user_id,
        department_id=department_id,
        approver_id=approver_id,
        status=status,
        year=year,
        month=month,
    )


async def list_leave_years(session: AsyncSession) -> list[int]:
    return await LeaveRequestRepository(session).list_years()


async def get_leave_request(session: AsyncSession, leave_id: int) -> LeaveRequest:
    leave_request = await LeaveRequestRepository(session).get_by_id(leave_id)
    if leave_request is None:
        raise NotFoundError("Leave request not found.")
    return leave_request


async def create_leave_request(
    session: AsyncSession, current_user: User, payload: LeaveRequestCreateRequest
) -> LeaveRequest:
    active_statuses = (
        LeaveRequestStatus.PENDING.value,
        LeaveRequestStatus.APPROVED.value,
    )
    existing_leave = await LeaveRequestRepository(session).get_active_for_user_date(
        current_user.id,
        payload.leave_date,
        statuses=active_statuses,
    )
    if existing_leave is not None:
        raise ConflictError("An active leave request already exists for this date.")

    existing_overtime = await OvertimeRepository(session).get_active_for_user_date(
        current_user.id,
        payload.leave_date,
        statuses=(
            OvertimeRequest.Status.PENDING.value,
            OvertimeRequest.Status.APPROVED.value,
        ),
    )
    if existing_overtime is not None:
        raise ConflictError("An active overtime request already exists for this date.")

    if payload.leave_type == LeaveType.PAID.value:
        leave_credit = await _ensure_leave_credit(session, current_user.id)
        if leave_credit.remaining_credits <= 0:
            raise ConflictError("Insufficient leave credits for paid leave.")

    approval_pool = await _get_approval_pool(session, current_user)
    first_approver_id = approval_pool[0]
    second_approver_id = await _get_backup_approver_id(session, current_user)
    leave_request = LeaveRequest(
        user_id=current_user.id,
        leave_date=payload.leave_date,
        leave_type=payload.leave_type,
        info=payload.info,
        first_approver_id=first_approver_id,
        second_approver_id=second_approver_id,
        first_approver_status=LeaveRequestStatus.PENDING.value,
        second_approver_status=(
            LeaveRequestStatus.PENDING.value if second_approver_id is not None else None
        ),
        status=LeaveRequestStatus.PENDING.value,
        approver_pool=[
            LeaveRequestApprover(
                approver_id=approver_id,
                status=LeaveRequestStatus.PENDING.value,
            )
            for approver_id in approval_pool
        ],
    )
    leave_request = await LeaveRequestRepository(session).create(leave_request)

    leave_date = leave_request.leave_date.isoformat()
    requester_name = _user_display_name(current_user)
    leave_type = _leave_type_label(leave_request.leave_type)
    for approver_id in approval_pool:
        await _notify_user(
            session,
            recipient_id=approver_id,
            sender_id=current_user.id,
            content=f"{requester_name} filed a {leave_type} leave request for {leave_date}.",
            url=f"/leave/inbox?leave_id={leave_request.id}",
        )
    return leave_request


async def cancel_leave_request(
    session: AsyncSession, leave_id: int, current_user: User
) -> LeaveRequest:
    repository = LeaveRequestRepository(session)
    leave_request = await repository.get_by_id(leave_id)
    if leave_request is None:
        raise NotFoundError("Leave request not found.")

    if leave_request.user_id != current_user.id and not is_staff_user(current_user):
        raise PermissionDeniedError("You are not allowed to cancel this leave request.")
    if leave_request.status != LeaveRequestStatus.PENDING.value:
        raise ConflictError("Only pending leave requests can be cancelled.")

    now = utc_now()
    leave_request.status = LeaveRequestStatus.CANCELLED.value
    if leave_request.first_approver_status == LeaveRequestStatus.PENDING.value:
        leave_request.first_approver_status = LeaveRequestStatus.CANCELLED.value
        leave_request.first_approver_at = now
    if leave_request.second_approver_status == LeaveRequestStatus.PENDING.value:
        leave_request.second_approver_status = LeaveRequestStatus.CANCELLED.value
        leave_request.second_approver_at = now
    for assignment in leave_request.approver_pool:
        if assignment.status == LeaveRequestStatus.PENDING.value:
            assignment.status = LeaveRequestStatus.CANCELLED.value
            assignment.acted_at = now

    return await repository.save(leave_request)


async def review_leave_request(
    session: AsyncSession,
    leave_id: int,
    current_user: User,
    payload: LeaveRequestReviewRequest,
) -> LeaveRequest:
    repository = LeaveRequestRepository(session)
    leave_request = await repository.get_by_id(leave_id)
    if leave_request is None:
        raise NotFoundError("Leave request not found.")

    if leave_request.status != LeaveRequestStatus.PENDING.value:
        raise ConflictError("Leave request has already been processed.")

    response = payload.response
    now = utc_now()

    if leave_request.user_id == current_user.id:
        raise PermissionDeniedError("You cannot review your own leave request.")

    current_pool_assignment = next(
        (
            assignment
            for assignment in leave_request.approver_pool
            if assignment.approver_id == current_user.id
        ),
        None,
    )
    if current_pool_assignment is None:
        raise PermissionDeniedError("You do not have approval rights for this request.")
    if current_pool_assignment.status != LeaveRequestStatus.PENDING.value:
        raise ConflictError("Leave request has already been reviewed by you.")

    final_status = (
        LeaveRequestStatus.APPROVED.value
        if response == "APPROVE"
        else LeaveRequestStatus.REJECTED.value
    )
    current_pool_assignment.status = final_status
    current_pool_assignment.acted_at = now
    for assignment in leave_request.approver_pool:
        if assignment is current_pool_assignment:
            continue
        if assignment.status == LeaveRequestStatus.PENDING.value:
            assignment.status = final_status

    if (
        leave_request.first_approver_id is not None
        and leave_request.first_approver_status == LeaveRequestStatus.PENDING.value
    ):
        leave_request.first_approver_status = final_status
        leave_request.first_approver_at = now
    if (
        leave_request.second_approver_id is not None
        and leave_request.second_approver_status == LeaveRequestStatus.PENDING.value
    ):
        leave_request.second_approver_status = final_status
        leave_request.second_approver_at = now
    leave_request.status = final_status

    leave_request = await repository.save(leave_request)

    if (
        leave_request.status == LeaveRequestStatus.APPROVED.value
        and leave_request.leave_type == LeaveType.PAID.value
    ):
        leave_credit = await _ensure_leave_credit(session, leave_request.user_id)
        if leave_credit.remaining_credits <= 0:
            raise ConflictError("Insufficient leave credits for paid leave.")
        leave_credit.used_credits += 1
        await LeaveCreditRepository(session).save(leave_credit)

    leave_date = leave_request.leave_date.isoformat()
    leave_type = _leave_type_label(leave_request.leave_type)

    if response == "APPROVE":
        if leave_request.status == LeaveRequestStatus.APPROVED.value:
            await _notify_user(
                session,
                recipient_id=leave_request.user_id,
                sender_id=current_user.id,
                content=f"Your {leave_type} leave request for {leave_date} has been approved.",
                url=f"/leave?leave_id={leave_request.id}",
            )
    elif leave_request.status == LeaveRequestStatus.REJECTED.value:
        await _notify_user(
            session,
            recipient_id=leave_request.user_id,
            sender_id=current_user.id,
            content=f"Your {leave_type} leave request for {leave_date} has been rejected.",
            url=f"/leave?leave_id={leave_request.id}",
        )

    return leave_request


async def escalate_leave_request(
    session: AsyncSession,
    leave_id: int,
    current_user: User,
) -> LeaveRequest:
    repository = LeaveRequestRepository(session)
    leave_request = await repository.get_by_id(leave_id)
    if leave_request is None:
        raise NotFoundError("Leave request not found.")
    if leave_request.status != LeaveRequestStatus.PENDING.value:
        raise ConflictError("Only pending leave requests can be escalated.")
    if leave_request.escalated_to_backup_at is not None:
        raise ConflictError("Leave request is already escalated to the backup approver.")
    if leave_request.second_approver_id is None:
        raise ConflictError("No Level 2 backup approver is configured for this request.")
    if leave_request.user_id == leave_request.second_approver_id:
        raise ConflictError("Level 2 approver cannot be the same as the requester.")

    user_repository = UserRepository(session)
    backup_approver = await user_repository.get_by_id(leave_request.second_approver_id)
    if backup_approver is None or not backup_approver.is_active:
        raise ConflictError("Level 2 backup approver is not available.")

    if leave_request.first_approver_status != LeaveRequestStatus.PENDING.value:
        raise ConflictError("Level 1 approver has already acted on this request.")

    now = utc_now()
    if leave_request.first_approver_id is not None:
        for assignment in leave_request.approver_pool:
            if (
                assignment.approver_id == leave_request.first_approver_id
                and assignment.status == LeaveRequestStatus.PENDING.value
            ):
                assignment.status = LeaveRequestStatus.CANCELLED.value
                assignment.acted_at = now

    leave_request.first_approver_status = LeaveRequestStatus.CANCELLED.value
    leave_request.first_approver_at = now
    leave_request.second_approver_status = LeaveRequestStatus.PENDING.value
    leave_request.second_approver_at = None
    leave_request.escalated_to_backup_at = now
    leave_request.escalated_to_backup_by_id = current_user.id

    backup_assignment = next(
        (
            assignment
            for assignment in leave_request.approver_pool
            if assignment.approver_id == leave_request.second_approver_id
        ),
        None,
    )
    if backup_assignment is None:
        leave_request.approver_pool.append(
            LeaveRequestApprover(
                approver_id=leave_request.second_approver_id,
                status=LeaveRequestStatus.PENDING.value,
            )
        )
    else:
        backup_assignment.status = LeaveRequestStatus.PENDING.value
        backup_assignment.acted_at = None

    leave_request = await repository.save(leave_request)
    requester_name = _user_display_name(leave_request.user) if leave_request.user else "A user"
    leave_type = _leave_type_label(leave_request.leave_type)
    await _notify_user(
        session,
        recipient_id=leave_request.second_approver_id,
        sender_id=current_user.id,
        content=(
            f"{requester_name}'s {leave_type} leave request for "
            f"{leave_request.leave_date.isoformat()} was escalated to you as backup approver."
        ),
        url=f"/leave/inbox?leave_id={leave_request.id}",
    )
    return leave_request

async def list_leave_credits(
    session: AsyncSession, user_id: UUID | None = None, department_id: int | None = None
) -> list[LeaveCredit]:
    credits = await LeaveCreditRepository(session).list()
    if user_id is not None:
        credits = [credit for credit in credits if credit.user_id == user_id]
    if department_id is not None:
        credits = [
            credit
            for credit in credits
            if credit.user is not None and credit.user.department_id == department_id
        ]
    return credits


async def get_my_leave_credit(session: AsyncSession, user_id: UUID) -> LeaveCredit:
    return await _ensure_leave_credit(session, user_id)


async def set_leave_credit(
    session: AsyncSession, user_id: UUID, payload: LeaveCreditUpsertRequest
) -> LeaveCredit:
    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")

    repository = LeaveCreditRepository(session)
    leave_credit = await repository.get_by_user_id(user_id)
    if leave_credit is None:
        leave_credit = LeaveCredit(user_id=user_id, credits=payload.credits, used_credits=0)
        leave_credit = await repository.create(leave_credit)
        await _notify_user(
            session,
            recipient_id=user_id,
            sender_id=None,
            content=f"Your annual leave credit was set to {leave_credit.credits} day(s).",
            url="/leave",
        )
        return leave_credit

    leave_credit.credits = payload.credits
    leave_credit = await repository.save(leave_credit)
    await _notify_user(
        session,
        recipient_id=user_id,
        sender_id=None,
        content=f"Your annual leave credit was updated to {leave_credit.credits} day(s).",
        url="/leave",
    )
    return leave_credit


async def reset_leave_credit(session: AsyncSession, user_id: UUID) -> LeaveCredit:
    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")

    leave_credit = await _ensure_leave_credit(session, user_id)
    leave_credit.used_credits = 0
    leave_credit = await LeaveCreditRepository(session).save(leave_credit)
    await _notify_user(
        session,
        recipient_id=user_id,
        sender_id=None,
        content=(
            "Your leave usage was reset and all configured leave credits are now available."
        ),
        url="/leave",
    )
    return leave_credit
