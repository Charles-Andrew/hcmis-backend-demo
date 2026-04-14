from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.time import utc_now
from app.models.attendance import AttendanceRecord, OvertimeRequest
from app.models.leave import LeaveRequestStatus
from app.models.special_requests import (
    CertificateAttendanceRequest,
    CertificateAttendanceRequestApprover,
    OfficialBusinessRequest,
    OfficialBusinessRequestApprover,
    SpecialRequestStatus,
)
from app.models.user import User
from app.repositories.attendance import AttendanceRecordRepository, OvertimeRepository
from app.repositories.leave import LeaveRequestRepository
from app.repositories.special_requests import (
    CertificateAttendanceRequestRepository,
    OfficialBusinessRequestRepository,
)
from app.repositories.users import UserRepository
from app.schemas.special_requests import (
    CertificateAttendanceRequestCreateRequest,
    OfficialBusinessRequestCreateRequest,
    SpecialRequestApproverAssignmentRead,
    SpecialRequestRespondRequest,
    SpecialRequestScope,
)
from app.schemas.user import UserRead
from app.services.notifications import create_notification


def _display_user_name(user: User) -> str:
    full_name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
    return full_name or user.email


def _certificate_attendance_timestamp(request: CertificateAttendanceRequest) -> datetime:
    return datetime.combine(request.date, request.time, tzinfo=UTC)


async def _notify_user(
    session: AsyncSession,
    *,
    recipient_id: UUID | None,
    sender_id: UUID | None,
    content: str,
    url: str | None,
) -> None:
    if recipient_id is None or recipient_id == sender_id:
        return
    if not hasattr(session, "add") or not hasattr(session, "commit"):
        return

    await create_notification(
        session,
        recipient_id=recipient_id,
        sender_id=sender_id,
        content=content,
        url=url,
    )


async def _build_approval_pool(session: AsyncSession, user: User) -> list[User]:
    if user.level_1_approver_id is None:
        raise NotFoundError("No Level 1 approver is configured for this user.")

    primary_approver = await UserRepository(session).get_by_id(user.level_1_approver_id)
    if primary_approver is None or not primary_approver.is_active:
        raise NotFoundError("Level 1 approver is not available for this user.")
    if primary_approver.id == user.id:
        raise ConflictError("Level 1 approver cannot be the same as the requester.")
    return [primary_approver]


async def _get_backup_approver(session: AsyncSession, user: User) -> User | None:
    if user.level_2_approver_id is None:
        return None

    backup_approver = await UserRepository(session).get_by_id(user.level_2_approver_id)
    if backup_approver is None or not backup_approver.is_active:
        raise NotFoundError("Level 2 approver is not available for this user.")
    if backup_approver.id == user.id:
        raise ConflictError("Level 2 approver cannot be the same as the requester.")
    if user.level_1_approver_id is not None and backup_approver.id == user.level_1_approver_id:
        raise ConflictError("Level 2 approver must be different from Level 1 approver.")
    return backup_approver


def _resolve_scope(
    *,
    scope: SpecialRequestScope | None,
    current_user_id: UUID,
    current_user_is_staff: bool,
    user_id: UUID | None,
    approver_id: UUID | None,
) -> tuple[SpecialRequestScope, UUID | None, UUID | None]:
    if scope is not None:
        scope_label = scope
    elif user_id is not None:
        scope_label = "mine"
    elif approver_id is not None:
        scope_label = "approvals"
    elif current_user_is_staff:
        scope_label = "all"
    else:
        scope_label = "mine"

    selected_user_id = user_id
    selected_approver_id = approver_id

    if scope_label == "all":
        if not current_user_is_staff:
            raise PermissionDeniedError("You do not have permission to view all requests.")
    elif scope_label == "approvals":
        if selected_approver_id is None:
            selected_approver_id = current_user_id
        elif selected_approver_id != current_user_id and not current_user_is_staff:
            raise PermissionDeniedError("You do not have permission to view this approver's requests.")
    else:
        if selected_user_id is None:
            selected_user_id = current_user_id
        elif selected_user_id != current_user_id and not current_user_is_staff:
            raise PermissionDeniedError("You do not have permission to view this user's requests.")

    return scope_label, selected_user_id, selected_approver_id


