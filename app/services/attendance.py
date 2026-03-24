from calendar import monthrange, day_name
from datetime import UTC, date, datetime
from typing import Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
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
from app.repositories.attendance import (
    AttendanceRecordRepository,
    DailyShiftRecordRepository,
    DailyShiftScheduleRepository,
    HolidayRepository,
    OvertimeRepository,
    ShiftRepository,
    ShiftSwapRepository,
)
from app.repositories.departments import DepartmentRepository
from app.repositories.users import UserRepository
from app.schemas.attendance import (
    AttendanceRecordRead,
    AttendanceRecordCreateRequest,
    AttendanceRecordUpdateRequest,
    AttendanceSummaryDayRead,
    AttendanceSummaryRead,
    DepartmentScheduleUpdateRequest,
    DailyShiftRecordCreateRequest,
    DailyShiftScheduleCreateRequest,
    DailyShiftScheduleRead,
    HolidayCreateRequest,
    HolidayRead,
    HolidayUpdateRequest,
    OvertimeRequestCreateRequest,
    OvertimeRequestRespondRequest,
    ShiftCreateRequest,
    ShiftSwapRequestCreateRequest,
    ShiftSwapRequestRespondRequest,
    ShiftUpdateRequest,
)


def _month_window(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    last_day = monthrange(year, month)[1]
    end = date(year, month, last_day)
    return start, end


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


async def _get_department_with_shifts(
    session: AsyncSession, department_id: int
) -> Department:
    statement = (
        select(Department)
        .options(selectinload(Department.shifts))
        .where(Department.id == department_id)
    )
    result = await session.execute(statement)
    department = result.scalar_one_or_none()
    if department is None:
        raise NotFoundError("Department not found.")
    return department


async def list_shifts(session: AsyncSession) -> list[Shift]:
    return await ShiftRepository(session).list()


async def create_shift(session: AsyncSession, payload: ShiftCreateRequest) -> Shift:
    repository = ShiftRepository(session)
    existing = await repository.get_by_identity(
        payload.description,
        payload.start_time,
        payload.end_time,
        payload.start_time_2,
        payload.end_time_2,
    )
    if existing is not None:
        raise ConflictError("A shift with the same times already exists.")

    shift = Shift(
        description=payload.description,
        start_time=payload.start_time,
        end_time=payload.end_time,
        start_time_2=payload.start_time_2,
        end_time_2=payload.end_time_2,
        is_active=payload.is_active,
    )
    return await repository.create(shift)


async def update_shift(
    session: AsyncSession, shift_id: int, payload: ShiftUpdateRequest
) -> Shift:
    repository = ShiftRepository(session)
    shift = await repository.get_by_id(shift_id)
    if shift is None:
        raise NotFoundError("Shift not found.")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(shift, key, value)
    return await repository.save(shift)


async def delete_shift(session: AsyncSession, shift_id: int) -> str:
    repository = ShiftRepository(session)
    shift = await repository.get_by_id(shift_id)
    if shift is None:
        raise NotFoundError("Shift not found.")
    description = shift.description
    try:
        await repository.delete(shift)
    except IntegrityError as exc:
        raise ConflictError("Shift cannot be deleted while it is in use.") from exc
    return description


async def update_department_schedule(
    session: AsyncSession, department_id: int, payload: DepartmentScheduleUpdateRequest
) -> Department:
    department_repository = DepartmentRepository(session)
    shift_repository = ShiftRepository(session)
    department = await department_repository.get_by_id(department_id)
    if department is None:
        raise NotFoundError("Department not found.")

    selected_shifts: list[Shift] = []
    for shift_id in dict.fromkeys(payload.shift_ids):
        shift = await shift_repository.get_by_id(shift_id)
        if shift is None:
            raise NotFoundError("Shift not found.")
        selected_shifts.append(shift)

    department.workweek = payload.workweek
    department.shifts.clear()
    department.shifts.extend(selected_shifts)
    await department_repository.save(department)
    return await _get_department_with_shifts(session, department_id)


async def get_department_schedule(
    session: AsyncSession, department_id: int
) -> Department:
    return await _get_department_with_shifts(session, department_id)


async def list_daily_shift_records(
    session: AsyncSession, department_id: int, year: int, month: int
) -> list[DailyShiftRecord]:
    return await DailyShiftRecordRepository(session).list_for_department_month(
        department_id, year, month
    )


async def create_daily_shift_record(
    session: AsyncSession, payload: DailyShiftRecordCreateRequest
) -> DailyShiftRecord:
    repository = DailyShiftRecordRepository(session)
    existing = await repository.get_by_department_date(
        payload.department_id, payload.date
    )
    if existing is not None:
        raise ConflictError("Daily shift record already exists for the selected date.")

    record = DailyShiftRecord(
        date=payload.date,
        department_id=payload.department_id,
        is_approved=payload.is_approved,
    )
    record = await repository.create(record)
    if payload.schedule_ids:
        schedule_repo = DailyShiftScheduleRepository(session)
        schedules = []
        for schedule_id in payload.schedule_ids:
            schedule = await schedule_repo.get_by_id(schedule_id)
            if schedule is None:
                raise NotFoundError("Daily shift schedule not found.")
            schedules.append(schedule)
        record.schedules.extend(schedules)
        record = await repository.save(record)
    return record


async def create_daily_shift_schedule(
    session: AsyncSession, payload: DailyShiftScheduleCreateRequest
) -> DailyShiftSchedule:
    user = await UserRepository(session).get_by_id(payload.user_id)
    if user is None:
        raise NotFoundError("User not found.")
    shift = await ShiftRepository(session).get_by_id(payload.shift_id)
    if shift is None:
        raise NotFoundError("Shift not found.")
    schedule = DailyShiftSchedule(
        date=payload.date,
        user_id=payload.user_id,
        shift_id=payload.shift_id,
    )
    return await DailyShiftScheduleRepository(session).create(schedule)


async def list_daily_shift_schedules(
    session: AsyncSession, department_id: int, year: int, month: int
) -> list[DailyShiftSchedule]:
    return await DailyShiftScheduleRepository(session).list_for_department_month(
        department_id, year, month
    )


async def delete_daily_shift_schedule(
    session: AsyncSession, schedule_id: int
) -> None:
    repository = DailyShiftScheduleRepository(session)
    schedule = await repository.get_by_id(schedule_id)
    if schedule is None:
        raise NotFoundError("Daily shift schedule not found.")
    await repository.delete(schedule)


async def list_attendance_records(
    session: AsyncSession, user_id: int, year: int, month: int
) -> list[AttendanceRecord]:
    start, end = _month_window(year, month)
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=UTC)
    end_dt = datetime.combine(end, datetime.max.time(), tzinfo=UTC)
    return await AttendanceRecordRepository(session).list_for_user_range(
        user_id, start_dt, end_dt
    )


