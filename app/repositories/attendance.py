from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.attendance import (
    AttendanceRecord,
    DepartmentRosterDay,
    EmployeeShiftAssignment,
    Holiday,
    OvertimeRequest,
    ShiftTemplate,
    ShiftSwapRequest,
)
from app.models.user import User


class ShiftTemplateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self) -> list[ShiftTemplate]:
        result = await self.session.execute(select(ShiftTemplate).order_by(ShiftTemplate.description))
        return list(result.scalars().all())

    async def get_by_id(self, shift_id: int) -> ShiftTemplate | None:
        result = await self.session.execute(select(ShiftTemplate).where(ShiftTemplate.id == shift_id))
        return result.scalar_one_or_none()

    async def get_by_identity(
        self,
        description: str,
        start_time,
        end_time,
        start_time_2=None,
        end_time_2=None,
    ) -> ShiftTemplate | None:
        result = await self.session.execute(
            select(ShiftTemplate).where(
                ShiftTemplate.description == description,
                ShiftTemplate.start_time == start_time,
                ShiftTemplate.end_time == end_time,
                ShiftTemplate.start_time_2 == start_time_2,
                ShiftTemplate.end_time_2 == end_time_2,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, shift: ShiftTemplate) -> ShiftTemplate:
        self.session.add(shift)
        await self.session.commit()
        await self.session.refresh(shift)
        return shift

    async def save(self, shift: ShiftTemplate) -> ShiftTemplate:
        await self.session.commit()
        await self.session.refresh(shift)
        return shift

    async def delete(self, shift: ShiftTemplate) -> None:
        await self.session.delete(shift)
        await self.session.commit()


class AttendanceRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user_range(
        self, user_id: int, start: datetime, end: datetime
    ) -> list[AttendanceRecord]:
        result = await self.session.execute(
            select(AttendanceRecord)
            .where(
                AttendanceRecord.user_id == user_id,
                AttendanceRecord.timestamp >= start,
                AttendanceRecord.timestamp <= end,
            )
            .order_by(AttendanceRecord.timestamp)
        )
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> AttendanceRecord | None:
        result = await self.session.execute(
            select(AttendanceRecord).where(AttendanceRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_duplicate(
        self, user_id: int, timestamp: datetime, punch: str
    ) -> AttendanceRecord | None:
        result = await self.session.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.user_id == user_id,
                AttendanceRecord.timestamp == timestamp,
                AttendanceRecord.punch == punch,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, record: AttendanceRecord) -> AttendanceRecord:
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def save(self, record: AttendanceRecord) -> AttendanceRecord:
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def delete(self, record: AttendanceRecord) -> None:
        await self.session.delete(record)
        await self.session.commit()


class EmployeeShiftAssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_department_month(
        self, department_id: int, year: int, month: int
    ) -> list[EmployeeShiftAssignment]:
        result = await self.session.execute(
            select(EmployeeShiftAssignment)
            .options(
                selectinload(EmployeeShiftAssignment.shift_template),
                selectinload(EmployeeShiftAssignment.user).selectinload(User.department),
            )
            .join(EmployeeShiftAssignment.user)
            .where(
                EmployeeShiftAssignment.date >= date(year, month, 1),
                EmployeeShiftAssignment.date < date(year + (month // 12), ((month % 12) + 1), 1),
                EmployeeShiftAssignment.user.has(department_id=department_id),
            )
            .order_by(EmployeeShiftAssignment.date)
        )
        return list(result.scalars().all())

    async def list_for_user_month(
        self, user_id: int, year: int, month: int
    ) -> list[EmployeeShiftAssignment]:
        result = await self.session.execute(
            select(EmployeeShiftAssignment)
            .options(
                selectinload(EmployeeShiftAssignment.shift_template),
                selectinload(EmployeeShiftAssignment.user).selectinload(User.department),
            )
            .where(
                EmployeeShiftAssignment.user_id == user_id,
                EmployeeShiftAssignment.date >= date(year, month, 1),
                EmployeeShiftAssignment.date < date(year + (month // 12), ((month % 12) + 1), 1),
            )
            .order_by(EmployeeShiftAssignment.date)
        )
        return list(result.scalars().all())

    async def get_by_id(self, schedule_id: int) -> EmployeeShiftAssignment | None:
        result = await self.session.execute(
            select(EmployeeShiftAssignment)
            .options(
                selectinload(EmployeeShiftAssignment.shift_template),
                selectinload(EmployeeShiftAssignment.user).selectinload(User.department),
            )
            .where(EmployeeShiftAssignment.id == schedule_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_date(
        self, user_id: int, selected_date: date
    ) -> EmployeeShiftAssignment | None:
        result = await self.session.execute(
            select(EmployeeShiftAssignment).where(
                EmployeeShiftAssignment.user_id == user_id,
                EmployeeShiftAssignment.date == selected_date,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, schedule: EmployeeShiftAssignment) -> EmployeeShiftAssignment:
        self.session.add(schedule)
        await self.session.commit()
        loaded = await self.get_by_id(schedule.id)
        return loaded if loaded is not None else schedule

    async def save(self, schedule: EmployeeShiftAssignment) -> EmployeeShiftAssignment:
        await self.session.commit()
        loaded = await self.get_by_id(schedule.id)
        return loaded if loaded is not None else schedule

    async def delete(self, schedule: EmployeeShiftAssignment) -> None:
        await self.session.delete(schedule)
        await self.session.commit()


class DepartmentRosterDayRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_department_date(
        self, department_id: int, selected_date: date
    ) -> DepartmentRosterDay | None:
        result = await self.session.execute(
            select(DepartmentRosterDay)
            .options(selectinload(DepartmentRosterDay.employee_shift_assignments))
            .where(
                DepartmentRosterDay.department_id == department_id,
                DepartmentRosterDay.date == selected_date,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_department_month(
        self, department_id: int, year: int, month: int
    ) -> list[DepartmentRosterDay]:
        result = await self.session.execute(
            select(DepartmentRosterDay)
            .options(selectinload(DepartmentRosterDay.employee_shift_assignments))
            .where(
                DepartmentRosterDay.department_id == department_id,
                DepartmentRosterDay.date >= date(year, month, 1),
                DepartmentRosterDay.date < date(year + (month // 12), ((month % 12) + 1), 1),
            )
            .order_by(DepartmentRosterDay.date)
        )
        return list(result.scalars().all())

    async def create(self, record: DepartmentRosterDay) -> DepartmentRosterDay:
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def save(self, record: DepartmentRosterDay) -> DepartmentRosterDay:
        await self.session.commit()
        await self.session.refresh(record)
        return record


class HolidayRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, year: int | None = None) -> list[Holiday]:
        statement = select(Holiday).order_by(Holiday.year.desc(), Holiday.month.desc(), Holiday.day.desc())
        if year is not None:
            statement = statement.where((Holiday.year == year) | (Holiday.is_regular.is_(True)))
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, holiday_id: int) -> Holiday | None:
        result = await self.session.execute(select(Holiday).where(Holiday.id == holiday_id))
        return result.scalar_one_or_none()

    async def create(self, holiday: Holiday) -> Holiday:
        self.session.add(holiday)
        await self.session.commit()
        await self.session.refresh(holiday)
        return holiday

    async def save(self, holiday: Holiday) -> Holiday:
        await self.session.commit()
        await self.session.refresh(holiday)
        return holiday

    async def delete(self, holiday: Holiday) -> None:
        await self.session.delete(holiday)
        await self.session.commit()


class OvertimeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _base_statement():
        return select(OvertimeRequest).options(
            selectinload(OvertimeRequest.user).selectinload(User.department),
            selectinload(OvertimeRequest.approver),
        )

    async def list_for_user(self, user_id: int) -> list[OvertimeRequest]:
        statement = self._base_statement().where(OvertimeRequest.user_id == user_id)
        statement = statement.order_by(OvertimeRequest.date.desc(), OvertimeRequest.id.desc())
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_for_approver(self, approver_id: int) -> list[OvertimeRequest]:
        statement = self._base_statement().where(OvertimeRequest.approver_id == approver_id)
        statement = statement.order_by(OvertimeRequest.date.desc(), OvertimeRequest.id.desc())
        result = await self.session.execute(statement)
        return list(result.scalars().all())

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
    ) -> list[OvertimeRequest]:
        statement = self._base_statement()

        if user_id is not None:
            statement = statement.where(OvertimeRequest.user_id == user_id)
        if approver_id is not None:
            statement = statement.where(OvertimeRequest.approver_id == approver_id)
        if year is not None:
            statement = statement.where(func.extract("year", OvertimeRequest.date) == year)
        if month is not None:
            statement = statement.where(func.extract("month", OvertimeRequest.date) == month)
        if status is not None:
            statement = statement.where(OvertimeRequest.status == status)
        if department_id is not None:
            statement = statement.where(OvertimeRequest.user.has(User.department_id == department_id))
        if query:
            lowered = f"%{query.lower()}%"
            statement = statement.where(
                OvertimeRequest.user.has(
                    func.lower(User.first_name).like(lowered)
                    | func.lower(User.last_name).like(lowered)
                    | func.lower(User.email).like(lowered)
                )
            )

        statement = statement.order_by(
            OvertimeRequest.status.asc(),
            OvertimeRequest.date.desc(),
            OvertimeRequest.id.desc(),
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, overtime_id: int) -> OvertimeRequest | None:
        result = await self.session.execute(
            select(OvertimeRequest).where(OvertimeRequest.id == overtime_id)
        )
        return result.scalar_one_or_none()

    async def create(self, overtime: OvertimeRequest) -> OvertimeRequest:
        self.session.add(overtime)
        await self.session.commit()
        await self.session.refresh(overtime)
        return overtime

    async def save(self, overtime: OvertimeRequest) -> OvertimeRequest:
        await self.session.commit()
        await self.session.refresh(overtime)
        return overtime

    async def delete(self, overtime: OvertimeRequest) -> None:
        await self.session.delete(overtime)
        await self.session.commit()


class ShiftSwapRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: int) -> list[ShiftSwapRequest]:
        result = await self.session.execute(
            select(ShiftSwapRequest)
            .where(
                (ShiftSwapRequest.requested_by_id == user_id)
                | (ShiftSwapRequest.requested_for_id == user_id)
            )
            .order_by(ShiftSwapRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_for_approver(self, approver_id: int) -> list[ShiftSwapRequest]:
        result = await self.session.execute(
            select(ShiftSwapRequest)
            .where(ShiftSwapRequest.approver_id == approver_id)
            .order_by(ShiftSwapRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, swap_id: int) -> ShiftSwapRequest | None:
        result = await self.session.execute(
            select(ShiftSwapRequest).where(ShiftSwapRequest.id == swap_id)
        )
        return result.scalar_one_or_none()

    async def create(self, swap: ShiftSwapRequest) -> ShiftSwapRequest:
        self.session.add(swap)
        await self.session.commit()
        await self.session.refresh(swap)
        return swap

    async def save(self, swap: ShiftSwapRequest) -> ShiftSwapRequest:
        await self.session.commit()
        await self.session.refresh(swap)
        return swap

    async def delete(self, swap: ShiftSwapRequest) -> None:
        await self.session.delete(swap)
        await self.session.commit()


ShiftRepository = ShiftTemplateRepository
DailyShiftScheduleRepository = EmployeeShiftAssignmentRepository
DailyShiftRecordRepository = DepartmentRosterDayRepository
