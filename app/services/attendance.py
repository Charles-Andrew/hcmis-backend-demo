from uuid import UUID

from calendar import monthrange, day_name
from datetime import UTC, date, datetime
from typing import Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.capabilities import is_staff_user
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from app.core.time import utc_now
from app.models.attendance import (
    AttendanceRecord,
    DepartmentRosterDay,
    EmployeeShiftAssignment,
    Holiday,
    OvertimeApprover,
    OvertimeRequest,
    OvertimeRequestApprover,
    ShiftTemplate,
    ShiftSwapRequest,
)
from app.models.department import Department
from app.models.leave import LeaveRequestStatus
from app.models.user import User
from app.repositories.attendance import (
    AttendanceRecordRepository,
    DepartmentRosterDayRepository,
    EmployeeShiftAssignmentRepository,
    HolidayRepository,
    OvertimeApproverRepository,
    OvertimeRepository,
    ShiftTemplateRepository,
    ShiftSwapRepository,
)
from app.repositories.leave import LeaveRequestRepository
from app.repositories.departments import DepartmentRepository
from app.repositories.users import UserRepository
from app.services.notifications import create_notification_if_possible
from app.schemas.attendance import (
    AttendanceRecordRead,
    AttendanceRecordCreateRequest,
    AttendanceRecordUpdateRequest,
    AttendanceSummaryDayRead,
    AttendanceSummaryLeaveRead,
    AttendanceSummaryRead,
    DepartmentScheduleUpdateRequest,
    DepartmentRosterDayCreateRequest,
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
    OvertimeApproverUpsertRequest,
    OvertimeRequestCreateRequest,
    OvertimeRequestScope,
    OvertimeRequestRespondRequest,
    ShiftTemplateCreateRequest,
    ShiftSwapRequestCreateRequest,
    ShiftSwapRequestRespondRequest,
    ShiftTemplateUpdateRequest,
)
from app.schemas.user import UserRead


def _display_user_name(user: User | None) -> str:
    if user is None:
        return "A user"
    full_name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
    return full_name or user.email