async def create_attendance_record(
    session: AsyncSession, payload: AttendanceRecordCreateRequest
) -> AttendanceRecord:
    user = await UserRepository(session).get_by_id(payload.user_id)
    if user is None:
        raise NotFoundError("User not found.")
    repository = AttendanceRecordRepository(session)
    duplicate = await repository.get_duplicate(
        payload.user_id, _ensure_aware(payload.timestamp), payload.punch
    )
    if duplicate is not None:
        raise ConflictError("Attendance record already exists.")
    record = AttendanceRecord(
        user_id=payload.user_id,
        device_user_id=payload.device_user_id,
        timestamp=_ensure_aware(payload.timestamp),
        punch=payload.punch,
    )
    return await repository.create(record)


async def sync_device_attendance(
    session: AsyncSession,
    device_user_id: int,
    timestamp: datetime,
    punch: Literal["IN", "OUT"],
) -> AttendanceRecord:
    user_repository = UserRepository(session)
    users = await user_repository.list(include_superusers=True)
    user = next((candidate for candidate in users if candidate.biometric_uid == device_user_id), None)
    if user is None:
        raise NotFoundError("No user is mapped to the provided biometric UID.")
    return await create_attendance_record(
        session,
        AttendanceRecordCreateRequest(
            user_id=user.id,
            device_user_id=device_user_id,
            timestamp=timestamp,
            punch=punch,
        ),
    )


