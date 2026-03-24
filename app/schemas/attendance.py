from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.schemas.department import DepartmentRead
from app.schemas.user import UserRead


class ShiftRead(BaseModel):
    id: int
    description: str
    start_time: time | None = None
    end_time: time | None = None
    start_time_2: time | None = None
    end_time_2: time | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DepartmentScheduleRead(BaseModel):
    id: int
    name: str
    code: str
    workweek: list[str] = Field(default_factory=list)
    is_active: bool
    shifts: list[ShiftRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ShiftCreateRequest(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    start_time: time
    end_time: time
    start_time_2: time | None = None
    end_time_2: time | None = None
    is_active: bool = True


class ShiftUpdateRequest(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=255)
    start_time: time | None = None
    end_time: time | None = None
    start_time_2: time | None = None
    end_time_2: time | None = None
    is_active: bool | None = None


class AttendanceRecordRead(BaseModel):
    id: int
    user_id: int
    device_user_id: int | None = None
    timestamp: datetime
    punch: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceRecordCreateRequest(BaseModel):
    user_id: int
    device_user_id: int | None = None
    timestamp: datetime
    punch: Literal["IN", "OUT"]


class AttendanceRecordUpdateRequest(BaseModel):
    timestamp: datetime | None = None
    punch: Literal["IN", "OUT"] | None = None


class DailyShiftScheduleRead(BaseModel):
    id: int
    date: date
    user_id: int
    shift_id: int
    user: UserRead | None = None
    shift: ShiftRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailyShiftScheduleCreateRequest(BaseModel):
    date: date
    user_id: int
    shift_id: int


class DailyShiftRecordRead(BaseModel):
    id: int
    date: date
    department_id: int
    is_approved: bool
    department: DepartmentRead | None = None
    schedules: list[DailyShiftScheduleRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailyShiftRecordCreateRequest(BaseModel):
    date: date
    department_id: int
    schedule_ids: list[int] = Field(default_factory=list)
    is_approved: bool = False


class DepartmentScheduleUpdateRequest(BaseModel):
    workweek: list[str] = Field(default_factory=list)
    shift_ids: list[int] = Field(default_factory=list)


class HolidayRead(BaseModel):
    id: int
    name: str
    day: int
    month: int
    year: int | None = None
    is_regular: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HolidayCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    day: int
    month: int
    year: int | None = None
    is_regular: bool = False


class HolidayUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    day: int | None = None
    month: int | None = None
    year: int | None = None
    is_regular: bool | None = None


class OvertimeRequestRead(BaseModel):
    id: int
    user_id: int
    approver_id: int
    info: str | None = None
    date: date
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OvertimeRequestCreateRequest(BaseModel):
    user_id: int
    approver_id: int
    info: str | None = None
    date: date


class OvertimeRequestRespondRequest(BaseModel):
    response: Literal["APPROVE", "REJECT"]


class ShiftSwapRequestRead(BaseModel):
    id: int
    requested_by_id: int
    requested_for_id: int
    current_schedule_id: int
    requested_schedule_id: int
    approver_id: int
    info: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShiftSwapRequestCreateRequest(BaseModel):
    requested_by_id: int
    requested_for_id: int
    current_schedule_id: int
    requested_schedule_id: int
    approver_id: int
    info: str | None = None


class ShiftSwapRequestRespondRequest(BaseModel):
    response: Literal["APPROVE", "REJECT"]


class AttendanceSummaryDayRead(BaseModel):
    day: int
    day_name: str
    shift: DailyShiftScheduleRead | None = None
    attendance_records: list[AttendanceRecordRead] = Field(default_factory=list)
    holidays: list[HolidayRead] = Field(default_factory=list)
    overtime_approved: bool = False


class AttendanceSummaryRead(BaseModel):
    year: int
    month: int
    days: list[AttendanceSummaryDayRead]
