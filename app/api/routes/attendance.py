from uuid import UUID

from datetime import UTC, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db_session,
    require_bridge_agent,
    require_staff_user,
)
from app.core.capabilities import is_staff_user
from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models.attendance import (
    AttendanceRecord,
    DepartmentRosterDay,
    EmployeeShiftAssignment,
    Holiday,
    OvertimeApprover,
    OvertimeRequest,
    ShiftTemplate,
    ShiftSwapRequest,
)
from app.models.department import Department
from app.models.user import User
from app.schemas.attendance import (
    AttendanceRecordCreateRequest,
    AttendanceRecordRead,
    AttendanceRecordUpdateRequest,
    AttendanceSummaryRead,
    BridgeBiometricSnapshotRequest,
    BridgeBiometricSnapshotResponse,
    BridgeCommandScanUsersCreateRequest,
    BridgeCommandAckRequest,
    BridgeCommandRead,
    BridgeCommandsResponse,
    BridgeCommandSyncUsersCreateRequest,
    BridgeHeartbeatRequest,
    BridgeHeartbeatResponse,
    BridgeLogsRequest,
    BridgeLogsResponse,
    BridgeReconcileResponse,
    BridgeReconcileRow,
    BridgeUserRead,
    BridgeUsersResponse,
    DepartmentShiftPolicyRead,
    DepartmentScheduleUpdateRequest,
    DepartmentRosterDayCreateRequest,
    DepartmentRosterDayRead,
    EmployeeShiftAssignmentCreateRequest,
    EmployeeShiftAssignmentCopyPreviousMonthRequest,
    EmployeeShiftAssignmentCopyPreviousMonthResponse,
    EmployeeShiftAssignmentGenerateMonthRequest,
    EmployeeShiftAssignmentGenerateMonthResponse,
    EmployeeShiftAssignmentRead,
    EmployeeShiftAssignmentUpdateRequest,
    HolidayCreateRequest,
    HolidayRead,
    HolidayUpdateRequest,
    OvertimeApproverAssignmentRead,
    OvertimeApproverRead,
    OvertimeApproverUpsertRequest,
    OvertimeRequestCreateRequest,
    OvertimeRequestRead,
    OvertimeRequestScope,
    OvertimeRequestRespondRequest,
    ShiftTemplateCreateRequest,
    ShiftTemplateRead,
    ShiftSwapRequestCreateRequest,
    ShiftSwapRequestRead,
    ShiftSwapRequestRespondRequest,
    ShiftTemplateUpdateRequest,
)
from app.core.time import utc_now
from app.repositories.attendance import BridgeUserSnapshotRepository
from app.repositories.users import UserRepository
from app.services.bridge_commands import (
    ack_command,
    dispatch_commands,
    list_site_device_commands,
    queue_scan_users_command,
    queue_sync_users_command,
)
from app.services.attendance import (
    copy_previous_month_employee_shift_assignments,
    create_attendance_record,
    create_daily_shift_record,
    create_employee_shift_assignment,
    create_holiday,
    create_overtime_request,
    generate_month_employee_shift_assignments,
    get_my_overtime_approver_assignment,
    create_shift_template,
    create_shift_swap_request,
    delete_attendance_record,
    delete_holiday,
    delete_overtime_approver,
    delete_overtime_request,
    delete_shift_template,
    delete_employee_shift_assignment,
    delete_shift_swap_request,
    get_attendance_summary,
    list_attendance_records,
    list_daily_shift_records,
    list_employee_shift_assignments,
    list_holidays,
    list_overtime_approvers,
    list_overtime_requests,
    list_shift_swap_requests,
    list_shift_templates,
    get_department_schedule,
    respond_to_overtime_request,
    respond_to_shift_swap_request,
    sync_device_attendance,
    upsert_overtime_approver,
    update_attendance_record,
    update_department_schedule,
    update_employee_shift_assignment,
    update_holiday,
    update_shift_template,
)

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/bridge/commands/sync-users", response_model=BridgeCommandRead, status_code=status.HTTP_201_CREATED)
async def post_bridge_sync_users_command(
    payload: BridgeCommandSyncUsersCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> BridgeCommandRead:
    return await queue_sync_users_command(
        session,
        payload=payload,
        requested_by_user_id=current_user.id,
    )


@router.post("/bridge/commands/scan-users", response_model=BridgeCommandRead, status_code=status.HTTP_201_CREATED)
async def post_bridge_scan_users_command(
    payload: BridgeCommandScanUsersCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> BridgeCommandRead:
    return await queue_scan_users_command(
        session,
        payload=payload,
        requested_by_user_id=current_user.id,
    )


@router.get("/bridge/commands", response_model=BridgeCommandsResponse)
async def get_bridge_commands(
    site_code: str = Query(..., min_length=1),
    device_id: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_bridge_agent),
) -> BridgeCommandsResponse:
    commands = await dispatch_commands(
        session,
        site_code=site_code,
        device_id=device_id,
        limit=limit,
    )
    return BridgeCommandsResponse(commands=commands)


@router.post("/bridge/commands/{command_id}/ack", response_model=BridgeCommandRead)
async def post_bridge_command_ack(
    command_id: int,
    payload: BridgeCommandAckRequest,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_bridge_agent),
) -> BridgeCommandRead:
    return await ack_command(
        session,
        command_id=command_id,
        payload=payload,
    )