def _month_window(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    last_day = monthrange(year, month)[1]
    end = date(year, month, last_day)
    return start, end


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _normalize_role(role: str | None) -> str:
    normalized = (role or "EMP").strip().upper()
    return normalized or "EMP"


def _approver_role_label(role: str) -> str:
    labels = {
        "DH": "Department Head",
        "DIR": "Director",
        "PRES": "President",
        "HR": "HR",
    }
    return labels.get(role, role)


async def _validate_overtime_approver_assignment(
    *,
    user_repository: UserRepository,
    approver_id: UUID | None,
    expected_role: str,
    approver_label: str,
    department_id: int,
) -> None:
    if approver_id is None:
        return

    user = await user_repository.get_by_id(approver_id)
    if user is None:
        raise NotFoundError("Approver user not found.")

    if not user.is_active:
        raise BadRequestError(f"{approver_label} must be an active user.")

    role = _normalize_role(user.role)
    if role != expected_role:
        expected_role_label = _approver_role_label(expected_role)
        raise BadRequestError(f"{approver_label} must have the {expected_role_label} role.")

    if expected_role == "DH" and user.department_id != department_id:
        raise BadRequestError(
            "Department approver must belong to the same department."
        )


def _validate_holiday_date(day: int, month: int, year: int | None) -> None:
    validation_year = year if year is not None else 2000
    try:
        date(validation_year, month, day)
    except ValueError as exc:
        raise BadRequestError("Holiday date is invalid.") from exc


async def _ensure_holiday_date_available(
    repository: HolidayRepository,
    *,
    day: int,
    month: int,
    year: int | None,
    exclude_id: int | None = None,
) -> None:
    conflicting_holiday = await repository.find_conflict(
        day=day,
        month=month,
        year=year,
        exclude_id=exclude_id,
    )
    if conflicting_holiday is None:
        return
    if conflicting_holiday.year is None:
        raise ConflictError("A recurring holiday already exists for this date.")
    raise ConflictError("A holiday already exists for this date.")


async def _get_overtime_approver_settings(
    session: AsyncSession, user: User
) -> OvertimeApprover:
    if user.department_id is None:
        raise ConflictError("User is not assigned to a department.")

    approver_settings = await OvertimeApproverRepository(session).get_by_department_id(
        user.department_id
    )
    if approver_settings is None:
        raise NotFoundError("Overtime approver settings not found for this department.")
    return approver_settings


async def _build_overtime_approval_pool(session: AsyncSession, user: User) -> list[User]:
    approver_settings = await _get_overtime_approver_settings(session, user)
    role = _normalize_role(user.role)
    if role == "DH":
        candidate_ids = [
            approver_settings.director_approver_id,
            approver_settings.president_approver_id,
            approver_settings.hr_approver_id,
        ]
    elif role == "DIR":
        candidate_ids = [
            approver_settings.president_approver_id,
            approver_settings.hr_approver_id,
        ]
    elif role == "PRES":
        candidate_ids = [approver_settings.hr_approver_id]
    elif role == "HR":
        candidate_ids = [
            approver_settings.president_approver_id,
            approver_settings.director_approver_id,
            approver_settings.department_approver_id,
        ]
    else:
        candidate_ids = [
            approver_settings.department_approver_id,
            approver_settings.director_approver_id,
            approver_settings.president_approver_id,
            approver_settings.hr_approver_id,
        ]

    pool: list[User] = []
    seen_ids: set[UUID] = set()
    user_repository = UserRepository(session)
    for candidate_id in candidate_ids:
        if candidate_id is None or candidate_id in seen_ids:
            continue
        approver = await user_repository.get_by_id(candidate_id)
        if approver is None or not approver.is_active:
            continue
        if approver.id == user.id:
            continue
        seen_ids.add(approver.id)
        pool.append(approver)
    return pool


async def _get_department_with_shifts(
    session: AsyncSession, department_id: int
) -> Department:
    statement = (
        select(Department)
        .options(selectinload(Department.shift_templates))
        .where(Department.id == department_id)
    )
    result = await session.execute(statement)
    department = result.scalar_one_or_none()
    if department is None:
        raise NotFoundError("Department not found.")
    return department


async def list_shift_templates(session: AsyncSession) -> list[ShiftTemplate]:
    return await ShiftTemplateRepository(session).list()


async def create_shift_template(
    session: AsyncSession, payload: ShiftTemplateCreateRequest
) -> ShiftTemplate:
    repository = ShiftTemplateRepository(session)
    existing = await repository.get_by_identity(
        payload.description,
        payload.start_time,
        payload.end_time,
        payload.start_time_2,
        payload.end_time_2,
    )
    if existing is not None:
        raise ConflictError("A shift with the same times already exists.")

    shift = ShiftTemplate(
        description=payload.description,
        start_time=payload.start_time,
        end_time=payload.end_time,
        start_time_2=payload.start_time_2,
        end_time_2=payload.end_time_2,
        is_active=payload.is_active,
    )
    return await repository.create(shift)


async def update_shift_template(
    session: AsyncSession, shift_id: int, payload: ShiftTemplateUpdateRequest
) -> ShiftTemplate:
    repository = ShiftTemplateRepository(session)
    shift = await repository.get_by_id(shift_id)
    if shift is None:
        raise NotFoundError("Shift not found.")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(shift, key, value)
    return await repository.save(shift)


async def delete_shift_template(session: AsyncSession, shift_id: int) -> str:
    repository = ShiftTemplateRepository(session)
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
    shift_repository = ShiftTemplateRepository(session)
    department = await department_repository.get_by_id(department_id)
    if department is None:
        raise NotFoundError("Department not found.")

    selected_shifts: list[ShiftTemplate] = []
    for shift_id in dict.fromkeys(payload.shift_ids):
        shift = await shift_repository.get_by_id(shift_id)
        if shift is None:
            raise NotFoundError("Shift not found.")
        selected_shifts.append(shift)

    department.default_workweek = payload.workweek
    department.shift_templates.clear()
    department.shift_templates.extend(selected_shifts)
    await department_repository.save(department)
    return await _get_department_with_shifts(session, department_id)


async def get_department_schedule(
    session: AsyncSession, department_id: int
) -> Department:
    return await _get_department_with_shifts(session, department_id)


async def list_daily_shift_records(
    session: AsyncSession, department_id: int, year: int, month: int
) -> list[DepartmentRosterDay]:
    return await DepartmentRosterDayRepository(session).list_for_department_month(
        department_id, year, month
    )


async def create_daily_shift_record(
    session: AsyncSession, payload: DepartmentRosterDayCreateRequest
) -> DepartmentRosterDay:
    repository = DepartmentRosterDayRepository(session)
    existing = await repository.get_by_department_date(
        payload.department_id, payload.date
    )
    if existing is not None:
        raise ConflictError("Daily shift record already exists for the selected date.")

    record = DepartmentRosterDay(
        date=payload.date,
        department_id=payload.department_id,
        is_approved=payload.is_approved,
    )
    record = await repository.create(record)
    if payload.schedule_ids:
        schedule_repo = EmployeeShiftAssignmentRepository(session)
        schedules = []
        for schedule_id in payload.schedule_ids:
            schedule = await schedule_repo.get_by_id(schedule_id)
            if schedule is None:
                raise NotFoundError("Daily shift schedule not found.")
            schedules.append(schedule)
        record.employee_shift_assignments.extend(schedules)
        record = await repository.save(record)
    return record


async def create_employee_shift_assignment(
    session: AsyncSession, payload: EmployeeShiftAssignmentCreateRequest
) -> EmployeeShiftAssignment:
    repository = EmployeeShiftAssignmentRepository(session)
    user = await UserRepository(session).get_by_id(payload.user_id)
    if user is None:
        raise NotFoundError("User not found.")
    shift = await ShiftTemplateRepository(session).get_by_id(payload.shift_id)
    if shift is None:
        raise NotFoundError("Shift not found.")
    existing = await repository.get_by_user_date(payload.user_id, payload.date)
    if existing is not None:
        raise ConflictError("A shift assignment already exists for the selected employee and date.")
    schedule = EmployeeShiftAssignment(
        date=payload.date,
        user_id=payload.user_id,
        shift_template_id=payload.shift_id,
    )
    schedule = await repository.create(schedule)
    await create_notification_if_possible(
        session,
        recipient_id=payload.user_id,
        content=(
            f"You were assigned to shift {shift.description} on "
            f"{payload.date.isoformat()}."
        ),
        url=f"/attendance?year={payload.date.year}&month={payload.date.month}",
    )
    return schedule


async def copy_previous_month_employee_shift_assignments(
    session: AsyncSession,
    payload: EmployeeShiftAssignmentCopyPreviousMonthRequest,
) -> EmployeeShiftAssignmentCopyPreviousMonthResponse:
    repository = EmployeeShiftAssignmentRepository(session)
    user = await UserRepository(session).get_by_id(payload.user_id)
    if user is None:
        raise NotFoundError("User not found.")

    if payload.month == 1:
        source_year = payload.year - 1
        source_month = 12
    else:
        source_year = payload.year
        source_month = payload.month - 1

    source_assignments = await repository.list_for_user_month(
        payload.user_id, source_year, source_month
    )
    if not source_assignments:
        raise NotFoundError("No assignments found in the previous month to copy.")

    target_assignments = await repository.list_for_user_month(
        payload.user_id, payload.year, payload.month
    )
    for assignment in target_assignments:
        await repository.delete(assignment)

    copied_count = 0
    skipped_count = 0
    target_last_day = monthrange(payload.year, payload.month)[1]

    for source_assignment in source_assignments:
        day = source_assignment.date.day
        if day > target_last_day:
            skipped_count += 1
            continue

        copied_assignment = EmployeeShiftAssignment(
            date=date(payload.year, payload.month, day),
            user_id=payload.user_id,
            shift_template_id=source_assignment.shift_template_id,
        )
        await repository.create(copied_assignment)
        copied_count += 1

    return EmployeeShiftAssignmentCopyPreviousMonthResponse(
        copied_count=copied_count,
        skipped_count=skipped_count,
    )


async def generate_month_employee_shift_assignments(
    session: AsyncSession,
    payload: EmployeeShiftAssignmentGenerateMonthRequest,
) -> EmployeeShiftAssignmentGenerateMonthResponse:
    repository = EmployeeShiftAssignmentRepository(session)
    department_repository = DepartmentRepository(session)
    user = await UserRepository(session).get_by_id(payload.user_id)
    if user is None:
        raise NotFoundError("User not found.")
    if user.department_id is None:
        raise ConflictError("The selected user does not belong to a department.")

    department = await department_repository.get_by_id(user.department_id)
    if department is None:
        raise NotFoundError("Department not found.")

    allowed_templates = list(department.shift_templates)
    if not allowed_templates:
        raise ConflictError("The department does not have any allowed shift templates.")

    selected_template = None
    if payload.shift_id is not None:
        selected_template = next(
            (template for template in allowed_templates if template.id == payload.shift_id),
            None,
        )
        if selected_template is None:
            raise ConflictError("The selected shift template is not allowed for this department.")
    else:
        selected_template = allowed_templates[0]

    workweek_days = {day.strip() for day in department.default_workweek if day.strip()}
    if not workweek_days:
        raise ConflictError("The department does not have a default workweek configured.")

    generated_count = 0
    skipped_count = 0
    for day in range(1, monthrange(payload.year, payload.month)[1] + 1):
        current_date = date(payload.year, payload.month, day)
        weekday_name = day_name[current_date.weekday()]
        if weekday_name not in workweek_days:
            continue

        existing = await repository.get_by_user_date(payload.user_id, current_date)
        if existing is not None:
            skipped_count += 1
            continue

        await repository.create(
            EmployeeShiftAssignment(
                date=current_date,
                user_id=payload.user_id,
                shift_template_id=selected_template.id,
            )
        )
        generated_count += 1

    return EmployeeShiftAssignmentGenerateMonthResponse(
        generated_count=generated_count,
        skipped_count=skipped_count,
    )


async def list_employee_shift_assignments(
    session: AsyncSession, department_id: int, year: int, month: int
) -> list[EmployeeShiftAssignment]:
    return await EmployeeShiftAssignmentRepository(session).list_for_department_month(
        department_id, year, month
    )


async def delete_employee_shift_assignment(
    session: AsyncSession, schedule_id: int
) -> None:
    repository = EmployeeShiftAssignmentRepository(session)
    schedule = await repository.get_by_id(schedule_id)
    if schedule is None:
        raise NotFoundError("Daily shift schedule not found.")
    shift_description = (
        schedule.shift_template.description if schedule.shift_template is not None else "your shift"
    )
    schedule_date = schedule.date.isoformat()
    user_id = schedule.user_id
    await repository.delete(schedule)
    await create_notification_if_possible(
        session,
        recipient_id=user_id,
        content=(
            f"Your shift assignment ({shift_description}) on {schedule_date} was removed."
        ),
        url=f"/attendance?year={schedule.date.year}&month={schedule.date.month}",
    )


async def update_employee_shift_assignment(
    session: AsyncSession,
    schedule_id: int,
    payload: EmployeeShiftAssignmentUpdateRequest,
) -> EmployeeShiftAssignment:
    repository = EmployeeShiftAssignmentRepository(session)
    schedule = await repository.get_by_id(schedule_id)
    if schedule is None:
        raise NotFoundError("Daily shift schedule not found.")
    previous_shift_description = (
        schedule.shift_template.description if schedule.shift_template is not None else "previous shift"
    )
    shift = await ShiftTemplateRepository(session).get_by_id(payload.shift_id)
    if shift is None:
        raise NotFoundError("Shift not found.")
    schedule.shift_template_id = payload.shift_id
    schedule = await repository.save(schedule)
    await create_notification_if_possible(
        session,
        recipient_id=schedule.user_id,
        content=(
            f"Your shift on {schedule.date.isoformat()} was updated from "
            f"{previous_shift_description} to {shift.description}."
        ),
        url=f"/attendance?year={schedule.date.year}&month={schedule.date.month}",
    )
    return schedule


async def list_attendance_records(
    session: AsyncSession, user_id: UUID, year: int, month: int
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
    if payload.raw_event_id:
        by_raw_event = await repository.get_by_raw_event_id(payload.raw_event_id)
        if by_raw_event is not None:
            raise ConflictError("Attendance record already exists.")
        deleted_raw_event = await repository.get_deleted_by_raw_event_id(payload.raw_event_id)
        if deleted_raw_event is not None:
            raise ConflictError("Attendance record was deleted and cannot be restored.")
    duplicate = await repository.get_duplicate(
        payload.user_id, _ensure_aware(payload.timestamp), payload.punch
    )
    if duplicate is not None:
        raise ConflictError("Attendance record already exists.")
    record = AttendanceRecord(
        user_id=payload.user_id,
        device_user_id=payload.device_user_id,
        raw_event_id=payload.raw_event_id,
        timestamp=_ensure_aware(payload.timestamp),
        punch=payload.punch,
    )
    return await repository.create(record)


async def sync_device_attendance(
    session: AsyncSession,
    device_user_id: int,
    timestamp: datetime,
    punch: Literal["IN", "OUT"],
    raw_event_id: str | None = None,
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
            raw_event_id=raw_event_id,
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
    await repository.delete(record, tombstone_raw_event_id=record.raw_event_id)


async def list_holidays(session: AsyncSession, year: int | None = None) -> list[Holiday]:
    return await HolidayRepository(session).list(year=year)


async def create_holiday(session: AsyncSession, payload: HolidayCreateRequest) -> Holiday:
    _validate_holiday_date(payload.day, payload.month, payload.year)
    repository = HolidayRepository(session)
    await _ensure_holiday_date_available(
        repository,
        day=payload.day,
        month=payload.month,
        year=payload.year,
    )
    holiday = Holiday(
        name=payload.name,
        day=payload.day,
        month=payload.month,
        year=payload.year,
    )
    return await repository.create(holiday)


async def update_holiday(
    session: AsyncSession, holiday_id: int, payload: HolidayUpdateRequest
) -> Holiday:
    repository = HolidayRepository(session)
    holiday = await repository.get_by_id(holiday_id)
    if holiday is None:
        raise NotFoundError("Holiday not found.")
    data = payload.model_dump(exclude_unset=True)
    updated_day = data.get("day", holiday.day)
    updated_month = data.get("month", holiday.month)
    updated_year = data.get("year", holiday.year)
    _validate_holiday_date(updated_day, updated_month, updated_year)
    await _ensure_holiday_date_available(
        repository,
        day=updated_day,
        month=updated_month,
        year=updated_year,
        exclude_id=holiday_id,
    )
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
    session: AsyncSession,
    *,
    current_user_id: UUID,
    current_user_is_staff: bool,
    scope: OvertimeRequestScope | None = None,
    user_id: UUID | None = None,
    approver_id: UUID | None = None,
    year: int | None = None,
    month: int | None = None,
    status: str | None = None,
    department_id: int | None = None,
    query: str | None = None,
) -> list[OvertimeRequest]:
    scope_label: OvertimeRequestScope
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
            raise PermissionDeniedError("You do not have permission to view all overtime requests.")
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

    return await OvertimeRepository(session).list(
        user_id=selected_user_id if scope_label != "approvals" else None,
        approver_id=selected_approver_id if scope_label != "mine" else None,
        year=year,
        month=month,
        status=status,
        department_id=department_id,
        query=query,
    )


async def list_overtime_approvers(session: AsyncSession) -> list[OvertimeApprover]:
    return await OvertimeApproverRepository(session).list()


async def upsert_overtime_approver(
    session: AsyncSession, department_id: int, payload: OvertimeApproverUpsertRequest
) -> OvertimeApprover:
    department = await DepartmentRepository(session).get_by_id(department_id)
    if department is None:
        raise NotFoundError("Department not found.")

    user_repository = UserRepository(session)
    await _validate_overtime_approver_assignment(
        user_repository=user_repository,
        approver_id=payload.department_approver_id,
        expected_role="DH",
        approver_label="Department approver",
        department_id=department_id,
    )
    await _validate_overtime_approver_assignment(
        user_repository=user_repository,
        approver_id=payload.director_approver_id,
        expected_role="DIR",
        approver_label="Director approver",
        department_id=department_id,
    )
    await _validate_overtime_approver_assignment(
        user_repository=user_repository,
        approver_id=payload.president_approver_id,
        expected_role="PRES",
        approver_label="President approver",
        department_id=department_id,
    )
    await _validate_overtime_approver_assignment(
        user_repository=user_repository,
        approver_id=payload.hr_approver_id,
        expected_role="HR",
        approver_label="HR approver",
        department_id=department_id,
    )

    repository = OvertimeApproverRepository(session)
    overtime_approver = await repository.get_by_department_id(department_id)
    if overtime_approver is None:
        overtime_approver = OvertimeApprover(department_id=department_id)
        overtime_approver.department_approver_id = payload.department_approver_id
        overtime_approver.director_approver_id = payload.director_approver_id
        overtime_approver.president_approver_id = payload.president_approver_id
        overtime_approver.hr_approver_id = payload.hr_approver_id
        return await repository.create(overtime_approver)

    overtime_approver.department_approver_id = payload.department_approver_id
    overtime_approver.director_approver_id = payload.director_approver_id
    overtime_approver.president_approver_id = payload.president_approver_id
    overtime_approver.hr_approver_id = payload.hr_approver_id
    return await repository.save(overtime_approver)


async def delete_overtime_approver(session: AsyncSession, department_id: int) -> None:
    repository = OvertimeApproverRepository(session)
    overtime_approver = await repository.get_by_department_id(department_id)
    if overtime_approver is None:
        raise NotFoundError("Overtime approver settings not found.")
    await repository.delete(overtime_approver)


async def get_my_overtime_approver_assignment(
    session: AsyncSession, current_user: User
) -> OvertimeApproverAssignmentRead:
    approvers = await _build_overtime_approval_pool(session, current_user)
    approver = approvers[0] if approvers else None
    return OvertimeApproverAssignmentRead(
        approver_id=approver.id if approver is not None else None,
        approver=UserRead.model_validate(approver) if approver is not None else None,
        approver_ids=[item.id for item in approvers],
        approvers=[UserRead.model_validate(item) for item in approvers],
    )


async def create_overtime_request(
    session: AsyncSession, current_user: User, payload: OvertimeRequestCreateRequest
) -> OvertimeRequest:
    user = await UserRepository(session).get_by_id(payload.user_id)
    if user is None:
        raise NotFoundError("User not found.")
    existing_overtime = await OvertimeRepository(session).get_active_for_user_date(
        payload.user_id,
        payload.date,
        statuses=(
            OvertimeRequest.Status.PENDING.value,
            OvertimeRequest.Status.APPROVED.value,
        ),
    )
    if existing_overtime is not None:
        raise ConflictError("An active overtime request already exists for this date.")
    existing_leave = await LeaveRequestRepository(session).get_active_for_user_date(
        payload.user_id,
        payload.date,
        statuses=(
            LeaveRequestStatus.PENDING.value,
            LeaveRequestStatus.APPROVED.value,
        ),
    )
    if existing_leave is not None:
        raise ConflictError("An active leave request already exists for this date.")
    approvers = await _build_overtime_approval_pool(session, user)
    if not approvers:
        raise NotFoundError("No overtime approver is configured for this user.")
    first_approver = approvers[0]
    overtime = OvertimeRequest(
        user_id=payload.user_id,
        approver_id=first_approver.id,
        info=payload.info,
        date=payload.date,
        status=OvertimeRequest.Status.PENDING.value,
        approver_pool=[
            OvertimeRequestApprover(
                approver_id=approver.id,
                status=OvertimeRequest.Status.PENDING.value,
            )
            for approver in approvers
        ],
    )
    overtime = await OvertimeRepository(session).create(overtime)
    requester_name = _display_user_name(user)
    for approver in approvers:
        await create_notification_if_possible(
            session,
            recipient_id=approver.id,
            sender_id=current_user.id,
            content=f"{requester_name} filed an overtime request for {overtime.date.isoformat()}.",
            url=(
                f"/hr/overtime-management?scope=approvals&status=PENDING"
                f"&month={overtime.date.month}&year={overtime.date.year}"
            ),
        )
    return overtime


async def respond_to_overtime_request(
    session: AsyncSession,
    overtime_id: int,
    approver_id: UUID,
    payload: OvertimeRequestRespondRequest,
) -> OvertimeRequest:
    repository = OvertimeRepository(session)
    overtime = await repository.get_by_id(overtime_id)
    if overtime is None:
        raise NotFoundError("Overtime request not found.")
    if overtime.user_id == approver_id:
        raise PermissionDeniedError("You cannot review your own overtime request.")
    current_pool_assignment = next(
        (
            assignment
            for assignment in overtime.approver_pool
            if assignment.approver_id == approver_id
        ),
        None,
    )
    if current_pool_assignment is None:
        raise PermissionDeniedError("You do not have permission to respond to this request.")
    if current_pool_assignment.status != OvertimeRequest.Status.PENDING.value:
        raise ConflictError("This overtime request has already been decided by you.")
    if overtime.status != OvertimeRequest.Status.PENDING.value:
        raise ConflictError("This overtime request has already been decided.")
    final_status = (
        OvertimeRequest.Status.APPROVED.value
        if payload.response == "APPROVE"
        else OvertimeRequest.Status.REJECTED.value
    )
    current_pool_assignment.status = final_status
    current_pool_assignment.acted_at = datetime.now(UTC)
    for assignment in overtime.approver_pool:
        if assignment is current_pool_assignment:
            continue
        if assignment.status == OvertimeRequest.Status.PENDING.value:
            assignment.status = final_status
    overtime.approver_id = approver_id
    overtime.status = final_status
    overtime = await repository.save(overtime)
    decision = "approved" if payload.response == "APPROVE" else "rejected"
    await create_notification_if_possible(
        session,
        recipient_id=overtime.user_id,
        sender_id=approver_id,
        content=(
            f"Your overtime request for {overtime.date.isoformat()} has been {decision}."
        ),
        url=f"/overtime?month={overtime.date.month}&year={overtime.date.year}",
    )
    return overtime


async def cancel_overtime_request(
    session: AsyncSession, overtime_id: int, current_user: User
) -> OvertimeRequest:
    repository = OvertimeRepository(session)
    overtime = await repository.get_by_id(overtime_id)
    if overtime is None:
        raise NotFoundError("Overtime request not found.")
    if overtime.user_id != current_user.id and not is_staff_user(current_user):
        raise PermissionDeniedError("You are not allowed to cancel this overtime request.")
    if overtime.status != OvertimeRequest.Status.PENDING.value:
        raise ConflictError("Only pending overtime requests can be cancelled.")

    now = utc_now()
    overtime.status = OvertimeRequest.Status.CANCELLED.value
    for assignment in overtime.approver_pool:
        if assignment.status == OvertimeRequest.Status.PENDING.value:
            assignment.status = OvertimeRequest.Status.CANCELLED.value
            assignment.acted_at = now
    return await repository.save(overtime)


async def list_shift_swap_requests(
    session: AsyncSession, user_id: UUID | None = None, approver_id: UUID | None = None
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
    schedule_repository = EmployeeShiftAssignmentRepository(session)
    users: dict[UUID, User] = {}
    for user_id in (payload.requested_by_id, payload.requested_for_id, payload.approver_id):
        user = await user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        users[user_id] = user
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
        status=ShiftSwapRequest.Status.PENDING.value,
    )
    swap = await ShiftSwapRepository(session).create(swap)
    requester_name = _display_user_name(users.get(payload.requested_by_id))
    await create_notification_if_possible(
        session,
        recipient_id=swap.approver_id,
        sender_id=swap.requested_by_id,
        content=f"{requester_name} filed a shift swap request that needs your review.",
        url=(
            f"/hr/user-attendance-management?tab=shifts&user={swap.requested_by_id}"
            f"&year={current_schedule.date.year}&month={current_schedule.date.month}"
        ),
    )
    await create_notification_if_possible(
        session,
        recipient_id=swap.requested_for_id,
        sender_id=swap.requested_by_id,
        content=f"{requester_name} requested to swap shift assignments with you.",
        url=(
            f"/attendance?year={current_schedule.date.year}"
            f"&month={current_schedule.date.month}"
        ),
    )
    return swap


async def respond_to_shift_swap_request(
    session: AsyncSession,
    swap_id: int,
    approver_id: UUID,
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
    swap = await repository.save(swap)
    decision = "approved" if payload.response == "APPROVE" else "rejected"
    await create_notification_if_possible(
        session,
        recipient_id=swap.requested_by_id,
        sender_id=approver_id,
        content=f"Your shift swap request has been {decision}.",
        url="/attendance",
    )
    await create_notification_if_possible(
        session,
        recipient_id=swap.requested_for_id,
        sender_id=approver_id,
        content=f"A shift swap request involving you has been {decision}.",
        url="/attendance",
    )
    return swap


async def delete_shift_swap_request(session: AsyncSession, swap_id: int) -> None:
    repository = ShiftSwapRepository(session)
    swap = await repository.get_by_id(swap_id)
    if swap is None:
        raise NotFoundError("Shift swap request not found.")
    await repository.delete(swap)


async def get_attendance_summary(
    session: AsyncSession, user_id: UUID, year: int, month: int
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
    assignments = await EmployeeShiftAssignmentRepository(session).list_for_user_month(
        user_id, year, month
    )
    holidays = await HolidayRepository(session).list(year=year)
    overtime = await OvertimeRepository(session).list_for_user(user_id)
    approved_leave_requests = await LeaveRequestRepository(session).list(
        user_id=user_id,
        status=LeaveRequestStatus.APPROVED.value,
        year=year,
        month=month,
    )

    records_by_day: dict[int, list[AttendanceRecord]] = {}
    for record in attendance_records:
        records_by_day.setdefault(record.timestamp.astimezone().day, []).append(record)

    assignments_by_day: dict[int, EmployeeShiftAssignment] = {}
    for assignment in assignments:
        assignments_by_day[assignment.date.day] = assignment

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
    approved_leave_by_day = {
        leave_request.leave_date.day: leave_request
        for leave_request in approved_leave_requests
    }

    summary_days: list[AttendanceSummaryDayRead] = []
    for day in range(1, total_days + 1):
        summary_days.append(
            AttendanceSummaryDayRead(
                day=day,
                day_name=day_name[date(year, month, day).weekday()],
                shift=EmployeeShiftAssignmentRead.model_validate(assignments_by_day[day])
                if day in assignments_by_day
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
                approved_leave=AttendanceSummaryLeaveRead(
                    id=approved_leave_by_day[day].id,
                    leave_date=approved_leave_by_day[day].leave_date,
                    leave_type=approved_leave_by_day[day].leave_type,
                    info=approved_leave_by_day[day].info,
                )
                if day in approved_leave_by_day
                else None,
            )
        )

    return AttendanceSummaryRead(year=year, month=month, days=summary_days)


list_shifts = list_shift_templates
create_shift = create_shift_template
update_shift = update_shift_template
delete_shift = delete_shift_template
create_daily_shift_schedule = create_employee_shift_assignment
list_daily_shift_schedules = list_employee_shift_assignments
delete_daily_shift_schedule = delete_employee_shift_assignment