async def _ensure_no_conflicting_active_requests(
    session: AsyncSession,
    *,
    user_id: UUID,
    selected_date,
) -> None:
    existing_overtime = await OvertimeRepository(session).get_active_for_user_date(
        user_id,
        selected_date,
        statuses=(
            OvertimeRequest.Status.PENDING.value,
            OvertimeRequest.Status.APPROVED.value,
        ),
    )
    if existing_overtime is not None:
        raise ConflictError("An active overtime request already exists for this date.")

    existing_leave = await LeaveRequestRepository(session).get_active_for_user_date(
        user_id,
        selected_date,
        statuses=(
            LeaveRequestStatus.PENDING.value,
            LeaveRequestStatus.APPROVED.value,
        ),
    )
    if existing_leave is not None:
        raise ConflictError("An active leave request already exists for this date.")

    existing_official_business = await OfficialBusinessRequestRepository(
        session
    ).get_active_for_user_date(
        user_id,
        selected_date,
        statuses=(
            SpecialRequestStatus.PENDING.value,
            SpecialRequestStatus.APPROVED.value,
        ),
    )
    if existing_official_business is not None:
        raise ConflictError("An active official business request already exists for this date.")

    existing_certificate = await CertificateAttendanceRequestRepository(
        session
    ).get_active_for_user_date(
        user_id,
        selected_date,
        statuses=(
            SpecialRequestStatus.PENDING.value,
            SpecialRequestStatus.APPROVED.value,
        ),
    )
    if existing_certificate is not None:
        raise ConflictError("An active certificate of attendance request already exists for this date.")


async def get_my_special_request_approver_assignment(
    session: AsyncSession, current_user: User
) -> SpecialRequestApproverAssignmentRead:
    approvers = await _build_approval_pool(session, current_user)
    approver = approvers[0] if approvers else None
    return SpecialRequestApproverAssignmentRead(
        approver_id=approver.id if approver is not None else None,
        approver=UserRead.model_validate(approver) if approver is not None else None,
        approver_ids=[item.id for item in approvers],
        approvers=[UserRead.model_validate(item) for item in approvers],
    )


async def list_official_business_requests(
    session: AsyncSession,
    *,
    current_user_id: UUID,
    current_user_is_staff: bool,
    scope: SpecialRequestScope | None = None,
    user_id: UUID | None = None,
    approver_id: UUID | None = None,
    year: int | None = None,
    month: int | None = None,
    status: str | None = None,
    department_id: int | None = None,
    query: str | None = None,
) -> list[OfficialBusinessRequest]:
    scope_label, selected_user_id, selected_approver_id = _resolve_scope(
        scope=scope,
        current_user_id=current_user_id,
        current_user_is_staff=current_user_is_staff,
        user_id=user_id,
        approver_id=approver_id,
    )
    return await OfficialBusinessRequestRepository(session).list(
        user_id=selected_user_id if scope_label != "approvals" else None,
        approver_id=selected_approver_id if scope_label != "mine" else None,
        year=year,
        month=month,
        status=status,
        department_id=department_id,
        query=query,
    )


async def create_official_business_request(
    session: AsyncSession,
    current_user: User,
    payload: OfficialBusinessRequestCreateRequest,
) -> OfficialBusinessRequest:
    user = await UserRepository(session).get_by_id(payload.user_id)
    if user is None:
        raise NotFoundError("User not found.")

    await _ensure_no_conflicting_active_requests(
        session,
        user_id=payload.user_id,
        selected_date=payload.date,
    )

    approvers = await _build_approval_pool(session, user)
    if not approvers:
        raise NotFoundError("No Level 1 approver is configured for this user.")

    first_approver = approvers[0]
    request = OfficialBusinessRequest(
        user_id=payload.user_id,
        approver_id=first_approver.id,
        info=payload.info,
        date=payload.date,
        status=SpecialRequestStatus.PENDING.value,
        approver_pool=[
            OfficialBusinessRequestApprover(
                approver_id=approver.id,
                status=SpecialRequestStatus.PENDING.value,
            )
            for approver in approvers
        ],
    )
    request = await OfficialBusinessRequestRepository(session).create(request)

    requester_name = _display_user_name(user)
    for approver in approvers:
        await _notify_user(
            session,
            recipient_id=approver.id,
            sender_id=current_user.id,
            content=(
                f"{requester_name} filed an official business request "
                f"for {request.date.isoformat()}."
            ),
            url="/requests/inbox",
        )
    return request


