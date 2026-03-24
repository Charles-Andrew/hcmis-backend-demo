from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, require_staff_user
from app.models.attendance import (
    AttendanceRecord,
    DailyShiftRecord,
    DailyShiftSchedule,
    Holiday,
    OvertimeRequest,
    Shift,
    ShiftSwapRequest,
)
from app.models.department import Department
from app.models.user import User
from app.schemas.attendance import (
    AttendanceRecordCreateRequest,
    AttendanceRecordRead,
    AttendanceRecordUpdateRequest,
    AttendanceSummaryRead,
    DepartmentScheduleUpdateRequest,
    DailyShiftRecordCreateRequest,
    DailyShiftRecordRead,
    DailyShiftScheduleCreateRequest,
    DailyShiftScheduleRead,
    HolidayCreateRequest,
    HolidayRead,
    HolidayUpdateRequest,
    OvertimeRequestCreateRequest,
    OvertimeRequestRead,
    OvertimeRequestRespondRequest,
    ShiftCreateRequest,
    ShiftRead,
    ShiftSwapRequestCreateRequest,
    ShiftSwapRequestRead,
    ShiftSwapRequestRespondRequest,
    ShiftUpdateRequest,
)
from app.schemas.department import DepartmentRead
from app.services.attendance import (
    create_attendance_record,
    create_daily_shift_record,
    create_daily_shift_schedule,
    create_holiday,
    create_overtime_request,
    create_shift,
    create_shift_swap_request,
    delete_attendance_record,
    delete_holiday,
    delete_overtime_request,
    delete_shift,
    delete_daily_shift_schedule,
    delete_shift_swap_request,
    get_attendance_summary,
    list_attendance_records,
    list_daily_shift_records,
    list_daily_shift_schedules,
    list_holidays,
    list_overtime_requests,
    list_shift_swap_requests,
    list_shifts,
    respond_to_overtime_request,
    respond_to_shift_swap_request,
    sync_device_attendance,
    update_attendance_record,
    update_department_schedule,
    update_holiday,
    update_shift,
)

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("/shifts", response_model=list[ShiftRead])
async def get_shifts(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[Shift]:
    return await list_shifts(session)


@router.post("/shifts", response_model=ShiftRead, status_code=status.HTTP_201_CREATED)
async def post_shift(
    payload: ShiftCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Shift:
    return await create_shift(session, payload)


@router.patch("/shifts/{shift_id}", response_model=ShiftRead)
async def patch_shift(
    shift_id: int,
    payload: ShiftUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Shift:
    return await update_shift(session, shift_id, payload)


@router.delete("/shifts/{shift_id}", response_model=str)
async def remove_shift(
    shift_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> str:
    return await delete_shift(session, shift_id)


@router.patch("/departments/{department_id}/schedule", response_model=DepartmentRead)
async def patch_department_schedule(
    department_id: int,
    payload: DepartmentScheduleUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Department:
    return await update_department_schedule(session, department_id, payload)


@router.get("/schedules", response_model=list[DailyShiftScheduleRead])
async def get_daily_shift_schedules(
    department_id: int = Query(...),
    year: int = Query(...),
    month: int = Query(...),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[DailyShiftSchedule]:
    return await list_daily_shift_schedules(session, department_id, year, month)


@router.post("/schedules", response_model=DailyShiftScheduleRead, status_code=status.HTTP_201_CREATED)
async def post_daily_shift_schedule(
    payload: DailyShiftScheduleCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> DailyShiftSchedule:
    return await create_daily_shift_schedule(session, payload)


@router.delete("/schedules/{schedule_id}", response_model=None)
async def remove_daily_shift_schedule(
    schedule_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_daily_shift_schedule(session, schedule_id)


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


@router.get("/daily-shifts", response_model=list[DailyShiftRecordRead])
async def get_daily_shift_records(
    department_id: int = Query(...),
    year: int = Query(...),
    month: int = Query(...),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[DailyShiftRecord]:
    return await list_daily_shift_records(session, department_id, year, month)


@router.post("/daily-shifts", response_model=DailyShiftRecordRead, status_code=status.HTTP_201_CREATED)
async def post_daily_shift_record(
    payload: DailyShiftRecordCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> DailyShiftRecord:
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
    user_id: int | None = Query(default=None),
    approver_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[OvertimeRequest]:
    return await list_overtime_requests(session, user_id=user_id, approver_id=approver_id)


@router.post("/overtime", response_model=OvertimeRequestRead, status_code=status.HTTP_201_CREATED)
async def post_overtime_request(
    payload: OvertimeRequestCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OvertimeRequest:
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
