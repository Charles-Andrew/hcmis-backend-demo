from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.schemas.user import UserRead


SpecialRequestScope = Literal["mine", "approvals", "all"]


class SpecialRequestApproverAssignmentRead(BaseModel):
    approver_id: UUID | None = None
    approver: UserRead | None = None
    approver_ids: list[UUID] = Field(default_factory=list)
    approvers: list[UserRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SpecialRequestRespondRequest(BaseModel):
    response: Literal["APPROVE", "REJECT"]


class OfficialBusinessRequestCreateRequest(BaseModel):
    user_id: UUID
    info: str | None = None
    date: date


class OfficialBusinessRequestApproverRead(BaseModel):
    id: int
    official_business_request_id: int
    approver_id: UUID
    status: str
    acted_at: datetime | None = None
    approver: UserRead | None = None

    model_config = ConfigDict(from_attributes=True)


class OfficialBusinessRequestRead(BaseModel):
    id: int
    user_id: UUID
    approver_id: UUID
    info: str | None = None
    date: date
    escalated_to_backup_at: datetime | None = None
    escalated_to_backup_by_id: UUID | None = None
    status: str
    user_name: str | None = None
    user_email: str | None = None
    user_department_name: str | None = None
    approver_name: str | None = None
    approver_pool: list[OfficialBusinessRequestApproverRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CertificateAttendanceRequestCreateRequest(BaseModel):
    user_id: UUID
    info: str | None = None
    date: date
    time: time
    punch: Literal["IN", "OUT"]


class CertificateAttendanceRequestApproverRead(BaseModel):
    id: int
    certificate_attendance_request_id: int
    approver_id: UUID
    status: str
    acted_at: datetime | None = None
    approver: UserRead | None = None

    model_config = ConfigDict(from_attributes=True)


class CertificateAttendanceRequestRead(BaseModel):
    id: int
    user_id: UUID
    approver_id: UUID
    info: str | None = None
    date: date
    time: time
    punch: Literal["IN", "OUT"]
    escalated_to_backup_at: datetime | None = None
    escalated_to_backup_by_id: UUID | None = None
    status: str
    user_name: str | None = None
    user_email: str | None = None
    user_department_name: str | None = None
    approver_name: str | None = None
    approver_pool: list[CertificateAttendanceRequestApproverRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
