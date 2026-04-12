import anyio
import pytest
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Literal, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.time import utc_now
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
from app.models.leave import LeaveRequest, LeaveRequestStatus
from app.models.user import User
from app.schemas.attendance import (
    AttendanceRecordCreateRequest,
    AttendanceRecordUpdateRequest,
    AttendanceSummaryRead,
    DepartmentScheduleUpdateRequest,
    HolidayCreateRequest,
    OvertimeRequestCreateRequest,
    OvertimeRequestRespondRequest,
    ShiftTemplateCreateRequest,
    ShiftSwapRequestCreateRequest,
    ShiftSwapRequestRespondRequest,
)
from app.services import attendance as attendance_service


@dataclass
class OvertimeApprover:
    id: int
    department_id: int
    department_approver_id: UUID | None
    director_approver_id: UUID | None
    president_approver_id: UUID | None
    hr_approver_id: UUID | None
    created_at: datetime
    updated_at: datetime


class FakeUserRepository:
    users: dict[UUID, User] = {}

    def __init__(self, session):
        self.session = session

    async def get_by_id(self, user_id: UUID):
        return self.users.get(user_id)

    async def list(self, include_superusers: bool = False, **kwargs):
        users = list(self.users.values())
        if not include_superusers:
            users = [user for user in users if not user.is_superuser]
        return users


class FakeDepartmentRepository:
    departments: dict[int, Department] = {}

    def __init__(self, session):
        self.session = session

    async def get_by_id(self, department_id: int):
        return self.departments.get(department_id)

    async def save(self, department: Department):
        department.updated_at = utc_now()
        self.departments[department.id] = department
        return department


class FakeShiftTemplateRepository:
    shifts: dict[int, ShiftTemplate] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(self):
        return sorted(self.shifts.values(), key=lambda item: item.description)

    async def get_by_id(self, shift_id: int):
        return self.shifts.get(shift_id)

    async def get_by_identity(self, description, start_time, end_time, start_time_2=None, end_time_2=None):
        for shift in self.shifts.values():
            if (
                shift.description == description
                and shift.start_time == start_time
                and shift.end_time == end_time
                and shift.start_time_2 == start_time_2
                and shift.end_time_2 == end_time_2
            ):
                return shift
        return None

    async def create(self, shift: ShiftTemplate):
        shift.id = self.next_id
        self.next_id += 1
        shift.created_at = shift.created_at or utc_now()
        shift.updated_at = shift.updated_at or utc_now()
        self.shifts[shift.id] = shift
        return shift

    async def save(self, shift: ShiftTemplate):
        shift.updated_at = utc_now()
        self.shifts[shift.id] = shift
        return shift

    async def delete(self, shift: ShiftTemplate):
        self.shifts.pop(shift.id, None)


class FakeAttendanceRecordRepository:
    records: dict[int, AttendanceRecord] = {}
    deleted_raw_event_ids: set[str] = set()
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list_for_user_range(self, user_id: UUID, start: datetime, end: datetime):
        return [
            record
            for record in self.records.values()
            if record.user_id == user_id and start <= record.timestamp <= end
        ]

    async def get_by_id(self, record_id: int):
        return self.records.get(record_id)

    async def get_duplicate(self, user_id: int, timestamp: datetime, punch: str):
        for record in self.records.values():
            if (
                record.user_id == user_id
                and record.timestamp == timestamp
                and record.punch == punch
            ):
                return record
        return None

    async def get_by_raw_event_id(self, raw_event_id: str):
        for record in self.records.values():
            if record.raw_event_id == raw_event_id:
                return record
        return None

    async def get_deleted_by_raw_event_id(self, raw_event_id: str):
        if raw_event_id in self.deleted_raw_event_ids:
            return object()
        return None

    async def create(self, record: AttendanceRecord):
        record.id = self.next_id
        self.next_id += 1
        record.created_at = record.created_at or utc_now()
        record.updated_at = record.updated_at or utc_now()
        self.records[record.id] = record
        return record

    async def save(self, record: AttendanceRecord):
        record.updated_at = utc_now()
        self.records[record.id] = record
        return record

    async def delete(self, record: AttendanceRecord, *, tombstone_raw_event_id: str | None = None):
        if tombstone_raw_event_id:
            self.deleted_raw_event_ids.add(tombstone_raw_event_id)
        self.records.pop(record.id, None)


class FakeEmployeeShiftAssignmentRepository:
    schedules: dict[int, EmployeeShiftAssignment] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list_for_department_month(self, department_id: int, year: int, month: int):
        return [
            schedule
            for schedule in self.schedules.values()
            if schedule.user.department_id == department_id
            and schedule.date.year == year
            and schedule.date.month == month
        ]

    async def list_for_user_month(self, user_id: UUID, year: int, month: int):
        return [
            schedule
            for schedule in self.schedules.values()
            if schedule.user_id == user_id
            and schedule.date.year == year
            and schedule.date.month == month
        ]

    async def get_by_id(self, schedule_id: int):
        return self.schedules.get(schedule_id)

    async def get_by_user_date(self, user_id: UUID, selected_date: date):
        for schedule in self.schedules.values():
            if schedule.user_id == user_id and schedule.date == selected_date:
                return schedule
        return None

    async def create(self, schedule: EmployeeShiftAssignment):
        schedule.id = self.next_id
        self.next_id += 1
        schedule.created_at = schedule.created_at or utc_now()
        schedule.updated_at = schedule.updated_at or utc_now()
        self.schedules[schedule.id] = schedule
        return schedule

    async def save(self, schedule: EmployeeShiftAssignment):
        schedule.updated_at = utc_now()
        self.schedules[schedule.id] = schedule
        return schedule

    async def delete(self, schedule: EmployeeShiftAssignment):
        self.schedules.pop(schedule.id, None)