@router.get("/bridge/commands/history", response_model=BridgeCommandsResponse)
async def get_bridge_commands_history(
    site_code: str = Query(..., min_length=1),
    device_id: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> BridgeCommandsResponse:
    _ = current_user
    commands = await list_site_device_commands(
        session,
        site_code=site_code,
        device_id=device_id,
        limit=limit,
    )
    return BridgeCommandsResponse(commands=commands)


@router.get("/bridge/users", response_model=BridgeUsersResponse)
async def get_bridge_users(
    site_code: str = Query(..., min_length=1),
    device_id: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_bridge_agent),
) -> BridgeUsersResponse:
    # site_code/device_id are required for parity with bridge endpoint contract
    del site_code, device_id
    users = await UserRepository(session).list(include_superusers=False)
    response_users = [
        BridgeUserRead(
            user_id=user.id,
            biometric_uid=user.biometric_uid,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
        )
        for user in users
        if user.biometric_uid is not None
    ]
    return BridgeUsersResponse(users=response_users)


def _bridge_punch_to_attendance(punch: int | None) -> Literal["IN", "OUT"]:
    if punch in {1, 3, 5, 7}:
        return "OUT"
    return "IN"


def _bridge_device_timezone() -> ZoneInfo:
    timezone_name = settings.bridge_device_timezone.strip() or "Asia/Manila"
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid BRIDGE_DEVICE_TIMEZONE: {timezone_name}",
        ) from exc


def _normalize_bridge_timestamp(value: datetime, *, device_timezone: ZoneInfo) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=device_timezone).astimezone(UTC)
    return value.astimezone(UTC)


@router.post("/bridge/logs", response_model=BridgeLogsResponse)
async def post_bridge_logs(
    payload: BridgeLogsRequest,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_bridge_agent),
) -> BridgeLogsResponse:
    device_timezone = _bridge_device_timezone()
    accepted = 0
    duplicates = 0
    unknown_users = 0
    failed = 0
    for event in payload.events:
        device_user_id_raw = str(event.device_user_id).strip()
        if not device_user_id_raw.isdigit():
            failed += 1
            continue
        try:
            await sync_device_attendance(
                session,
                device_user_id=int(device_user_id_raw),
                timestamp=_normalize_bridge_timestamp(
                    event.timestamp,
                    device_timezone=device_timezone,
                ),
                punch=_bridge_punch_to_attendance(event.punch),
                raw_event_id=event.raw_event_id,
            )
            accepted += 1
        except ConflictError:
            duplicates += 1
        except NotFoundError:
            unknown_users += 1
        except Exception:
            failed += 1
    return BridgeLogsResponse(
        accepted=accepted,
        duplicates=duplicates,
        unknown_users=unknown_users,
        failed=failed,
    )


@router.post("/bridge/heartbeat", response_model=BridgeHeartbeatResponse)
async def post_bridge_heartbeat(
    payload: BridgeHeartbeatRequest,
    _: None = Depends(require_bridge_agent),
) -> BridgeHeartbeatResponse:
    del payload
    return BridgeHeartbeatResponse(status="ok")


@router.post("/bridge/users/snapshot", response_model=BridgeBiometricSnapshotResponse)
async def post_bridge_users_snapshot(
    payload: BridgeBiometricSnapshotRequest,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_bridge_agent),
) -> BridgeBiometricSnapshotResponse:
    stored_users = await BridgeUserSnapshotRepository(session).replace_for_site_device(
        site_code=payload.site_code,
        device_id=payload.device_id,
        scanned_at=payload.scanned_at or utc_now(),
        users=[user.model_dump() for user in payload.users],
    )
    return BridgeBiometricSnapshotResponse(status="ok", stored_users=stored_users)


