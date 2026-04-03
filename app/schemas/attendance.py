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


class BridgeUserRead(BaseModel):
    user_id: int
    biometric_uid: int
    first_name: str
    last_name: str
    is_active: bool


class BridgeUsersResponse(BaseModel):
    users: list[BridgeUserRead] = Field(default_factory=list)


class BridgeCommandSyncUsersCreateRequest(BaseModel):
    site_code: str = Field(min_length=1, max_length=64)
    device_id: str = Field(min_length=1, max_length=128)


class BridgeCommandScanUsersCreateRequest(BaseModel):
    site_code: str = Field(min_length=1, max_length=64)
    device_id: str = Field(min_length=1, max_length=128)


class BridgeCommandAckRequest(BaseModel):
    status: Literal["done", "failed"]
    message: str | None = None
    executed_at: datetime | None = None


class BridgeCommandRead(BaseModel):
    command_id: int
    site_code: str
    device_id: str
    type: str
    payload: dict = Field(default_factory=dict)
    status: str
    message: str | None = None
    created_at: datetime
    dispatched_at: datetime | None = None
    executed_at: datetime | None = None


class BridgeCommandsResponse(BaseModel):
    commands: list[BridgeCommandRead] = Field(default_factory=list)


class BridgeLogEventRequest(BaseModel):
    device_user_id: str
    timestamp: datetime
    status: int | None = None
    punch: int | None = None
    raw_event_id: str | None = None


class BridgeLogsRequest(BaseModel):
    site_code: str = Field(min_length=1, max_length=64)
    device_id: str = Field(min_length=1, max_length=128)
    events: list[BridgeLogEventRequest] = Field(default_factory=list)


class BridgeLogsResponse(BaseModel):
    accepted: int = 0
    duplicates: int = 0
    unknown_users: int = 0
    failed: int = 0


class BridgeHeartbeatRequest(BaseModel):
    site_code: str = Field(min_length=1, max_length=64)
    device_id: str = Field(min_length=1, max_length=128)
    agent_version: str | None = None
    device_reachable: bool
    last_sync_at: str | None = None


class BridgeHeartbeatResponse(BaseModel):
    status: str = "ok"


class BridgeBiometricSnapshotUser(BaseModel):
    biometric_uid: int
    name: str = ""


class BridgeBiometricSnapshotRequest(BaseModel):
    site_code: str = Field(min_length=1, max_length=64)
    device_id: str = Field(min_length=1, max_length=128)
    scanned_at: datetime | None = None
    users: list[BridgeBiometricSnapshotUser] = Field(default_factory=list)


class BridgeBiometricSnapshotResponse(BaseModel):
    status: str = "ok"
    stored_users: int = 0


class BridgeReconcileRow(BaseModel):
    key: str
    biometric_uid: int | None = None
    app_user_id: int | None = None
    app_name: str | None = None
    biometric_name: str | None = None
    present_in_app: bool
    present_in_biometric: bool


class BridgeReconcileResponse(BaseModel):
    site_code: str
    device_id: str
    rows: list[BridgeReconcileRow] = Field(default_factory=list)


ShiftRead = ShiftTemplateRead
DepartmentScheduleRead = DepartmentShiftPolicyRead
ShiftCreateRequest = ShiftTemplateCreateRequest
ShiftUpdateRequest = ShiftTemplateUpdateRequest
DailyShiftScheduleRead = EmployeeShiftAssignmentRead
DailyShiftScheduleCreateRequest = EmployeeShiftAssignmentCreateRequest
DailyShiftRecordRead = DepartmentRosterDayRead
DailyShiftRecordCreateRequest = DepartmentRosterDayCreateRequest
