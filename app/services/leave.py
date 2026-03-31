from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capabilities import is_staff_user
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.time import utc_now
from app.models.leave import (
    LeaveApprover,
    LeaveCredit,
    LeaveRequest,
    LeaveRequestStatus,
    LeaveType,
)
from app.models.user import User
from app.repositories.departments import DepartmentRepository
from app.repositories.leave import (
    LeaveApproverRepository,
    LeaveCreditRepository,
    LeaveRequestRepository,
)
from app.repositories.users import UserRepository
from app.schemas.leave import (
    LeaveApproverUpsertRequest,
    LeaveCreditUpsertRequest,
    LeaveRequestCreateRequest,
    LeaveRequestReviewRequest,
)


def list_leave_types() -> list[dict[str, str]]:
    return [
        {
            "value": leave_type.value,
            "label": leave_type.name.replace("_", " ").title(),
        }
        for leave_type in LeaveType
    ]


def _normalize_approval_chain(
    first_approver_id: int | None, second_approver_id: int | None
) -> tuple[int | None, int | None]:
    chain: list[int] = []
    for approver_id in (first_approver_id, second_approver_id):
        if approver_id is not None and approver_id not in chain:
            chain.append(approver_id)
    first = chain[0] if chain else None
    second = chain[1] if len(chain) > 1 else None
    return first, second


async def _ensure_leave_credit(session: AsyncSession, user_id: int) -> LeaveCredit:
    repository = LeaveCreditRepository(session)
    leave_credit = await repository.get_by_user_id(user_id)
    if leave_credit is None:
        leave_credit = LeaveCredit(user_id=user_id, credits=0, used_credits=0)
        return await repository.create(leave_credit)
    return leave_credit


async def _get_approval_chain(
    session: AsyncSession, user: User
) -> tuple[int | None, int | None]:
    if user.department_id is None:
        raise ConflictError("User is not assigned to a department.")

    approver_settings = await LeaveApproverRepository(session).get_by_department_id(
        user.department_id
    )
    if approver_settings is None:
        raise NotFoundError("Leave approver settings not found for this department.")

    role = (user.role or "EMP").upper()
    if role == "DH":
        chain = (
            approver_settings.director_approver_id,
            approver_settings.hr_approver_id,
        )
    elif role == "DIR":
        chain = (
            approver_settings.president_approver_id,
            approver_settings.hr_approver_id,
        )
    elif role == "PRES":
        chain = (approver_settings.hr_approver_id, None)
    else:
        chain = (
            approver_settings.department_approver_id,
            approver_settings.hr_approver_id,
        )

    first_approver_id, second_approver_id = _normalize_approval_chain(*chain)
    if first_approver_id is None:
        raise NotFoundError("No leave approver is configured for this user.")
    return first_approver_id, second_approver_id


async def list_leave_requests(
    session: AsyncSession,
    user_id: int | None = None,
    department_id: int | None = None,
    approver_id: int | None = None,
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
    if payload.leave_type == LeaveType.PAID.value:
        leave_credit = await _ensure_leave_credit(session, current_user.id)
        if leave_credit.remaining_credits <= 0:
            raise ConflictError("Insufficient leave credits for paid leave.")

    first_approver_id, second_approver_id = await _get_approval_chain(
        session, current_user
    )
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
    )
    return await LeaveRequestRepository(session).create(leave_request)