class FakeDepartmentRosterDayRepository:
    records: dict[int, DepartmentRosterDay] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def get_by_department_date(self, department_id: int, selected_date: date):
        for record in self.records.values():
            if record.department_id == department_id and record.date == selected_date:
                return record
        return None

    async def list_for_department_month(self, department_id: int, year: int, month: int):
        return [
            record
            for record in self.records.values()
            if record.department_id == department_id
            and record.date.year == year
            and record.date.month == month
        ]

    async def create(self, record: DepartmentRosterDay):
        record.id = self.next_id
        self.next_id += 1
        record.created_at = record.created_at or utc_now()
        record.updated_at = record.updated_at or utc_now()
        self.records[record.id] = record
        return record

    async def save(self, record: DepartmentRosterDay):
        record.updated_at = utc_now()
        self.records[record.id] = record
        return record


class FakeHolidayRepository:
    holidays: dict[int, Holiday] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(self, year: int | None = None):
        holidays = list(self.holidays.values())
        if year is not None:
            holidays = [holiday for holiday in holidays if holiday.year in (None, year)]
        return sorted(holidays, key=lambda item: (item.year or 0, item.month, item.day), reverse=True)

    async def get_by_id(self, holiday_id: int):
        return self.holidays.get(holiday_id)

    async def find_conflict(
        self,
        *,
        day: int,
        month: int,
        year: int | None,
        exclude_id: int | None = None,
    ):
        for holiday in self.holidays.values():
            if exclude_id is not None and holiday.id == exclude_id:
                continue
            if holiday.day != day or holiday.month != month:
                continue
            if holiday.year is None or year is None or holiday.year == year:
                return holiday
        return None

    async def create(self, holiday: Holiday):
        holiday.id = self.next_id
        self.next_id += 1
        holiday.created_at = holiday.created_at or utc_now()
        holiday.updated_at = holiday.updated_at or utc_now()
        self.holidays[holiday.id] = holiday
        return holiday

    async def save(self, holiday: Holiday):
        holiday.updated_at = utc_now()
        self.holidays[holiday.id] = holiday
        return holiday

    async def delete(self, holiday: Holiday):
        self.holidays.pop(holiday.id, None)


class FakeLeaveRequestRepository:
    leave_requests: dict[int, LeaveRequest] = {}

    def __init__(self, session):
        self.session = session

    async def list(
        self,
        user_id: UUID | None = None,
        department_id: int | None = None,
        approver_id: UUID | None = None,
        status: str | None = None,
        year: int | None = None,
        month: int | None = None,
    ):
        requests = list(self.leave_requests.values())
        if user_id is not None:
            requests = [item for item in requests if item.user_id == user_id]
        if status is not None:
            requests = [item for item in requests if item.status == status]
        if year is not None:
            requests = [item for item in requests if item.leave_date.year == year]
        if month is not None:
            requests = [item for item in requests if item.leave_date.month == month]
        return sorted(requests, key=lambda item: (item.leave_date, item.created_at), reverse=True)

    async def get_active_for_user_date(self, user_id: UUID, selected_date: date, *, statuses: tuple[str, ...]):
        for request in self.leave_requests.values():
            if (
                request.user_id == user_id
                and request.leave_date == selected_date
                and request.status in statuses
            ):
                return request
        return None


class FakeOvertimeRepository:
    overtime_requests: dict[int, OvertimeRequest] = {}
    next_id = 1
    next_assignment_id = 1

    def __init__(self, session):
        self.session = session

    async def list_for_user(self, user_id: UUID):
        return [
            overtime
            for overtime in self.overtime_requests.values()
            if overtime.user_id == user_id
        ]

    async def list_for_approver(self, approver_id: UUID):
        return [
            overtime
            for overtime in self.overtime_requests.values()
            if any(
                assignment.approver_id == approver_id
                for assignment in (overtime.approver_pool or [])
            )
        ]

    async def list(
        self,
        *,
        user_id: int | None = None,
        approver_id: int | None = None,
        year: int | None = None,
        month: int | None = None,
        status: str | None = None,
        department_id: int | None = None,
        query: str | None = None,
    ):
        _ = department_id
        results = list(self.overtime_requests.values())
        if user_id is not None:
            results = [item for item in results if item.user_id == user_id]
        if approver_id is not None:
            results = [
                item
                for item in results
                if any(
                    assignment.approver_id == approver_id
                    for assignment in (item.approver_pool or [])
                )
            ]
        if year is not None:
            results = [item for item in results if item.date.year == year]
        if month is not None:
            results = [item for item in results if item.date.month == month]
        if status is not None:
            results = [item for item in results if item.status == status]
        if query:
            lowered = query.lower()
            results = [
                item
                for item in results
                if lowered in (item.info or "").lower()
            ]
        return results

    async def get_by_id(self, overtime_id: int):
        return self.overtime_requests.get(overtime_id)

    async def get_active_for_user_date(self, user_id: UUID, selected_date: date, *, statuses: tuple[str, ...]):
        for overtime in self.overtime_requests.values():
            if (
                overtime.user_id == user_id
                and overtime.date == selected_date
                and overtime.status in statuses
            ):
                return overtime
        return None

    async def create(self, overtime: OvertimeRequest):
        overtime.id = self.next_id
        self.next_id += 1
        overtime.created_at = overtime.created_at or utc_now()
        overtime.updated_at = overtime.updated_at or utc_now()
        for assignment in overtime.approver_pool:
            assignment.id = assignment.id or self.next_assignment_id
            self.next_assignment_id += 1
            assignment.overtime_request_id = overtime.id
        self.overtime_requests[overtime.id] = overtime
        return overtime

    async def save(self, overtime: OvertimeRequest):
        overtime.updated_at = utc_now()
        self.overtime_requests[overtime.id] = overtime
        return overtime

    async def delete(self, overtime: OvertimeRequest):
        self.overtime_requests.pop(overtime.id, None)


