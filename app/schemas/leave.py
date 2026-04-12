from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.schemas.user import UserRead


class LeaveTypeOptionRead(BaseModel):
    value: str
    label: str


class LeaveCreditUpsertRequest(BaseModel):
    credits: int = Field(ge=0)


class LeaveCreditRead(BaseModel):
    user_id: UUID
    credits: int
    used_credits: int
    remaining_credits: int
    user: UserRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaveRequestCreateRequest(BaseModel):
    leave_date: date
    leave_type: Literal["PA", "UN", "WR"]
    info: str | None = None


class LeaveRequestReviewRequest(BaseModel):
    response: Literal["APPROVE", "REJECT"]


class LeaveRequestApproverRead(BaseModel):
    id: int
    leave_request_id: int
    approver_id: UUID
    status: str
    acted_at: datetime | None = None
    approver: UserRead | None = None

    model_config = ConfigDict(from_attributes=True)


class LeaveRequestRead(BaseModel):
    id: int
    user_id: UUID
    leave_date: date
    leave_type: str
    info: str | None = None
    first_approver_id: UUID | None = None
    first_approver_status: str
    first_approver_at: datetime | None = None
    second_approver_id: UUID | None = None
    second_approver_status: str | None = None
    second_approver_at: datetime | None = None
    escalated_to_backup_at: datetime | None = None
    escalated_to_backup_by_id: UUID | None = None
    status: str
    user: UserRead | None = None
    first_approver: UserRead | None = None
    second_approver: UserRead | None = None
    approver_pool: list[LeaveRequestApproverRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