async def respond_to_official_business_request(
    session: AsyncSession,
    request_id: int,
    approver_id: UUID,
    payload: SpecialRequestRespondRequest,
) -> OfficialBusinessRequest:
    repository = OfficialBusinessRequestRepository(session)
    request = await repository.get_by_id(request_id)
    if request is None:
        raise NotFoundError("Official business request not found.")
    if request.user_id == approver_id:
        raise PermissionDeniedError("You cannot review your own official business request.")

    current_pool_assignment = next(
        (
            assignment
            for assignment in request.approver_pool
            if assignment.approver_id == approver_id
        ),
        None,
    )
    if current_pool_assignment is None:
        raise PermissionDeniedError("You do not have permission to respond to this request.")
    if current_pool_assignment.status != SpecialRequestStatus.PENDING.value:
        raise ConflictError("This official business request has already been decided by you.")
    if request.status != SpecialRequestStatus.PENDING.value:
        raise ConflictError("This official business request has already been decided.")

    final_status = (
        SpecialRequestStatus.APPROVED.value
        if payload.response == "APPROVE"
        else SpecialRequestStatus.REJECTED.value
    )
    now = utc_now()
    current_pool_assignment.status = final_status
    current_pool_assignment.acted_at = now
    for assignment in request.approver_pool:
        if assignment is current_pool_assignment:
            continue
        if assignment.status == SpecialRequestStatus.PENDING.value:
            assignment.status = final_status

    request.approver_id = approver_id
    request.status = final_status
    request = await repository.save(request)

    decision = "approved" if payload.response == "APPROVE" else "rejected"
    await _notify_user(
        session,
        recipient_id=request.user_id,
        sender_id=approver_id,
        content=(
            f"Your official business request for {request.date.isoformat()} "
            f"has been {decision}."
        ),
        url="/official-business",
    )
    return request


async def cancel_official_business_request(
    session: AsyncSession,
    request_id: int,
    current_user: User,
    *,
    current_user_is_staff: bool,
) -> OfficialBusinessRequest:
    repository = OfficialBusinessRequestRepository(session)
    request = await repository.get_by_id(request_id)
    if request is None:
        raise NotFoundError("Official business request not found.")
    if request.user_id != current_user.id and not current_user_is_staff:
        raise PermissionDeniedError("You are not allowed to cancel this official business request.")
    if request.status != SpecialRequestStatus.PENDING.value:
        raise ConflictError("Only pending official business requests can be cancelled.")

    now = utc_now()
    request.status = SpecialRequestStatus.CANCELLED.value
    for assignment in request.approver_pool:
        if assignment.status == SpecialRequestStatus.PENDING.value:
            assignment.status = SpecialRequestStatus.CANCELLED.value
            assignment.acted_at = now
    return await repository.save(request)


async def escalate_official_business_request(
    session: AsyncSession,
    request_id: int,
    current_user: User,
) -> OfficialBusinessRequest:
    repository = OfficialBusinessRequestRepository(session)
    request = await repository.get_by_id(request_id)
    if request is None:
        raise NotFoundError("Official business request not found.")
    if request.status != SpecialRequestStatus.PENDING.value:
        raise ConflictError("Only pending official business requests can be escalated.")
    if request.escalated_to_backup_at is not None:
        raise ConflictError("Official business request is already escalated to the backup approver.")

    requester = request.user
    if requester is None:
        raise NotFoundError("Request owner not found.")
    backup_approver = await _get_backup_approver(session, requester)
    if backup_approver is None:
        raise ConflictError("No Level 2 backup approver is configured for this request.")
    if backup_approver.id == request.user_id:
        raise ConflictError("Level 2 approver cannot be the same as the requester.")
    if request.approver_id == backup_approver.id:
        raise ConflictError("Request is already assigned to the backup approver.")

    now = utc_now()
    for assignment in request.approver_pool:
        if assignment.status == SpecialRequestStatus.PENDING.value:
            assignment.status = SpecialRequestStatus.CANCELLED.value
            assignment.acted_at = now

    backup_assignment = next(
        (
            assignment
            for assignment in request.approver_pool
            if assignment.approver_id == backup_approver.id
        ),
        None,
    )
    if backup_assignment is None:
        request.approver_pool.append(
            OfficialBusinessRequestApprover(
                approver_id=backup_approver.id,
                status=SpecialRequestStatus.PENDING.value,
            )
        )
    else:
        backup_assignment.status = SpecialRequestStatus.PENDING.value
        backup_assignment.acted_at = None

    request.approver_id = backup_approver.id
    request.escalated_to_backup_at = now
    request.escalated_to_backup_by_id = current_user.id
    request = await repository.save(request)

    requester_name = _display_user_name(request.user)
    await _notify_user(
        session,
        recipient_id=backup_approver.id,
        sender_id=current_user.id,
        content=(
            f"{requester_name}'s official business request for {request.date.isoformat()} "
            "was escalated to you as backup approver."
        ),
        url="/requests/inbox",
    )
    return request


