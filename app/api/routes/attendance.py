from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, require_staff_user
from app.core.capabilities import is_staff_user
from app.core.exceptions import PermissionDeniedError
from app.models.attendance import (
    AttendanceRecord,
    DepartmentRosterDay,
    EmployeeShiftAssignment,
    Holiday,
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
from app.services.attendance import (
    create_attendance_record,
    create_daily_shift_record,
    create_employee_shift_assignment,
    create_holiday,
    copy_previous_month_employee_shift_assignments,
    create_overtime_request,
    generate_month_employee_shift_assignments,
    create_shift_template,
    create_shift_swap_request,
    delete_attendance_record,
    delete_holiday,
    delete_overtime_request,
    delete_shift_template,
    delete_employee_shift_assignment,
    delete_shift_swap_request,
    get_attendance_summary,
    list_attendance_records,
    list_daily_shift_records,
    list_employee_shift_assignments,
    list_holidays,
    list_overtime_requests,
    list_shift_swap_requests,
    list_shift_templates,
    get_department_schedule,
    respond_to_overtime_request,
    respond_to_shift_swap_request,
    sync_device_attendance,
    update_attendance_record,
    update_department_schedule,
    update_employee_shift_assignment,
    update_holiday,
    update_shift_template,
)

router = APIRouter(prefix="/attendance", tags=["attendance"])


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
    user_id: int = Query(...),
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
    user_id: int | None = Query(default=None),
    approver_id: int | None = Query(default=None),
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


@router.post("/overtime", response_model=OvertimeRequestRead, status_code=status.HTTP_201_CREATED)
async def post_overtime_request(
    payload: OvertimeRequestCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OvertimeRequest:
    is_staff = is_staff_user(current_user)
    if payload.user_id != current_user.id and not is_staff:
        raise PermissionDeniedError("You do not have permission to create this overtime request.")
    return await create_overtime_request(session, payload)


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
    user_id: int | None = Query(default=None),
    approver_id: int | None = Query(default=None),
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
    user_id: int,
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
    await sync_device_attendance(session, device_user_id, timestamp, punch)
    return "OK"