@router.get("/bridge/reconcile", response_model=BridgeReconcileResponse)
async def get_bridge_reconcile(
    site_code: str = Query(..., min_length=1),
    device_id: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> BridgeReconcileResponse:
    _ = current_user
    app_users = await UserRepository(session).list(include_superusers=True)
    biometric_users = await BridgeUserSnapshotRepository(session).list_for_site_device(
        site_code=site_code,
        device_id=device_id,
    )

    merged: dict[str, BridgeReconcileRow] = {}
    for app_user in app_users:
        app_name = " ".join(
            part
            for part in [app_user.first_name or "", app_user.last_name or ""]
            if part
        ).strip() or app_user.email
        if app_user.biometric_uid is None:
            key = f"app:{app_user.id}"
            merged[key] = BridgeReconcileRow(
                key=key,
                biometric_uid=None,
                app_user_id=app_user.id,
                app_name=app_name,
                biometric_name=None,
                present_in_app=True,
                present_in_biometric=False,
            )
            continue

        key = f"uid:{app_user.biometric_uid}"
        merged[key] = BridgeReconcileRow(
            key=key,
            biometric_uid=app_user.biometric_uid,
            app_user_id=app_user.id,
            app_name=app_name,
            biometric_name=None,
            present_in_app=True,
            present_in_biometric=False,
        )

    for biometric_user in biometric_users:
        key = f"uid:{biometric_user.biometric_uid}"
        existing = merged.get(key)
        if existing is None:
            merged[key] = BridgeReconcileRow(
                key=key,
                biometric_uid=biometric_user.biometric_uid,
                app_user_id=None,
                app_name=None,
                biometric_name=biometric_user.name,
                present_in_app=False,
                present_in_biometric=True,
            )
            continue
        existing.biometric_name = biometric_user.name
        existing.present_in_biometric = True

    rows = list(merged.values())
    rows.sort(
        key=lambda row: (
            row.biometric_uid is None,
            row.biometric_uid if row.biometric_uid is not None else 0,
            (row.app_name or row.biometric_name or "").lower(),
        )
    )
    return BridgeReconcileResponse(site_code=site_code, device_id=device_id, rows=rows)


@router.get("/shifts", response_model=list[ShiftTemplateRead], include_in_schema=False)
@router.get("/shift-templates", response_model=list[ShiftTemplateRead])
async def get_shift_templates(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[ShiftTemplate]:
    return await list_shift_templates(session)


@router.post("/shifts", response_model=ShiftTemplateRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/shift-templates", response_model=ShiftTemplateRead, status_code=status.HTTP_201_CREATED)
async def post_shift_template(
    payload: ShiftTemplateCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> ShiftTemplate:
    return await create_shift_template(session, payload)


@router.patch("/shifts/{shift_id}", response_model=ShiftTemplateRead, include_in_schema=False)
@router.patch("/shift-templates/{shift_id}", response_model=ShiftTemplateRead)
async def patch_shift_template(
    shift_id: int,
    payload: ShiftTemplateUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> ShiftTemplate:
    return await update_shift_template(session, shift_id, payload)


@router.delete("/shifts/{shift_id}", response_model=str, include_in_schema=False)
@router.delete("/shift-templates/{shift_id}", response_model=str)
async def remove_shift_template(
    shift_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> str:
    return await delete_shift_template(session, shift_id)


@router.patch(
    "/departments/{department_id}/schedule",
    response_model=DepartmentShiftPolicyRead,
    include_in_schema=False,
)
@router.patch(
    "/departments/{department_id}/shift-policy",
    response_model=DepartmentShiftPolicyRead,
)
async def patch_department_schedule(
    department_id: int,
    payload: DepartmentScheduleUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Department:
    return await update_department_schedule(session, department_id, payload)


@router.get(
    "/departments/{department_id}/schedule",
    response_model=DepartmentShiftPolicyRead,
    include_in_schema=False,
)
@router.get("/departments/{department_id}/shift-policy", response_model=DepartmentShiftPolicyRead)
async def read_department_schedule(
    department_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Department:
    return await get_department_schedule(session, department_id)


@router.get("/schedules", response_model=list[EmployeeShiftAssignmentRead], include_in_schema=False)
@router.get("/shift-assignments", response_model=list[EmployeeShiftAssignmentRead])
async def get_employee_shift_assignments(
    department_id: int = Query(...),
    year: int = Query(...),
    month: int = Query(...),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[EmployeeShiftAssignment]:
    return await list_employee_shift_assignments(session, department_id, year, month)


@router.post("/schedules", response_model=EmployeeShiftAssignmentRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/shift-assignments", response_model=EmployeeShiftAssignmentRead, status_code=status.HTTP_201_CREATED)
async def post_employee_shift_assignment(
    payload: EmployeeShiftAssignmentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> EmployeeShiftAssignment:
    return await create_employee_shift_assignment(session, payload)


@router.post(
    "/shift-assignments/copy-previous-month",
    response_model=EmployeeShiftAssignmentCopyPreviousMonthResponse,
)
async def copy_previous_month_shift_assignments(
    payload: EmployeeShiftAssignmentCopyPreviousMonthRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> EmployeeShiftAssignmentCopyPreviousMonthResponse:
    return await copy_previous_month_employee_shift_assignments(session, payload)


@router.post(
    "/shift-assignments/generate-month",
    response_model=EmployeeShiftAssignmentGenerateMonthResponse,
)
async def generate_month_shift_assignments(
    payload: EmployeeShiftAssignmentGenerateMonthRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> EmployeeShiftAssignmentGenerateMonthResponse:
    return await generate_month_employee_shift_assignments(session, payload)


@router.patch("/schedules/{schedule_id}", response_model=EmployeeShiftAssignmentRead, include_in_schema=False)
@router.patch("/shift-assignments/{schedule_id}", response_model=EmployeeShiftAssignmentRead)
async def patch_employee_shift_assignment(
    schedule_id: int,
    payload: EmployeeShiftAssignmentUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> EmployeeShiftAssignment:
    return await update_employee_shift_assignment(session, schedule_id, payload)


@router.delete("/schedules/{schedule_id}", response_model=None, include_in_schema=False)
@router.delete("/shift-assignments/{schedule_id}", response_model=None)
async def remove_employee_shift_assignment(
    schedule_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_employee_shift_assignment(session, schedule_id)


@router.get("/records", response_model=list[AttendanceRecordRead])
async def get_records(
    user_id: UUID = Query(...),
    year: int = Query(...),
    month: int = Query(...),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[AttendanceRecord]:
    return await list_attendance_records(session, user_id, year, month)


@router.post("/records", response_model=AttendanceRecordRead, status_code=status.HTTP_201_CREATED)
async def post_record(
    payload: AttendanceRecordCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> AttendanceRecord:
    return await create_attendance_record(session, payload)


@router.patch("/records/{record_id}", response_model=AttendanceRecordRead)
async def patch_record(
    record_id: int,
    payload: AttendanceRecordUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> AttendanceRecord:
    return await update_attendance_record(session, record_id, payload)


@router.delete("/records/{record_id}", response_model=None)
async def remove_record(
    record_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_attendance_record(session, record_id)


@router.get("/daily-shifts", response_model=list[DepartmentRosterDayRead])
async def get_department_roster_days(
    department_id: int = Query(...),
    year: int = Query(...),
    month: int = Query(...),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[DepartmentRosterDay]:
    return await list_daily_shift_records(session, department_id, year, month)


@router.post("/daily-shifts", response_model=DepartmentRosterDayRead, status_code=status.HTTP_201_CREATED)
async def post_department_roster_day(
    payload: DepartmentRosterDayCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> DepartmentRosterDay:
    return await create_daily_shift_record(session, payload)


@router.get("/holidays", response_model=list[HolidayRead])
async def get_holidays(
    year: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[Holiday]:
    return await list_holidays(session, year=year)


@router.post("/holidays", response_model=HolidayRead, status_code=status.HTTP_201_CREATED)
async def post_holiday(
    payload: HolidayCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Holiday:
    return await create_holiday(session, payload)


@router.patch("/holidays/{holiday_id}", response_model=HolidayRead)
async def patch_holiday(
    holiday_id: int,
    payload: HolidayUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Holiday:
    return await update_holiday(session, holiday_id, payload)


@router.delete("/holidays/{holiday_id}", response_model=str)
async def remove_holiday(
    holiday_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> str:
    return await delete_holiday(session, holiday_id)


@router.get("/overtime", response_model=list[OvertimeRequestRead])
async def get_overtime_requests(
    scope: OvertimeRequestScope | None = Query(default=None),
    user_id: UUID | None = Query(default=None),
    approver_id: UUID | None = Query(default=None),
    year: int | None = Query(default=None, ge=1900),
    month: int | None = Query(default=None, ge=1, le=12),
    status: str | None = Query(default=None, pattern="^(PEND|APP|REJ)$"),
    department_id: int | None = Query(default=None),
    q: str | None = Query(default=None, alias="q"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[OvertimeRequest]:
    is_staff = is_staff_user(current_user)
    return await list_overtime_requests(
        session,
        current_user_id=current_user.id,
        current_user_is_staff=is_staff,
        scope=scope,
        user_id=user_id,
        approver_id=approver_id,
        year=year,
        month=month,
        status=status,
        department_id=department_id,
        query=q,
    )


@router.get("/overtime-approvers", response_model=list[OvertimeApproverRead])
async def get_overtime_approvers(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[OvertimeApprover]:
    return await list_overtime_approvers(session)


@router.get("/overtime-approvers/me", response_model=OvertimeApproverAssignmentRead)
async def get_my_overtime_approver(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OvertimeApproverAssignmentRead:
    return await get_my_overtime_approver_assignment(session, current_user)


@router.put("/overtime-approvers/{department_id}", response_model=OvertimeApproverRead)
async def put_overtime_approver(
    department_id: int,
    payload: OvertimeApproverUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> OvertimeApprover:
    return await upsert_overtime_approver(session, department_id, payload)


@router.delete("/overtime-approvers/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_overtime_approver(
    department_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_overtime_approver(session, department_id)


@router.post("/overtime", response_model=OvertimeRequestRead, status_code=status.HTTP_201_CREATED)
async def post_overtime_request(
    payload: OvertimeRequestCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OvertimeRequest:
    is_staff = is_staff_user(current_user)
    if payload.user_id != current_user.id and not is_staff:
        raise PermissionDeniedError("You do not have permission to create this overtime request.")
    return await create_overtime_request(session, current_user, payload)


@router.post("/overtime/{overtime_id}/respond", response_model=OvertimeRequestRead)
async def post_respond_overtime(
    overtime_id: int,
    payload: OvertimeRequestRespondRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OvertimeRequest:
    return await respond_to_overtime_request(session, overtime_id, current_user.id, payload)


@router.delete("/overtime/{overtime_id}", response_model=None)
async def remove_overtime_request(
    overtime_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_overtime_request(session, overtime_id)


@router.get("/shift-swaps", response_model=list[ShiftSwapRequestRead])
async def get_shift_swaps(
    user_id: UUID | None = Query(default=None),
    approver_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ShiftSwapRequest]:
    return await list_shift_swap_requests(
        session, user_id=user_id, approver_id=approver_id
    )


@router.post("/shift-swaps", response_model=ShiftSwapRequestRead, status_code=status.HTTP_201_CREATED)
async def post_shift_swap(
    payload: ShiftSwapRequestCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ShiftSwapRequest:
    return await create_shift_swap_request(session, payload)


@router.post("/shift-swaps/{swap_id}/respond", response_model=ShiftSwapRequestRead)
async def post_respond_shift_swap(
    swap_id: int,
    payload: ShiftSwapRequestRespondRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ShiftSwapRequest:
    return await respond_to_shift_swap_request(session, swap_id, current_user.id, payload)


@router.delete("/shift-swaps/{swap_id}", response_model=None)
async def remove_shift_swap(
    swap_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_shift_swap_request(session, swap_id)


@router.get("/me/{year}/{month}", response_model=AttendanceSummaryRead)
async def get_my_attendance_summary(
    year: int,
    month: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AttendanceSummaryRead:
    return await get_attendance_summary(session, current_user.id, year, month)


@router.get("/users/{user_id}/{year}/{month}", response_model=AttendanceSummaryRead)
async def get_user_attendance_summary(
    user_id: UUID,
    year: int,
    month: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> AttendanceSummaryRead:
    return await get_attendance_summary(session, user_id, year, month)


@router.get("/device/getrequest", response_class=PlainTextResponse)
async def get_device_request() -> str:
    return "OK"


@router.post("/device/cdata", response_class=PlainTextResponse)
async def post_device_cdata(
    device_user_id: int = Query(...),
    timestamp: datetime = Query(...),
    punch: Literal["IN", "OUT"] = Query(...),
    session: AsyncSession = Depends(get_db_session),
) -> str:
    await sync_device_attendance(
        session,
        device_user_id,
        _normalize_bridge_timestamp(
            timestamp,
            device_timezone=_bridge_device_timezone(),
        ),
        punch,
    )
    return "OK"