async def list_certificate_attendance_requests(
    session: AsyncSession,
    *,
    current_user_id: UUID,
    current_user_is_staff: bool,
    scope: SpecialRequestScope | None = None,
    user_id: UUID | None = None,
    approver_id: UUID | None = None,
    year: int | None = None,
    month: int | None = None,
    status: str | None = None,
    department_id: int | None = None,
    query: str | None = None,
) -> list[CertificateAttendanceRequest]:
    scope_label, selected_user_id, selected_approver_id = _resolve_scope(
        scope=scope,
        current_user_id=current_user_id,
        current_user_is_staff=current_user_is_staff,
        user_id=user_id,
        approver_id=approver_id,
    )
    return await CertificateAttendanceRequestRepository(session).list(
        user_id=selected_user_id if scope_label != "approvals" else None,
        approver_id=selected_approver_id if scope_label != "mine" else None,
        year=year,
        month=month,
        status=status,
        department_id=department_id,
        query=query,
    )


async def create_certificate_attendance_request(
    session: AsyncSession,
    current_user: User,
    payload: CertificateAttendanceRequestCreateRequest,
) -> CertificateAttendanceRequest:
    user = await UserRepository(session).get_by_id(payload.user_id)
    if user is None:
        raise NotFoundError("User not found.")

    await _ensure_no_conflicting_active_requests(
        session,
        user_id=payload.user_id,
        selected_date=payload.date,
    )

    approvers = await _build_approval_pool(session, user)
    if not approvers:
        raise NotFoundError("No Level 1 approver is configured for this user.")

    first_approver = approvers[0]
    request = CertificateAttendanceRequest(
        user_id=payload.user_id,
        approver_id=first_approver.id,
        info=payload.info,
        date=payload.date,
        time=payload.time,
        punch=payload.punch,
        status=SpecialRequestStatus.PENDING.value,
        approver_pool=[
            CertificateAttendanceRequestApprover(
                approver_id=approver.id,
                status=SpecialRequestStatus.PENDING.value,
            )
            for approver in approvers
        ],
    )
    request = await CertificateAttendanceRequestRepository(session).create(request)

    requester_name = _display_user_name(user)
    for approver in approvers:
        await _notify_user(
            session,
            recipient_id=approver.id,
            sender_id=current_user.id,
            content=(
                f"{requester_name} filed a certificate of attendance request "
                f"for {request.date.isoformat()}."
            ),
            url="/requests/inbox",
        )
    return request


async def respond_to_certificate_attendance_request(
    session: AsyncSession,
    request_id: int,
    approver_id: UUID,
    payload: SpecialRequestRespondRequest,
) -> CertificateAttendanceRequest:
    repository = CertificateAttendanceRequestRepository(session)
    request = await repository.get_by_id(request_id)
    if request is None:
        raise NotFoundError("Certificate of attendance request not found.")
    if request.user_id == approver_id:
        raise PermissionDeniedError(
            "You cannot review your own certificate of attendance request."
        )

    current_pool_assignment = next(
        (
            assignment
            for assignment in request.approver_pool
            if assignment.approver_id == approver_id
        ),
        None,
    )
    if current_pool_assignment is None:
        raise PermissionDeniedError("You do not have permission to respond to this request.")
    if current_pool_assignment.status != SpecialRequestStatus.PENDING.value:
        raise ConflictError(
            "This certificate of attendance request has already been decided by you."
        )
    if request.status != SpecialRequestStatus.PENDING.value:
        raise ConflictError("This certificate of attendance request has already been decided.")

    final_status = (
        SpecialRequestStatus.APPROVED.value
        if payload.response == "APPROVE"
        else SpecialRequestStatus.REJECTED.value
    )
    now = utc_now()
    current_pool_assignment.status = final_status
    current_pool_assignment.acted_at = now
    for assignment in request.approver_pool:
        if assignment is current_pool_assignment:
            continue
        if assignment.status == SpecialRequestStatus.PENDING.value:
            assignment.status = final_status

    request.approver_id = approver_id
    request.status = final_status
    if payload.response == "APPROVE":
        attendance_repository = AttendanceRecordRepository(session)
        attendance_timestamp = _certificate_attendance_timestamp(request)
        duplicate = await attendance_repository.get_duplicate(
            request.user_id,
            attendance_timestamp,
            request.punch,
        )
        if duplicate is not None:
            raise ConflictError("Attendance record already exists.")
        session.add(
            AttendanceRecord(
                user_id=request.user_id,
                timestamp=attendance_timestamp,
                punch=request.punch,
            )
        )
    request = await repository.save(request)

    decision = "approved" if payload.response == "APPROVE" else "rejected"
    await _notify_user(
        session,
        recipient_id=request.user_id,
        sender_id=approver_id,
        content=(
            f"Your certificate of attendance request for {request.date.isoformat()} "
            f"has been {decision}."
        ),
        url="/certificate-of-attendance",
    )
    return request


