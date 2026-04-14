from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.core.capabilities import is_staff_user
from app.core.exceptions import PermissionDeniedError
from app.models.special_requests import CertificateAttendanceRequest, OfficialBusinessRequest
from app.models.user import User
from app.schemas.special_requests import (
    CertificateAttendanceRequestCreateRequest,
    CertificateAttendanceRequestRead,
    OfficialBusinessRequestCreateRequest,
    OfficialBusinessRequestRead,
    SpecialRequestApproverAssignmentRead,
    SpecialRequestRespondRequest,
    SpecialRequestScope,
)
from app.services.special_requests import (
    cancel_certificate_attendance_request,
    cancel_official_business_request,
    create_certificate_attendance_request,
    create_official_business_request,
    escalate_certificate_attendance_request,
    escalate_official_business_request,
    get_my_special_request_approver_assignment,
    list_certificate_attendance_requests,
    list_official_business_requests,
    respond_to_certificate_attendance_request,
    respond_to_official_business_request,
)

router = APIRouter(prefix="/special-requests", tags=["special-requests"])


@router.get("/official-business", response_model=list[OfficialBusinessRequestRead])
async def get_official_business_requests(
    scope: SpecialRequestScope | None = Query(default=None),
    user_id: UUID | None = Query(default=None),
    approver_id: UUID | None = Query(default=None),
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    status: str | None = Query(default=None),
    department_id: int | None = Query(default=None),
    query: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[OfficialBusinessRequest]:
    return await list_official_business_requests(
        session,
        current_user_id=current_user.id,
        current_user_is_staff=is_staff_user(current_user),
        scope=scope,
        user_id=user_id,
        approver_id=approver_id,
        year=year,
        month=month,
        status=status,
        department_id=department_id,
        query=query,
    )


@router.get(
    "/official-business-approvers/me",
    response_model=SpecialRequestApproverAssignmentRead,
)
async def get_my_official_business_approver(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> SpecialRequestApproverAssignmentRead:
    return await get_my_special_request_approver_assignment(session, current_user)


@router.post(
    "/official-business",
    response_model=OfficialBusinessRequestRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_official_business_request(
    payload: OfficialBusinessRequestCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OfficialBusinessRequest:
    if payload.user_id != current_user.id and not is_staff_user(current_user):
        raise PermissionDeniedError(
            "You do not have permission to create this official business request."
        )
    return await create_official_business_request(session, current_user, payload)


@router.post(
    "/official-business/{request_id}/respond",
    response_model=OfficialBusinessRequestRead,
)
async def post_respond_official_business(
    request_id: int,
    payload: SpecialRequestRespondRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OfficialBusinessRequest:
    return await respond_to_official_business_request(
        session, request_id, current_user.id, payload
    )


@router.post(
    "/official-business/{request_id}/escalate",
    response_model=OfficialBusinessRequestRead,
)
async def post_escalate_official_business(
    request_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OfficialBusinessRequest:
    if not is_staff_user(current_user):
        raise PermissionDeniedError("You do not have permission to escalate this request.")
    return await escalate_official_business_request(session, request_id, current_user)


@router.patch(
    "/official-business/{request_id}/cancel",
    response_model=OfficialBusinessRequestRead,
)
async def patch_cancel_official_business(
    request_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OfficialBusinessRequest:
    return await cancel_official_business_request(
        session,
        request_id,
        current_user,
        current_user_is_staff=is_staff_user(current_user),
    )


@router.get(
    "/certificate-attendance",
    response_model=list[CertificateAttendanceRequestRead],
)
async def get_certificate_attendance_requests(
    scope: SpecialRequestScope | None = Query(default=None),
    user_id: UUID | None = Query(default=None),
    approver_id: UUID | None = Query(default=None),
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    status: str | None = Query(default=None),
    department_id: int | None = Query(default=None),
    query: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[CertificateAttendanceRequest]:
    return await list_certificate_attendance_requests(
        session,
        current_user_id=current_user.id,
        current_user_is_staff=is_staff_user(current_user),
        scope=scope,
        user_id=user_id,
        approver_id=approver_id,
        year=year,
        month=month,
        status=status,
        department_id=department_id,
        query=query,
    )


@router.get(
    "/certificate-attendance-approvers/me",
    response_model=SpecialRequestApproverAssignmentRead,
)
async def get_my_certificate_attendance_approver(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> SpecialRequestApproverAssignmentRead:
    return await get_my_special_request_approver_assignment(session, current_user)


@router.post(
    "/certificate-attendance",
    response_model=CertificateAttendanceRequestRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_certificate_attendance_request(
    payload: CertificateAttendanceRequestCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> CertificateAttendanceRequest:
    if payload.user_id != current_user.id and not is_staff_user(current_user):
        raise PermissionDeniedError(
            "You do not have permission to create this certificate of attendance request."
        )
    return await create_certificate_attendance_request(session, current_user, payload)


@router.post(
    "/certificate-attendance/{request_id}/respond",
    response_model=CertificateAttendanceRequestRead,
)
async def post_respond_certificate_attendance(
    request_id: int,
    payload: SpecialRequestRespondRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> CertificateAttendanceRequest:
    return await respond_to_certificate_attendance_request(
        session, request_id, current_user.id, payload
    )


@router.post(
    "/certificate-attendance/{request_id}/escalate",
    response_model=CertificateAttendanceRequestRead,
)
async def post_escalate_certificate_attendance(
    request_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> CertificateAttendanceRequest:
    if not is_staff_user(current_user):
        raise PermissionDeniedError("You do not have permission to escalate this request.")
    return await escalate_certificate_attendance_request(session, request_id, current_user)


@router.patch(
    "/certificate-attendance/{request_id}/cancel",
    response_model=CertificateAttendanceRequestRead,
)
async def patch_cancel_certificate_attendance(
    request_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> CertificateAttendanceRequest:
    return await cancel_certificate_attendance_request(
        session,
        request_id,
        current_user,
        current_user_is_staff=is_staff_user(current_user),
    )