async def update_attendance_record(
    session: AsyncSession, record_id: int, payload: AttendanceRecordUpdateRequest
) -> AttendanceRecord:
    repository = AttendanceRecordRepository(session)
    record = await repository.get_by_id(record_id)
    if record is None:
        raise NotFoundError("Attendance record not found.")
    data = payload.model_dump(exclude_unset=True)
    if "timestamp" in data and data["timestamp"] is not None:
        record.timestamp = _ensure_aware(data["timestamp"])
    if "punch" in data and data["punch"] is not None:
        record.punch = data["punch"]
    return await repository.save(record)


async def delete_attendance_record(session: AsyncSession, record_id: int) -> None:
    repository = AttendanceRecordRepository(session)
    record = await repository.get_by_id(record_id)
    if record is None:
        raise NotFoundError("Attendance record not found.")
    await repository.delete(record)


async def list_holidays(session: AsyncSession, year: int | None = None) -> list[Holiday]:
    return await HolidayRepository(session).list(year=year)


async def create_holiday(session: AsyncSession, payload: HolidayCreateRequest) -> Holiday:
    holiday = Holiday(
        name=payload.name,
        day=payload.day,
        month=payload.month,
        year=payload.year,
        is_regular=payload.is_regular,
    )
    return await HolidayRepository(session).create(holiday)


async def update_holiday(
    session: AsyncSession, holiday_id: int, payload: HolidayUpdateRequest
) -> Holiday:
    repository = HolidayRepository(session)
    holiday = await repository.get_by_id(holiday_id)
    if holiday is None:
        raise NotFoundError("Holiday not found.")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(holiday, key, value)
    return await repository.save(holiday)


async def delete_holiday(session: AsyncSession, holiday_id: int) -> str:
    repository = HolidayRepository(session)
    holiday = await repository.get_by_id(holiday_id)
    if holiday is None:
        raise NotFoundError("Holiday not found.")
    holiday_label = f"{holiday.name} - {holiday.month}/{holiday.day}"
    await repository.delete(holiday)
    return holiday_label


async def list_overtime_requests(
    session: AsyncSession, user_id: int | None = None, approver_id: int | None = None
) -> list[OvertimeRequest]:
    repository = OvertimeRepository(session)
    if user_id is not None:
        return await repository.list_for_user(user_id)
    if approver_id is not None:
        return await repository.list_for_approver(approver_id)
    return []


async def create_overtime_request(
    session: AsyncSession, payload: OvertimeRequestCreateRequest
) -> OvertimeRequest:
    user = await UserRepository(session).get_by_id(payload.user_id)
    approver = await UserRepository(session).get_by_id(payload.approver_id)
    if user is None or approver is None:
        raise NotFoundError("User not found.")
    overtime = OvertimeRequest(
        user_id=payload.user_id,
        approver_id=payload.approver_id,
        info=payload.info,
        date=payload.date,
    )
    return await OvertimeRepository(session).create(overtime)


async def respond_to_overtime_request(
    session: AsyncSession,
    overtime_id: int,
    approver_id: int,
    payload: OvertimeRequestRespondRequest,
) -> OvertimeRequest:
    repository = OvertimeRepository(session)
    overtime = await repository.get_by_id(overtime_id)
    if overtime is None:
        raise NotFoundError("Overtime request not found.")
    if overtime.approver_id != approver_id:
        raise PermissionDeniedError("You do not have permission to respond to this request.")
    overtime.status = (
        OvertimeRequest.Status.APPROVED.value
        if payload.response == "APPROVE"
        else OvertimeRequest.Status.REJECTED.value
    )
    return await repository.save(overtime)


async def delete_overtime_request(session: AsyncSession, overtime_id: int) -> None:
    repository = OvertimeRepository(session)
    overtime = await repository.get_by_id(overtime_id)
    if overtime is None:
        raise NotFoundError("Overtime request not found.")
    await repository.delete(overtime)


async def list_shift_swap_requests(
    session: AsyncSession, user_id: int | None = None, approver_id: int | None = None
) -> list[ShiftSwapRequest]:
    repository = ShiftSwapRepository(session)
    if user_id is not None:
        return await repository.list_for_user(user_id)
    if approver_id is not None:
        return await repository.list_for_approver(approver_id)
    return []