async def cancel_certificate_attendance_request(
    session: AsyncSession,
    request_id: int,
    current_user: User,
    *,
    current_user_is_staff: bool,
) -> CertificateAttendanceRequest:
    repository = CertificateAttendanceRequestRepository(session)
    request = await repository.get_by_id(request_id)
    if request is None:
        raise NotFoundError("Certificate of attendance request not found.")
    if request.user_id != current_user.id and not current_user_is_staff:
        raise PermissionDeniedError(
            "You are not allowed to cancel this certificate of attendance request."
        )
    if request.status != SpecialRequestStatus.PENDING.value:
        raise ConflictError("Only pending certificate of attendance requests can be cancelled.")

    now = utc_now()
    request.status = SpecialRequestStatus.CANCELLED.value
    for assignment in request.approver_pool:
        if assignment.status == SpecialRequestStatus.PENDING.value:
            assignment.status = SpecialRequestStatus.CANCELLED.value
            assignment.acted_at = now
    return await repository.save(request)


async def escalate_certificate_attendance_request(
    session: AsyncSession,
    request_id: int,
    current_user: User,
) -> CertificateAttendanceRequest:
    repository = CertificateAttendanceRequestRepository(session)
    request = await repository.get_by_id(request_id)
    if request is None:
        raise NotFoundError("Certificate of attendance request not found.")
    if request.status != SpecialRequestStatus.PENDING.value:
        raise ConflictError("Only pending certificate of attendance requests can be escalated.")
    if request.escalated_to_backup_at is not None:
        raise ConflictError(
            "Certificate of attendance request is already escalated to the backup approver."
        )

    requester = request.user
    if requester is None:
        raise NotFoundError("Request owner not found.")
    backup_approver = await _get_backup_approver(session, requester)
    if backup_approver is None:
        raise ConflictError("No Level 2 backup approver is configured for this request.")
    if backup_approver.id == request.user_id:
        raise ConflictError("Level 2 approver cannot be the same as the requester.")
    if request.approver_id == backup_approver.id:
        raise ConflictError("Request is already assigned to the backup approver.")

    now = utc_now()
    for assignment in request.approver_pool:
        if assignment.status == SpecialRequestStatus.PENDING.value:
            assignment.status = SpecialRequestStatus.CANCELLED.value
            assignment.acted_at = now

    backup_assignment = next(
        (
            assignment
            for assignment in request.approver_pool
            if assignment.approver_id == backup_approver.id
        ),
        None,
    )
    if backup_assignment is None:
        request.approver_pool.append(
            CertificateAttendanceRequestApprover(
                approver_id=backup_approver.id,
                status=SpecialRequestStatus.PENDING.value,
            )
        )
    else:
        backup_assignment.status = SpecialRequestStatus.PENDING.value
        backup_assignment.acted_at = None

    request.approver_id = backup_approver.id
    request.escalated_to_backup_at = now
    request.escalated_to_backup_by_id = current_user.id
    request = await repository.save(request)

    requester_name = _display_user_name(request.user)
    await _notify_user(
        session,
        recipient_id=backup_approver.id,
        sender_id=current_user.id,
        content=(
            f"{requester_name}'s certificate of attendance request for "
            f"{request.date.isoformat()} was escalated to you as backup approver."
        ),
        url="/requests/inbox",
    )
    return request