class FakeOvertimeApproverRepository:
    overtime_approvers: dict[int, OvertimeApprover] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(self):
        return list(self.overtime_approvers.values())

    async def get_by_department_id(self, department_id: int):
        return self.overtime_approvers.get(department_id)

    async def create(self, overtime_approver: OvertimeApprover):
        overtime_approver.id = self.next_id
        self.next_id += 1
        overtime_approver.created_at = overtime_approver.created_at or utc_now()
        overtime_approver.updated_at = overtime_approver.updated_at or utc_now()
        self.overtime_approvers[overtime_approver.department_id] = overtime_approver
        return overtime_approver

    async def save(self, overtime_approver: OvertimeApprover):
        overtime_approver.updated_at = utc_now()
        self.overtime_approvers[overtime_approver.department_id] = overtime_approver
        return overtime_approver

    async def delete(self, overtime_approver: OvertimeApprover):
        self.overtime_approvers.pop(overtime_approver.department_id, None)


class FakeShiftSwapRepository:
    swaps: dict[int, ShiftSwapRequest] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list_for_user(self, user_id: UUID):
        return [
            swap
            for swap in self.swaps.values()
            if swap.requested_by_id == user_id or swap.requested_for_id == user_id
        ]

    async def list_for_approver(self, approver_id: UUID):
        return [swap for swap in self.swaps.values() if swap.approver_id == approver_id]

    async def get_by_id(self, swap_id: int):
        return self.swaps.get(swap_id)

    async def create(self, swap: ShiftSwapRequest):
        swap.id = self.next_id
        self.next_id += 1
        swap.created_at = swap.created_at or utc_now()
        swap.updated_at = swap.updated_at or utc_now()
        self.swaps[swap.id] = swap
        return swap

    async def save(self, swap: ShiftSwapRequest):
        swap.updated_at = utc_now()
        self.swaps[swap.id] = swap
        return swap

    async def delete(self, swap: ShiftSwapRequest):
        self.swaps.pop(swap.id, None)


async def _create_shift(payload: ShiftTemplateCreateRequest):
    return await attendance_service.create_shift_template(
        session=cast(AsyncSession, object()), payload=payload
    )


async def _update_department_schedule(department_id: int, payload: DepartmentScheduleUpdateRequest):
    return await attendance_service.update_department_schedule(
        session=cast(AsyncSession, object()),
        department_id=department_id,
        payload=payload,
    )


async def _fake_get_department_with_shifts(session, department_id: int):
    return FakeDepartmentRepository.departments[department_id]


async def _sync_device_attendance(
    device_user_id: int,
    timestamp: datetime,
    punch: Literal["IN", "OUT"],
    raw_event_id: str | None = None,
):
    return await attendance_service.sync_device_attendance(
        session=cast(AsyncSession, object()),
        device_user_id=device_user_id,
        timestamp=timestamp,
        punch=punch,
        raw_event_id=raw_event_id,
    )


async def _create_attendance_record(payload: AttendanceRecordCreateRequest):
    return await attendance_service.create_attendance_record(
        session=cast(AsyncSession, object()),
        payload=payload,
    )


async def _update_attendance_record(record_id: int, payload: AttendanceRecordUpdateRequest):
    return await attendance_service.update_attendance_record(
        session=cast(AsyncSession, object()),
        record_id=record_id,
        payload=payload,
    )


async def _create_holiday(payload: HolidayCreateRequest):
    return await attendance_service.create_holiday(
        session=cast(AsyncSession, object()),
        payload=payload,
    )


async def _create_overtime(payload: OvertimeRequestCreateRequest):
    return await attendance_service.create_overtime_request(
        session=cast(AsyncSession, object()),
        current_user=FakeUserRepository.users[payload.user_id],
        payload=payload,
    )


async def _respond_overtime(overtime_id: int, approver_id: UUID, payload: OvertimeRequestRespondRequest):
    return await attendance_service.respond_to_overtime_request(
        session=cast(AsyncSession, object()),
        overtime_id=overtime_id,
        approver_id=approver_id,
        payload=payload,
    )


async def _create_swap(payload: ShiftSwapRequestCreateRequest):
    return await attendance_service.create_shift_swap_request(
        session=cast(AsyncSession, object()),
        payload=payload,
    )


async def _respond_swap(swap_id: int, approver_id: UUID, payload: ShiftSwapRequestRespondRequest):
    return await attendance_service.respond_to_shift_swap_request(
        session=cast(AsyncSession, object()),
        swap_id=swap_id,
        approver_id=approver_id,
        payload=payload,
    )


async def _summary(user_id: UUID, year: int, month: int) -> AttendanceSummaryRead:
    return await attendance_service.get_attendance_summary(
        session=cast(AsyncSession, object()),
        user_id=user_id,
        year=year,
        month=month,
    )


async def _create_employee_shift_assignment(date_value: date, user_id: UUID, shift_id: int):
    return await attendance_service.create_employee_shift_assignment(
        session=cast(AsyncSession, object()),
        payload=attendance_service.EmployeeShiftAssignmentCreateRequest(
            date=date_value,
            user_id=user_id,
            shift_id=shift_id,
        ),
    )


async def _copy_previous_month_shift_assignments(user_id: UUID, year: int, month: int):
    return await attendance_service.copy_previous_month_employee_shift_assignments(
        session=cast(AsyncSession, object()),
        payload=attendance_service.EmployeeShiftAssignmentCopyPreviousMonthRequest(
            user_id=user_id,
            year=year,
            month=month,
        ),
    )


async def _generate_month_shift_assignments(
    user_id: UUID, year: int, month: int, shift_id: int | None = None
):
    return await attendance_service.generate_month_employee_shift_assignments(
        session=cast(AsyncSession, object()),
        payload=attendance_service.EmployeeShiftAssignmentGenerateMonthRequest(
            user_id=user_id,
            year=year,
            month=month,
            shift_id=shift_id,
        ),
    )


