from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, require_staff_user
from app.models.leave import LeaveCredit, LeaveRequest, LeaveTypePolicy
from app.models.user import User
from app.schemas.leave import (
    LeaveCreditRead,
    LeaveCreditUpsertRequest,
    LeaveRequestCreateRequest,
    LeaveRequestRead,
    LeaveRequestReviewRequest,
    LeaveTypeOptionRead,
    LeaveTypePolicyRead,
    LeaveTypePolicyUpsertRequest,
)
from app.services.leave import (
    LeaveCreditSnapshot,
    cancel_leave_request,
    create_leave_type_policy,
    create_leave_request,
    delete_leave_type_policy,
    escalate_leave_request,
    get_my_leave_credit,
    list_leave_credits,
    list_leave_type_policies,
    list_leave_requests,
    list_leave_types,
    list_leave_years,
    reset_leave_credit,
    review_leave_request,
    set_leave_credit,
    update_leave_type_policy,
)

router = APIRouter(prefix="/leave", tags=["leave"])


@router.get("/types", response_model=list[LeaveTypeOptionRead])
async def get_types(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, str]]:
    return await list_leave_types(session)


@router.get("/types/manage", response_model=list[LeaveTypePolicyRead])
async def get_leave_type_policies(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[LeaveTypePolicy]:
    return await list_leave_type_policies(session)


@router.post("/types", response_model=LeaveTypePolicyRead, status_code=status.HTTP_201_CREATED)
async def post_leave_type_policy(
    payload: LeaveTypePolicyUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> LeaveTypePolicy:
    return await create_leave_type_policy(session, payload)


@router.put("/types/{leave_type_id}", response_model=LeaveTypePolicyRead)
async def put_leave_type_policy(
    leave_type_id: UUID,
    payload: LeaveTypePolicyUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> LeaveTypePolicy:
    return await update_leave_type_policy(session, leave_type_id, payload)


@router.delete("/types/{leave_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_leave_type(
    leave_type_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_leave_type_policy(session, leave_type_id)


@router.get("/years", response_model=list[int])
async def get_years(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[int]:
    return await list_leave_years(session)


@router.get("/requests/me", response_model=list[LeaveRequestRead])
async def get_my_requests(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[LeaveRequest]:
    return await list_leave_requests(session, user_id=current_user.id, year=year, month=month)


@router.get("/requests/review", response_model=list[LeaveRequestRead])
async def get_review_requests(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    status: str | None = Query(default="PENDING"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[LeaveRequest]:
    return await list_leave_requests(
        session,
        approver_id=current_user.id,
        year=year,
        month=month,
        status=status,
    )


@router.get("/requests", response_model=list[LeaveRequestRead])
async def get_requests(
    user_id: UUID | None = Query(default=None),
    department_id: int | None = Query(default=None),
    approver_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[LeaveRequest]:
    return await list_leave_requests(
        session,
        user_id=user_id,
        department_id=department_id,
        approver_id=approver_id,
        status=status,
        year=year,
        month=month,
    )


@router.post("/requests/me", response_model=LeaveRequestRead, status_code=status.HTTP_201_CREATED)
async def post_my_request(
    payload: LeaveRequestCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> LeaveRequest:
    return await create_leave_request(session, current_user, payload)


@router.patch("/requests/{leave_id}/review", response_model=LeaveRequestRead)
async def patch_request_review(
    leave_id: int,
    payload: LeaveRequestReviewRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> LeaveRequest:
    return await review_leave_request(session, leave_id, current_user, payload)


@router.patch("/requests/{leave_id}/cancel", response_model=LeaveRequestRead)
async def cancel_request(
    leave_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> LeaveRequest:
    return await cancel_leave_request(session, leave_id, current_user)


@router.post("/requests/{leave_id}/escalate", response_model=LeaveRequestRead)
async def escalate_request(
    leave_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> LeaveRequest:
    return await escalate_leave_request(session, leave_id, current_user)


@router.get("/credits/me", response_model=LeaveCreditRead)
async def get_my_credit(
    leave_type: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> LeaveCreditSnapshot:
    return await get_my_leave_credit(session, current_user.id, leave_type=leave_type)


@router.get("/credits", response_model=list[LeaveCreditRead])
async def get_credits(
    user_id: UUID | None = Query(default=None),
    department_id: int | None = Query(default=None),
    leave_type: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[LeaveCreditSnapshot]:
    return await list_leave_credits(
        session,
        user_id=user_id,
        department_id=department_id,
        leave_type=leave_type,
    )


@router.put("/credits/{user_id}", response_model=LeaveCreditRead)
async def put_credit(
    user_id: UUID,
    payload: LeaveCreditUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> LeaveCredit:
    return await set_leave_credit(session, user_id, payload)


@router.post("/credits/{user_id}/reset", response_model=LeaveCreditRead)
async def reset_credit(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> LeaveCredit:
    return await reset_leave_credit(session, user_id)