async def create_shift_swap_request(
    session: AsyncSession, payload: ShiftSwapRequestCreateRequest
) -> ShiftSwapRequest:
    user_repository = UserRepository(session)
    schedule_repository = DailyShiftScheduleRepository(session)
    for user_id in (payload.requested_by_id, payload.requested_for_id, payload.approver_id):
        if await user_repository.get_by_id(user_id) is None:
            raise NotFoundError("User not found.")
    current_schedule = await schedule_repository.get_by_id(payload.current_schedule_id)
    requested_schedule = await schedule_repository.get_by_id(payload.requested_schedule_id)
    if current_schedule is None or requested_schedule is None:
        raise NotFoundError("Daily shift schedule not found.")
    swap = ShiftSwapRequest(
        requested_by_id=payload.requested_by_id,
        requested_for_id=payload.requested_for_id,
        current_schedule_id=payload.current_schedule_id,
        requested_schedule_id=payload.requested_schedule_id,
        approver_id=payload.approver_id,
        info=payload.info,
    )
    return await ShiftSwapRepository(session).create(swap)


async def respond_to_shift_swap_request(
    session: AsyncSession,
    swap_id: int,
    approver_id: int,
    payload: ShiftSwapRequestRespondRequest,
) -> ShiftSwapRequest:
    repository = ShiftSwapRepository(session)
    swap = await repository.get_by_id(swap_id)
    if swap is None:
        raise NotFoundError("Shift swap request not found.")
    if swap.approver_id != approver_id:
        raise PermissionDeniedError("You do not have permission to respond to this request.")
    swap.status = (
        ShiftSwapRequest.Status.APPROVED.value
        if payload.response == "APPROVE"
        else ShiftSwapRequest.Status.REJECTED.value
    )
    return await repository.save(swap)


async def delete_shift_swap_request(session: AsyncSession, swap_id: int) -> None:
    repository = ShiftSwapRepository(session)
    swap = await repository.get_by_id(swap_id)
    if swap is None:
        raise NotFoundError("Shift swap request not found.")
    await repository.delete(swap)


async def get_attendance_summary(
    session: AsyncSession, user_id: int, year: int, month: int
) -> AttendanceSummaryRead:
    user_repository = UserRepository(session)
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")

    start, end = _month_window(year, month)
    total_days = (end - start).days + 1
    attendance_records = await AttendanceRecordRepository(session).list_for_user_range(
        user_id,
        datetime.combine(start, datetime.min.time(), tzinfo=UTC),
        datetime.combine(end, datetime.max.time(), tzinfo=UTC),
    )
    schedules = (
        await DailyShiftRecordRepository(session).list_for_department_month(
            user.department_id or 0, year, month
        )
        if user.department_id
        else []
    )
    holidays = await HolidayRepository(session).list(year=year)
    overtime = await OvertimeRepository(session).list_for_user(user_id)

    records_by_day: dict[int, list[AttendanceRecord]] = {}
    for record in attendance_records:
        records_by_day.setdefault(record.timestamp.astimezone().day, []).append(record)

    schedules_by_day: dict[int, DailyShiftSchedule] = {}
    for record in schedules:
        if record.schedules:
            for schedule in record.schedules:
                if schedule.user_id == user_id:
                    schedules_by_day[record.date.day] = schedule

    holidays_by_day: dict[int, list[Holiday]] = {}
    for holiday in holidays:
        if holiday.month == month and (holiday.year is None or holiday.year == year):
            holidays_by_day.setdefault(holiday.day, []).append(holiday)

    overtime_by_day = {
        overtime_request.date.day
        for overtime_request in overtime
        if overtime_request.status == OvertimeRequest.Status.APPROVED.value
        and overtime_request.date.year == year
        and overtime_request.date.month == month
    }

    summary_days: list[AttendanceSummaryDayRead] = []
    for day in range(1, total_days + 1):
        summary_days.append(
            AttendanceSummaryDayRead(
                day=day,
                day_name=day_name[date(year, month, day).weekday()],
                shift=DailyShiftScheduleRead.model_validate(schedules_by_day[day])
                if day in schedules_by_day
                else None,
                attendance_records=[
                    AttendanceRecordRead.model_validate(record)
                    for record in records_by_day.get(day, [])
                ],
                holidays=[
                    HolidayRead.model_validate(holiday)
                    for holiday in holidays_by_day.get(day, [])
                ],
                overtime_approved=day in overtime_by_day,
            )
        )

    return AttendanceSummaryRead(year=year, month=month, days=summary_days)