def setup_function():
    FakeUserRepository.users = {}
    FakeDepartmentRepository.departments = {}
    FakeShiftTemplateRepository.shifts = {}
    FakeShiftTemplateRepository.next_id = 1
    FakeAttendanceRecordRepository.records = {}
    FakeAttendanceRecordRepository.deleted_raw_event_ids = set()
    FakeAttendanceRecordRepository.next_id = 1
    FakeEmployeeShiftAssignmentRepository.schedules = {}
    FakeEmployeeShiftAssignmentRepository.next_id = 1
    FakeDepartmentRosterDayRepository.records = {}
    FakeDepartmentRosterDayRepository.next_id = 1
    FakeHolidayRepository.holidays = {}
    FakeHolidayRepository.next_id = 1
    FakeLeaveRequestRepository.leave_requests = {}
    FakeOvertimeRepository.overtime_requests = {}
    FakeOvertimeRepository.next_id = 1
    FakeOvertimeRepository.next_assignment_id = 1
    FakeOvertimeApproverRepository.overtime_approvers = {}
    FakeOvertimeApproverRepository.next_id = 1
    FakeShiftSwapRepository.swaps = {}
    FakeShiftSwapRepository.next_id = 1


def _make_department(department_id: int, name: str = "Accounting"):
    department = Department(
        id=department_id,
        name=name,
        code=name[:3].upper(),
        workweek=["Monday", "Tuesday"],
        is_active=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    department.shift_templates = []
    department.department_roster_days = []
    return department


def _make_user(
    user_id: UUID,
    department: Department | None = None,
    biometric_uid: int | None = None,
    role: str | None = None,
):
    user = User(
        id=user_id,
        email=f"user{user_id}@example.com",
        password_hash="hashed",
        first_name="User",
        last_name=str(user_id),
        biometric_uid=biometric_uid,
        role=role,
        department_id=department.id if department else None,
        department=department,
        can_modify_shift=False,
        is_active=True,
        is_superuser=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    return user


def _make_shift(shift_id: int, description: str = "Morning"):
    return ShiftTemplate(
        id=shift_id,
        description=description,
        start_time=time(8, 0),
        end_time=time(17, 0),
        start_time_2=None,
        end_time_2=None,
        is_active=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )


def test_create_shift_and_reject_duplicate(monkeypatch):
    monkeypatch.setattr(attendance_service, "ShiftTemplateRepository", FakeShiftTemplateRepository)

    response = anyio.run(
        _create_shift,
        ShiftTemplateCreateRequest(
            description="Morning",
            start_time=time(8, 0),
            end_time=time(17, 0),
        ),
    )

    assert response.id == 1
    assert response.description == "Morning"

    try:
        anyio.run(
            _create_shift,
            ShiftTemplateCreateRequest(
                description="Morning",
                start_time=time(8, 0),
                end_time=time(17, 0),
            ),
        )
    except ConflictError:
        pass
    else:
        raise AssertionError("Expected ConflictError")


def test_update_department_schedule_sets_workweek_and_shifts(monkeypatch):
    department = _make_department(1)
    shift = _make_shift(1)
    FakeDepartmentRepository.departments = {department.id: department}
    FakeShiftTemplateRepository.shifts = {shift.id: shift}

    monkeypatch.setattr(attendance_service, "DepartmentRepository", FakeDepartmentRepository)
    monkeypatch.setattr(attendance_service, "ShiftTemplateRepository", FakeShiftTemplateRepository)
    monkeypatch.setattr(attendance_service, "_get_department_with_shifts", _fake_get_department_with_shifts)

    response = anyio.run(
        _update_department_schedule,
        1,
        DepartmentScheduleUpdateRequest(workweek=["Monday", "Wednesday"], shift_ids=[1]),
    )

    assert response.workweek == ["Monday", "Wednesday"]
    assert response.shifts[0].id == 1


def test_create_employee_shift_assignment_rejects_duplicate(monkeypatch):
    department = _make_department(1)
    user = _make_user(UUID(int=1), department=department)
    shift = _make_shift(1)
    existing = EmployeeShiftAssignment(
        id=1,
        date=date(2026, 3, 24),
        user=user,
        user_id=user.id,
        shift_template=shift,
        shift_template_id=shift.id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    FakeUserRepository.users = {user.id: user}
    FakeShiftTemplateRepository.shifts = {shift.id: shift}
    FakeEmployeeShiftAssignmentRepository.schedules = {existing.id: existing}

    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(attendance_service, "ShiftTemplateRepository", FakeShiftTemplateRepository)
    monkeypatch.setattr(
        attendance_service,
        "EmployeeShiftAssignmentRepository",
        FakeEmployeeShiftAssignmentRepository,
    )

    try:
        anyio.run(_create_employee_shift_assignment, date(2026, 3, 24), user.id, shift.id)
    except ConflictError:
        pass
    else:
        raise AssertionError("Expected ConflictError")


def test_copy_previous_month_shift_assignments(monkeypatch):
    department = _make_department(1)
    user = _make_user(UUID(int=1), department=department)
    source_shift_one = _make_shift(1, "Morning")
    source_shift_two = _make_shift(2, "Evening")
    target_shift = _make_shift(3, "Night")

    source_assignment_one = EmployeeShiftAssignment(
        id=1,
        date=date(2026, 2, 1),
        user=user,
        user_id=user.id,
        shift_template=source_shift_one,
        shift_template_id=source_shift_one.id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    source_assignment_two = EmployeeShiftAssignment(
        id=2,
        date=date(2026, 2, 15),
        user=user,
        user_id=user.id,
        shift_template=source_shift_two,
        shift_template_id=source_shift_two.id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    target_assignment = EmployeeShiftAssignment(
        id=3,
        date=date(2026, 3, 10),
        user=user,
        user_id=user.id,
        shift_template=target_shift,
        shift_template_id=target_shift.id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    FakeUserRepository.users = {user.id: user}
    FakeEmployeeShiftAssignmentRepository.schedules = {
        source_assignment_one.id: source_assignment_one,
        source_assignment_two.id: source_assignment_two,
        target_assignment.id: target_assignment,
    }
    FakeEmployeeShiftAssignmentRepository.next_id = 4

    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(
        attendance_service,
        "EmployeeShiftAssignmentRepository",
        FakeEmployeeShiftAssignmentRepository,
    )

    response = anyio.run(_copy_previous_month_shift_assignments, user.id, 2026, 3)

    assert response.copied_count == 2
    assert response.skipped_count == 0

    copied_assignments = sorted(
        [
            assignment
            for assignment in FakeEmployeeShiftAssignmentRepository.schedules.values()
            if assignment.date.year == 2026 and assignment.date.month == 3
        ],
        key=lambda item: item.date,
    )
    assert [assignment.date for assignment in copied_assignments] == [
        date(2026, 3, 1),
        date(2026, 3, 15),
    ]
    assert [assignment.shift_template_id for assignment in copied_assignments] == [1, 2]


def test_generate_month_shift_assignments_from_department_policy(monkeypatch):
    department = _make_department(1)
    department.workweek = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    primary_shift = _make_shift(1, "Morning")
    secondary_shift = _make_shift(2, "Night")
    department.shift_templates = [primary_shift, secondary_shift]
    user = _make_user(UUID(int=1), department=department)
    existing_assignment = EmployeeShiftAssignment(
        id=1,
        date=date(2026, 3, 3),
        user=user,
        user_id=user.id,
        shift_template=secondary_shift,
        shift_template_id=secondary_shift.id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    FakeUserRepository.users = {user.id: user}
    FakeDepartmentRepository.departments = {department.id: department}
    FakeEmployeeShiftAssignmentRepository.schedules = {existing_assignment.id: existing_assignment}
    FakeEmployeeShiftAssignmentRepository.next_id = 2

    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(attendance_service, "DepartmentRepository", FakeDepartmentRepository)
    monkeypatch.setattr(
        attendance_service,
        "EmployeeShiftAssignmentRepository",
        FakeEmployeeShiftAssignmentRepository,
    )

    response = anyio.run(_generate_month_shift_assignments, user.id, 2026, 3, primary_shift.id)

    assert response.generated_count > 0
    assert response.skipped_count == 1

    march_assignments = sorted(
        [
            assignment
            for assignment in FakeEmployeeShiftAssignmentRepository.schedules.values()
            if assignment.date.year == 2026 and assignment.date.month == 3
        ],
        key=lambda item: item.date,
    )
    assert any(
        assignment.date == date(2026, 3, 2) and assignment.shift_template_id == 1
        for assignment in march_assignments
    )
    assert any(assignment.date == date(2026, 3, 3) and assignment.shift_template_id == 2 for assignment in march_assignments)


def test_sync_device_attendance_uses_biometric_uid(monkeypatch):
    user = _make_user(UUID(int=1), biometric_uid=77)
    FakeUserRepository.users = {user.id: user}
    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(attendance_service, "AttendanceRecordRepository", FakeAttendanceRecordRepository)

    response = anyio.run(
        _sync_device_attendance,
        77,
        datetime(2026, 3, 24, 8, 0, tzinfo=UTC),
        "IN",
        "event-1",
    )

    assert response.user_id == UUID(int=1)
    assert response.device_user_id == 77
    assert response.raw_event_id == "event-1"


def test_create_and_update_attendance_record(monkeypatch):
    user = _make_user(UUID(int=1))
    FakeUserRepository.users = {user.id: user}
    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(attendance_service, "AttendanceRecordRepository", FakeAttendanceRecordRepository)

    created = anyio.run(
        _create_attendance_record,
        AttendanceRecordCreateRequest(
            user_id=UUID(int=1),
            device_user_id=5,
            timestamp=datetime(2026, 3, 24, 8, 0, tzinfo=UTC),
            punch="IN",
        ),
    )
    assert created.id == 1

    updated = anyio.run(
        _update_attendance_record,
        1,
        AttendanceRecordUpdateRequest(
            timestamp=datetime(2026, 3, 24, 17, 0, tzinfo=UTC),
            punch="OUT",
        ),
    )
    assert updated.punch == "OUT"


def test_create_attendance_record_rejects_duplicate_raw_event_id(monkeypatch):
    user = _make_user(UUID(int=1))
    FakeUserRepository.users = {user.id: user}
    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(attendance_service, "AttendanceRecordRepository", FakeAttendanceRecordRepository)

    created = anyio.run(
        _create_attendance_record,
        AttendanceRecordCreateRequest(
            user_id=UUID(int=1),
            device_user_id=5,
            raw_event_id="raw-duplicate-check",
            timestamp=datetime(2026, 3, 24, 8, 0, tzinfo=UTC),
            punch="IN",
        ),
    )
    assert created.raw_event_id == "raw-duplicate-check"

    try:
        anyio.run(
            _create_attendance_record,
            AttendanceRecordCreateRequest(
                user_id=UUID(int=1),
                device_user_id=5,
                raw_event_id="raw-duplicate-check",
                timestamp=datetime(2026, 3, 24, 8, 1, tzinfo=UTC),
                punch="OUT",
            ),
        )
    except ConflictError:
        pass
    else:
        raise AssertionError("Expected ConflictError")


def test_create_attendance_record_rejects_deleted_raw_event_id(monkeypatch):
    user = _make_user(UUID(int=1))
    FakeUserRepository.users = {user.id: user}
    FakeAttendanceRecordRepository.deleted_raw_event_ids = {"raw-deleted-check"}
    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(attendance_service, "AttendanceRecordRepository", FakeAttendanceRecordRepository)

    try:
        anyio.run(
            _create_attendance_record,
            AttendanceRecordCreateRequest(
                user_id=UUID(int=1),
                device_user_id=5,
                raw_event_id="raw-deleted-check",
                timestamp=datetime(2026, 3, 24, 8, 0, tzinfo=UTC),
                punch="IN",
            ),
        )
    except ConflictError as exc:
        assert str(exc) == "Attendance record was deleted and cannot be restored."
    else:
        raise AssertionError("Expected ConflictError")


def test_delete_attendance_record_preserves_raw_event_id_tombstone(monkeypatch):
    user = _make_user(UUID(int=1))
    record = AttendanceRecord(
        id=1,
        user_id=user.id,
        device_user_id=5,
        raw_event_id="raw-delete-me",
        timestamp=datetime(2026, 3, 24, 8, 0, tzinfo=UTC),
        punch="IN",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    FakeUserRepository.users = {user.id: user}
    FakeAttendanceRecordRepository.records = {record.id: record}
    monkeypatch.setattr(attendance_service, "AttendanceRecordRepository", FakeAttendanceRecordRepository)

    anyio.run(attendance_service.delete_attendance_record, cast(AsyncSession, object()), 1)

    assert 1 not in FakeAttendanceRecordRepository.records
    assert "raw-delete-me" in FakeAttendanceRecordRepository.deleted_raw_event_ids


def test_create_holiday_and_overtime_flow(monkeypatch):
    department = _make_department(1)
    user = _make_user(UUID(int=1), department=department)
    approver = _make_user(UUID(int=2), department=department, role="DH")
    FakeUserRepository.users = {user.id: user, approver.id: approver}
    FakeDepartmentRepository.departments = {department.id: department}
    FakeOvertimeApproverRepository.overtime_approvers = {
        department.id: OvertimeApprover(
            id=1,
            department_id=department.id,
            department_approver_id=approver.id,
            director_approver_id=None,
            president_approver_id=None,
            hr_approver_id=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    }
    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(attendance_service, "DepartmentRepository", FakeDepartmentRepository)
    monkeypatch.setattr(attendance_service, "HolidayRepository", FakeHolidayRepository)
    monkeypatch.setattr(
        attendance_service, "OvertimeApproverRepository", FakeOvertimeApproverRepository
    )
    monkeypatch.setattr(attendance_service, "OvertimeRepository", FakeOvertimeRepository)
    monkeypatch.setattr(attendance_service, "LeaveRequestRepository", FakeLeaveRequestRepository)
    monkeypatch.setattr(attendance_service, "LeaveRequestRepository", FakeLeaveRequestRepository)
    monkeypatch.setattr(attendance_service, "LeaveRequestRepository", FakeLeaveRequestRepository)

    holiday = anyio.run(
        _create_holiday,
        HolidayCreateRequest(name="Holiday", day=25, month=12, year=2026),
    )
    assert holiday.id == 1

    overtime = anyio.run(
        _create_overtime,
        OvertimeRequestCreateRequest(
            user_id=UUID(int=1), info="Support", date=date(2026, 3, 24)
        ),
    )
    assert overtime.id == 1
    assert overtime.approver_id == approver.id
    assert [item.approver_id for item in overtime.approver_pool] == [approver.id]

    approved = anyio.run(
        _respond_overtime,
        1,
        UUID(int=2),
        OvertimeRequestRespondRequest(response="APPROVE"),
    )
    assert approved.status == OvertimeRequest.Status.APPROVED.value
    assert len([item for item in approved.approver_pool if item.acted_at is not None]) == 1


def test_cancel_overtime_request_marks_pending_request_cancelled(monkeypatch):
    department = _make_department(1)
    user = _make_user(UUID(int=1), department=department)
    approver = _make_user(UUID(int=2), department=department, role="DH")
    FakeUserRepository.users = {user.id: user, approver.id: approver}
    FakeOvertimeApproverRepository.overtime_approvers = {
        department.id: OvertimeApprover(
            id=1,
            department_id=department.id,
            department_approver_id=approver.id,
            director_approver_id=None,
            president_approver_id=None,
            hr_approver_id=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    }

    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(
        attendance_service, "OvertimeApproverRepository", FakeOvertimeApproverRepository
    )
    monkeypatch.setattr(attendance_service, "OvertimeRepository", FakeOvertimeRepository)
    monkeypatch.setattr(attendance_service, "LeaveRequestRepository", FakeLeaveRequestRepository)

    overtime = anyio.run(
        _create_overtime,
        OvertimeRequestCreateRequest(
            user_id=user.id,
            info="Support",
            date=date(2026, 3, 24),
        ),
    )

    cancelled = anyio.run(
        attendance_service.cancel_overtime_request,
        cast(AsyncSession, object()),
        overtime.id,
        user,
    )
    assert cancelled.status == OvertimeRequest.Status.CANCELLED.value
    assert all(
        assignment.status == OvertimeRequest.Status.CANCELLED.value
        for assignment in cancelled.approver_pool
    )
    assert FakeOvertimeRepository.overtime_requests[overtime.id].status == (
        OvertimeRequest.Status.CANCELLED.value
    )


def test_cancel_overtime_request_rejects_other_user(monkeypatch):
    department = _make_department(1)
    user = _make_user(UUID(int=1), department=department)
    approver = _make_user(UUID(int=2), department=department, role="DH")
    other_user = _make_user(UUID(int=3), department=department)
    FakeUserRepository.users = {
        user.id: user,
        approver.id: approver,
        other_user.id: other_user,
    }
    FakeOvertimeApproverRepository.overtime_approvers = {
        department.id: OvertimeApprover(
            id=1,
            department_id=department.id,
            department_approver_id=approver.id,
            director_approver_id=None,
            president_approver_id=None,
            hr_approver_id=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    }

    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(
        attendance_service, "OvertimeApproverRepository", FakeOvertimeApproverRepository
    )
    monkeypatch.setattr(attendance_service, "OvertimeRepository", FakeOvertimeRepository)
    monkeypatch.setattr(attendance_service, "LeaveRequestRepository", FakeLeaveRequestRepository)

    overtime = anyio.run(
        _create_overtime,
        OvertimeRequestCreateRequest(
            user_id=user.id,
            info="Support",
            date=date(2026, 3, 24),
        ),
    )

    try:
        anyio.run(
            attendance_service.cancel_overtime_request,
            cast(AsyncSession, object()),
            overtime.id,
            other_user,
        )
    except attendance_service.PermissionDeniedError as exc:
        assert exc.detail == "You are not allowed to cancel this overtime request."
    else:
        raise AssertionError("Expected PermissionDeniedError")


def test_create_overtime_request_rejects_same_day_active_overtime(monkeypatch):
    department = _make_department(1)
    user = _make_user(UUID(int=1), department=department)
    approver = _make_user(UUID(int=2), department=department, role="DH")
    FakeUserRepository.users = {user.id: user, approver.id: approver}
    FakeOvertimeApproverRepository.overtime_approvers = {
        department.id: OvertimeApprover(
            id=1,
            department_id=department.id,
            department_approver_id=approver.id,
            director_approver_id=None,
            president_approver_id=None,
            hr_approver_id=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    }
    FakeLeaveRequestRepository.leave_requests = {}

    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(
        attendance_service, "OvertimeApproverRepository", FakeOvertimeApproverRepository
    )
    monkeypatch.setattr(attendance_service, "OvertimeRepository", FakeOvertimeRepository)
    monkeypatch.setattr(attendance_service, "LeaveRequestRepository", FakeLeaveRequestRepository)
    monkeypatch.setattr(attendance_service, "LeaveRequestRepository", FakeLeaveRequestRepository)

    anyio.run(
        _create_overtime,
        OvertimeRequestCreateRequest(user_id=user.id, info="First", date=date(2026, 3, 24)),
    )

    with pytest.raises(attendance_service.ConflictError, match="active overtime request already exists"):
        anyio.run(
            _create_overtime,
            OvertimeRequestCreateRequest(user_id=user.id, info="Second", date=date(2026, 3, 24)),
        )


def test_create_overtime_request_rejects_same_day_active_leave(monkeypatch):
    department = _make_department(1)
    user = _make_user(UUID(int=1), department=department)
    approver = _make_user(UUID(int=2), department=department, role="DH")
    FakeUserRepository.users = {user.id: user, approver.id: approver}
    FakeOvertimeApproverRepository.overtime_approvers = {
        department.id: OvertimeApprover(
            id=1,
            department_id=department.id,
            department_approver_id=approver.id,
            director_approver_id=None,
            president_approver_id=None,
            hr_approver_id=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    }
    FakeLeaveRequestRepository.leave_requests = {
        1: LeaveRequest(
            id=1,
            user_id=user.id,
            leave_date=date(2026, 3, 24),
            leave_type="PA",
            info="Leave",
            first_approver_id=approver.id,
            first_approver_status=LeaveRequestStatus.PENDING.value,
            first_approver_at=None,
            second_approver_id=None,
            second_approver_status=None,
            second_approver_at=None,
            status=LeaveRequestStatus.PENDING.value,
            approver_pool=[],
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    }

    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(
        attendance_service, "OvertimeApproverRepository", FakeOvertimeApproverRepository
    )
    monkeypatch.setattr(attendance_service, "OvertimeRepository", FakeOvertimeRepository)
    monkeypatch.setattr(attendance_service, "LeaveRequestRepository", FakeLeaveRequestRepository)

    with pytest.raises(attendance_service.ConflictError, match="active leave request already exists"):
        anyio.run(
            _create_overtime,
            OvertimeRequestCreateRequest(user_id=user.id, info="OT", date=date(2026, 3, 24)),
        )


def test_create_holiday_rejects_duplicate_specific_date(monkeypatch):
    FakeHolidayRepository.holidays = {
        1: Holiday(
            id=1,
            name="Founding Day",
            day=12,
            month=6,
            year=2026,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    }
    monkeypatch.setattr(attendance_service, "HolidayRepository", FakeHolidayRepository)

    try:
        anyio.run(
            _create_holiday,
            HolidayCreateRequest(name="Duplicate", day=12, month=6, year=2026),
        )
    except ConflictError as exc:
        assert exc.detail == "A holiday already exists for this date."
    else:
        raise AssertionError("Expected ConflictError for duplicate holiday date.")


def test_create_holiday_rejects_overlap_with_recurring_holiday(monkeypatch):
    FakeHolidayRepository.holidays = {
        1: Holiday(
            id=1,
            name="Christmas Day",
            day=25,
            month=12,
            year=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    }
    monkeypatch.setattr(attendance_service, "HolidayRepository", FakeHolidayRepository)

    try:
        anyio.run(
            _create_holiday,
            HolidayCreateRequest(
                name="Christmas 2026",
                day=25,
                month=12,
                year=2026,
            ),
        )
    except ConflictError as exc:
        assert exc.detail == "A recurring holiday already exists for this date."
    else:
        raise AssertionError("Expected ConflictError for recurring holiday overlap.")


def test_update_holiday_rejects_conflicting_date(monkeypatch):
    FakeHolidayRepository.holidays = {
        1: Holiday(
            id=1,
            name="New Year's Day",
            day=1,
            month=1,
            year=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        ),
        2: Holiday(
            id=2,
            name="Local Holiday",
            day=2,
            month=1,
            year=2026,
            created_at=utc_now(),
            updated_at=utc_now(),
        ),
    }
    monkeypatch.setattr(attendance_service, "HolidayRepository", FakeHolidayRepository)

    try:
        anyio.run(
            attendance_service.update_holiday,
            cast(AsyncSession, object()),
            2,
            attendance_service.HolidayUpdateRequest(day=1, month=1, year=2026),
        )
    except ConflictError as exc:
        assert exc.detail == "A recurring holiday already exists for this date."
    else:
        raise AssertionError("Expected ConflictError when moving holiday onto recurring date.")


def test_create_overtime_fails_without_configured_approver(monkeypatch):
    department = _make_department(1)
    user = _make_user(UUID(int=1), department=department)
    FakeUserRepository.users = {user.id: user}

    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(attendance_service, "OvertimeRepository", FakeOvertimeRepository)
    monkeypatch.setattr(attendance_service, "LeaveRequestRepository", FakeLeaveRequestRepository)

    try:
        anyio.run(
            _create_overtime,
            OvertimeRequestCreateRequest(
                user_id=UUID(int=1), info="Support", date=date(2026, 3, 24)
            ),
        )
    except NotFoundError as exc:
        assert str(exc) == "No Level 1 approver is configured for this user."
    else:
        raise AssertionError("Expected overtime creation to fail without approver settings.")


def test_shift_swap_flow(monkeypatch):
    requester = _make_user(UUID(int=1))
    target = _make_user(UUID(int=2))
    approver = _make_user(UUID(int=3))
    FakeUserRepository.users = {requester.id: requester, target.id: target, approver.id: approver}
    schedule_one = EmployeeShiftAssignment(
        id=1,
        date=date(2026, 3, 24),
        user=requester,
        user_id=requester.id,
        shift_template_id=1,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    schedule_two = EmployeeShiftAssignment(
        id=2,
        date=date(2026, 3, 24),
        user=target,
        user_id=target.id,
        shift_template_id=2,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    FakeEmployeeShiftAssignmentRepository.schedules = {1: schedule_one, 2: schedule_two}
    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(
        attendance_service,
        "EmployeeShiftAssignmentRepository",
        FakeEmployeeShiftAssignmentRepository,
    )
    monkeypatch.setattr(attendance_service, "ShiftSwapRepository", FakeShiftSwapRepository)

    created = anyio.run(
        _create_swap,
        ShiftSwapRequestCreateRequest(
            requested_by_id=UUID(int=1),
            requested_for_id=UUID(int=2),
            current_schedule_id=1,
            requested_schedule_id=2,
            approver_id=UUID(int=3),
            info="Swap request",
        ),
    )
    assert created.id == 1

    approved = anyio.run(
        _respond_swap,
        1,
        UUID(int=3),
        ShiftSwapRequestRespondRequest(response="APPROVE"),
    )
    assert approved.status == ShiftSwapRequest.Status.APPROVED.value


def test_attendance_summary_groups_days(monkeypatch):
    department = _make_department(1)
    user = _make_user(UUID(int=1), department=department)
    shift = _make_shift(1)
    record = AttendanceRecord(
        id=1,
        user_id=UUID(int=1),
        device_user_id=77,
        timestamp=datetime(2026, 3, 24, 8, 0, tzinfo=UTC),
        punch="IN",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    schedule = EmployeeShiftAssignment(
        id=1,
        date=date(2026, 3, 24),
        user=user,
        user_id=user.id,
        shift_template=shift,
        shift_template_id=shift.id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    daily_record = DepartmentRosterDay(
        id=1,
        date=date(2026, 3, 24),
        department_id=department.id,
        department=department,
        is_approved=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    daily_record.employee_shift_assignments = [schedule]
    holiday = Holiday(
        id=1,
        name="Holiday",
        day=24,
        month=3,
        year=2026,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    overtime = OvertimeRequest(
        id=1,
        user_id=UUID(int=1),
        approver_id=UUID(int=2),
        info="Support",
        date=date(2026, 3, 24),
        status=OvertimeRequest.Status.APPROVED.value,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    leave_request = LeaveRequest(
        id=1,
        user_id=UUID(int=1),
        leave_date=date(2026, 3, 24),
        leave_type="PA",
        info="Medical appointment",
        first_approver_id=UUID(int=2),
        first_approver_status=LeaveRequestStatus.APPROVED.value,
        first_approver_at=utc_now(),
        second_approver_id=None,
        second_approver_status=None,
        second_approver_at=None,
        status=LeaveRequestStatus.APPROVED.value,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    FakeUserRepository.users = {user.id: user}
    FakeEmployeeShiftAssignmentRepository.schedules = {schedule.id: schedule}
    FakeAttendanceRecordRepository.records = {record.id: record}
    FakeHolidayRepository.holidays = {holiday.id: holiday}
    FakeLeaveRequestRepository.leave_requests = {leave_request.id: leave_request}
    FakeOvertimeRepository.overtime_requests = {overtime.id: overtime}

    monkeypatch.setattr(attendance_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(
        attendance_service,
        "EmployeeShiftAssignmentRepository",
        FakeEmployeeShiftAssignmentRepository,
    )
    monkeypatch.setattr(attendance_service, "AttendanceRecordRepository", FakeAttendanceRecordRepository)
    monkeypatch.setattr(attendance_service, "HolidayRepository", FakeHolidayRepository)
    monkeypatch.setattr(attendance_service, "LeaveRequestRepository", FakeLeaveRequestRepository)
    monkeypatch.setattr(attendance_service, "OvertimeRepository", FakeOvertimeRepository)

    response = anyio.run(_summary, UUID(int=1), 2026, 3)

    assert isinstance(response, AttendanceSummaryRead)
    assert len(response.days) == 31
    assert response.days[23].attendance_records[0].id == 1
    assert response.days[23].holidays[0].name == "Holiday"
    assert response.days[23].overtime_approved is True
    assert response.days[23].approved_leave is not None
    assert response.days[23].approved_leave.leave_type == "PA"
