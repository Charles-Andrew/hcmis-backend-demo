from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.schemas.department import DepartmentRead
from app.schemas.user import UserRead


class ShiftTemplateRead(BaseModel):
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


class DepartmentShiftPolicyRead(BaseModel):
    id: int
    name: str
    code: str
    workweek: list[str] = Field(default_factory=list)
    is_active: bool
    shifts: list["ShiftTemplateRead"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ShiftTemplateCreateRequest(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    start_time: time
    end_time: time
    start_time_2: time | None = None
    end_time_2: time | None = None
    is_active: bool = True


class ShiftTemplateUpdateRequest(BaseModel):
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


class EmployeeShiftAssignmentRead(BaseModel):
    id: int
    date: date
    user_id: int
    shift_id: int
    user: UserRead | None = None
    shift: ShiftTemplateRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeShiftAssignmentCreateRequest(BaseModel):
    date: date
    user_id: int
    shift_id: int


class EmployeeShiftAssignmentUpdateRequest(BaseModel):
    shift_id: int


class EmployeeShiftAssignmentCopyPreviousMonthRequest(BaseModel):
    user_id: int
    year: int
    month: int


class EmployeeShiftAssignmentCopyPreviousMonthResponse(BaseModel):
    copied_count: int
    skipped_count: int


class EmployeeShiftAssignmentGenerateMonthRequest(BaseModel):
    user_id: int
    year: int
    month: int
    shift_id: int | None = None


class EmployeeShiftAssignmentGenerateMonthResponse(BaseModel):
    generated_count: int
    skipped_count: int


class DepartmentRosterDayRead(BaseModel):
    id: int
    date: date
    department_id: int
    is_approved: bool
    department: DepartmentRead | None = None
    schedules: list[EmployeeShiftAssignmentRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DepartmentRosterDayCreateRequest(BaseModel):
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
    user_name: str | None = None
    user_email: str | None = None
    user_department_name: str | None = None
    approver_name: str | None = None
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


OvertimeRequestScope = Literal["mine", "approvals", "all"]


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
    shift: EmployeeShiftAssignmentRead | None = None
    attendance_records: list[AttendanceRecordRead] = Field(default_factory=list)
    holidays: list[HolidayRead] = Field(default_factory=list)
    overtime_approved: bool = False


class AttendanceSummaryRead(BaseModel):
    year: int
    month: int
    days: list[AttendanceSummaryDayRead]


ShiftRead = ShiftTemplateRead
DepartmentScheduleRead = DepartmentShiftPolicyRead
ShiftCreateRequest = ShiftTemplateCreateRequest
ShiftUpdateRequest = ShiftTemplateUpdateRequest
DailyShiftScheduleRead = EmployeeShiftAssignmentRead
DailyShiftScheduleCreateRequest = EmployeeShiftAssignmentCreateRequest
DailyShiftRecordRead = DepartmentRosterDayRead
DailyShiftRecordCreateRequest = DepartmentRosterDayCreateRequest