async def delete_leave_request(
    session: AsyncSession, leave_id: int, current_user: User
) -> None:
    repository = LeaveRequestRepository(session)
    leave_request = await repository.get_by_id(leave_id)
    if leave_request is None:
        raise NotFoundError("Leave request not found.")

    if leave_request.user_id != current_user.id and not is_staff_user(current_user):
        raise PermissionDeniedError("You are not allowed to delete this leave request.")

    if (
        leave_request.status == LeaveRequestStatus.APPROVED.value
        and leave_request.leave_type == LeaveType.PAID.value
    ):
        leave_credit = await _ensure_leave_credit(session, leave_request.user_id)
        if leave_credit.used_credits > 0:
            leave_credit.used_credits -= 1
            await LeaveCreditRepository(session).save(leave_credit)

    await repository.delete(leave_request)


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

    if leave_request.first_approver_id == current_user.id:
        if leave_request.first_approver_status != LeaveRequestStatus.PENDING.value:
            raise ConflictError("Leave request has already been reviewed by you.")
        leave_request.first_approver_status = (
            LeaveRequestStatus.APPROVED.value
            if response == "APPROVE"
            else LeaveRequestStatus.REJECTED.value
        )
        leave_request.first_approver_at = now
        if response == "REJECT":
            leave_request.status = LeaveRequestStatus.REJECTED.value
        elif leave_request.second_approver_id is None:
            leave_request.status = LeaveRequestStatus.APPROVED.value
        else:
            leave_request.status = LeaveRequestStatus.PENDING.value
    elif leave_request.second_approver_id == current_user.id:
        if leave_request.second_approver_status is not None and (
            leave_request.second_approver_status != LeaveRequestStatus.PENDING.value
        ):
            raise ConflictError("Leave request has already been reviewed by you.")
        if leave_request.first_approver_status != LeaveRequestStatus.APPROVED.value:
            raise ConflictError("Leave request is not ready for your review.")
        leave_request.second_approver_status = (
            LeaveRequestStatus.APPROVED.value
            if response == "APPROVE"
            else LeaveRequestStatus.REJECTED.value
        )
        leave_request.second_approver_at = now
        leave_request.status = (
            LeaveRequestStatus.APPROVED.value
            if response == "APPROVE"
            else LeaveRequestStatus.REJECTED.value
        )
    else:
        raise PermissionDeniedError("You do not have approval rights for this request.")

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

    return leave_request


async def list_leave_approvers(session: AsyncSession) -> list[LeaveApprover]:
    return await LeaveApproverRepository(session).list()


async def upsert_leave_approver(
    session: AsyncSession,
    department_id: int,
    payload: LeaveApproverUpsertRequest,
) -> LeaveApprover:
    department = await DepartmentRepository(session).get_by_id(department_id)
    if department is None:
        raise NotFoundError("Department not found.")

    user_repository = UserRepository(session)
    for approver_id in [
        payload.department_approver_id,
        payload.director_approver_id,
        payload.president_approver_id,
        payload.hr_approver_id,
    ]:
        if approver_id is None:
            continue
        user = await user_repository.get_by_id(approver_id)
        if user is None:
            raise NotFoundError("Approver user not found.")

    repository = LeaveApproverRepository(session)
    leave_approver = await repository.get_by_department_id(department_id)
    if leave_approver is None:
        leave_approver = LeaveApprover(department_id=department_id)
        leave_approver.department_approver_id = payload.department_approver_id
        leave_approver.director_approver_id = payload.director_approver_id
        leave_approver.president_approver_id = payload.president_approver_id
        leave_approver.hr_approver_id = payload.hr_approver_id
        return await repository.create(leave_approver)

    leave_approver.department_approver_id = payload.department_approver_id
    leave_approver.director_approver_id = payload.director_approver_id
    leave_approver.president_approver_id = payload.president_approver_id
    leave_approver.hr_approver_id = payload.hr_approver_id
    return await repository.save(leave_approver)


async def delete_leave_approver(session: AsyncSession, department_id: int) -> None:
    repository = LeaveApproverRepository(session)
    leave_approver = await repository.get_by_department_id(department_id)
    if leave_approver is None:
        raise NotFoundError("Leave approver settings not found.")
    await repository.delete(leave_approver)


async def list_leave_credits(
    session: AsyncSession, user_id: int | None = None, department_id: int | None = None
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


async def get_my_leave_credit(session: AsyncSession, user_id: int) -> LeaveCredit:
    return await _ensure_leave_credit(session, user_id)


async def set_leave_credit(
    session: AsyncSession, user_id: int, payload: LeaveCreditUpsertRequest
) -> LeaveCredit:
    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")

    repository = LeaveCreditRepository(session)
    leave_credit = await repository.get_by_user_id(user_id)
    if leave_credit is None:
        leave_credit = LeaveCredit(user_id=user_id, credits=payload.credits, used_credits=0)
        return await repository.create(leave_credit)

    leave_credit.credits = payload.credits
    return await repository.save(leave_credit)


async def reset_leave_credit(session: AsyncSession, user_id: int) -> LeaveCredit:
    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")

    leave_credit = await _ensure_leave_credit(session, user_id)
    leave_credit.used_credits = 0
    return await LeaveCreditRepository(session).save(leave_credit)
