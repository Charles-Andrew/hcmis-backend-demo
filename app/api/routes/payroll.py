from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, require_staff_user
from app.core.time import local_today
from app.models.payroll import (
    FixedCompensation,
    Mp2Enrollment,
    PayrollPolicyVersion,
    Position,
    Payslip,
    PayslipVariableCompensation,
    PayslipVariableDeduction,
    ThirteenthMonthPayout,
)
from app.models.user import User
from app.schemas.payroll import (
    FixedCompensationRead,
    FixedCompensationUpsertRequest,
    FixedCompensationUsersRequest,
    Mp2EnrollmentCreateRequest,
    Mp2EnrollmentRead,
    Mp2EnrollmentUpdateRequest,
    PositionRead,
    PositionUpsertRequest,
    PayrollPolicyDetailRead,
    PayrollPolicyOfficialSeedRequest,
    PayrollPolicySourcesDetailRead,
    PayrollPolicySourcesUpdateRequest,
    PayrollPolicyRulesUpdateRequest,
    PayrollPolicySeedRequest,
    PayrollPolicyVersionCreateRequest,
    PayrollPolicyVersionRead,
    PayrollSettingRead,
    PayrollSettingUpdateRequest,
    PayslipCreateRequest,
    PayslipRead,
    PayslipSummaryRead,
    PayslipSummaryComparisonRead,
    PayslipUpdateRequest,
    PayslipVariableCompensationRead,
    PayslipVariableCompensationUpsertRequest,
    PayslipVariableDeductionRead,
    PayslipVariableDeductionUpsertRequest,
    ThirteenthMonthAdjustmentCreateRequest,
    ThirteenthMonthGenerateRequest,
    ThirteenthMonthPayoutRead,
)
from app.services.payroll_engine import compare_payslip_summary, get_payslip_summary_v2
from app.services.payroll_workflow import (
    activate_policy_version,
    delete_policy_version,
    create_policy_version,
    get_policy_version_rules,
    get_policy_version_sources,
    list_policy_versions,
    seed_ph_policy_baseline,
    seed_ph_policy_official_core,
    update_policy_version_sources,
    update_policy_version_rules,
)
from app.services.payroll import (
    add_payslip_variable_compensation,
    add_payslip_variable_deduction,
    add_thirteenth_month_adjustment,
    create_fixed_compensation,
    create_position,
    create_mp2_enrollment,
    delete_payslip,
    delete_fixed_compensation,
    delete_position,
    get_or_create_payslip,
    get_payslips,
    get_settings,
    generate_thirteenth_month_payouts,
    list_fixed_compensations,
    list_mp2_enrollments,
    list_positions,
    list_my_thirteenth_month_payouts,
    list_thirteenth_month_payouts,
    end_mp2_enrollment,
    remove_payslip_variable_compensation,
    remove_payslip_variable_deduction,
    remove_thirteenth_month_adjustment,
    release_thirteenth_month_payout,
    toggle_payslip_release,
    update_fixed_compensation,
    update_fixed_compensation_users,
    update_mp2_enrollment,
    update_position,
    update_payslip,
    update_settings,
)

router = APIRouter(prefix="/payroll", tags=["payroll"])


@router.get("/settings", response_model=PayrollSettingRead)
async def read_payroll_settings(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> object:
    return await get_settings(session)


@router.patch("/settings", response_model=PayrollSettingRead)
async def patch_payroll_settings(
    payload: PayrollSettingUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> object:
    return await update_settings(session, payload)


@router.get("/policy-versions", response_model=list[PayrollPolicyVersionRead])
async def read_policy_versions(
    policy_key: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[PayrollPolicyVersion]:
    return await list_policy_versions(session, policy_key=policy_key)


@router.post(
    "/policy-versions",
    response_model=PayrollPolicyVersionRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_policy_version(
    payload: PayrollPolicyVersionCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollPolicyVersion:
    return await create_policy_version(session, payload)


@router.delete(
    "/policy-versions/{policy_version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_policy_version(
    policy_version_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_policy_version(session, policy_version_id)


@router.post(
    "/policy-versions/{policy_version_id}/activate",
    response_model=PayrollPolicyVersionRead,
)
async def activate_selected_policy_version(
    policy_version_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollPolicyVersion:
    return await activate_policy_version(session, policy_version_id)


@router.post(
    "/policy-versions/seed-ph-baseline",
    response_model=PayrollPolicyVersionRead,
    status_code=status.HTTP_201_CREATED,
)
async def seed_policy_version(
    payload: PayrollPolicySeedRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollPolicyVersion:
    return await seed_ph_policy_baseline(session, payload)


@router.post(
    "/policy-versions/seed-ph-official-core",
    response_model=PayrollPolicyVersionRead,
    status_code=status.HTTP_201_CREATED,
)
async def seed_policy_version_official(
    payload: PayrollPolicyOfficialSeedRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollPolicyVersion:
    return await seed_ph_policy_official_core(session, payload)


@router.get(
    "/policy-versions/{policy_version_id}/rules",
    response_model=PayrollPolicyDetailRead,
)
async def read_policy_version_rules(
    policy_version_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollPolicyDetailRead:
    return await get_policy_version_rules(session, policy_version_id)


@router.put(
    "/policy-versions/{policy_version_id}/rules",
    response_model=PayrollPolicyDetailRead,
)
async def put_policy_version_rules(
    policy_version_id: int,
    payload: PayrollPolicyRulesUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollPolicyDetailRead:
    return await update_policy_version_rules(session, policy_version_id, payload)


@router.get(
    "/policy-versions/{policy_version_id}/sources",
    response_model=PayrollPolicySourcesDetailRead,
)
async def read_policy_version_sources(
    policy_version_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollPolicySourcesDetailRead:
    return await get_policy_version_sources(session, policy_version_id)


@router.put(
    "/policy-versions/{policy_version_id}/sources",
    response_model=PayrollPolicySourcesDetailRead,
)
async def put_policy_version_sources(
    policy_version_id: int,
    payload: PayrollPolicySourcesUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollPolicySourcesDetailRead:
    return await update_policy_version_sources(
        session,
        policy_version_id,
        payload,
        applied_by=current_user.id,
    )


@router.get("/mp2-enrollments", response_model=list[Mp2EnrollmentRead])
async def read_mp2_enrollments(
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[Mp2Enrollment]:
    return await list_mp2_enrollments(session, status=status)


@router.post(
    "/mp2-enrollments",
    response_model=Mp2EnrollmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_mp2_enrollment(
    payload: Mp2EnrollmentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Mp2Enrollment:
    return await create_mp2_enrollment(session, payload)


@router.patch("/mp2-enrollments/{enrollment_id}", response_model=Mp2EnrollmentRead)
async def patch_mp2_enrollment(
    enrollment_id: int,
    payload: Mp2EnrollmentUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Mp2Enrollment:
    return await update_mp2_enrollment(session, enrollment_id, payload)


@router.post("/mp2-enrollments/{enrollment_id}/end", response_model=Mp2EnrollmentRead)
async def post_end_mp2_enrollment(
    enrollment_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Mp2Enrollment:
    return await end_mp2_enrollment(session, enrollment_id, local_today())


@router.get("/positions", response_model=list[PositionRead])
async def read_positions(
    department_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[Position]:
    return await list_positions(session, department_id=department_id)


@router.post("/positions", response_model=PositionRead, status_code=status.HTTP_201_CREATED)
async def post_position(
    payload: PositionUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Position:
    return await create_position(session, payload)


@router.patch("/positions/{position_id}", response_model=PositionRead)
async def patch_position(
    position_id: int,
    payload: PositionUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Position:
    return await update_position(session, position_id, payload)


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_position(
    position_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_position(session, position_id)


@router.get("/fixed-compensations", response_model=list[FixedCompensationRead])
async def read_fixed_compensations(
    month: int | None = Query(default=None),
    year: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[FixedCompensation]:
    return await list_fixed_compensations(session, month=month, year=year)


@router.post(
    "/fixed-compensations",
    response_model=FixedCompensationRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_fixed_compensation(
    payload: FixedCompensationUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> FixedCompensation:
    return await create_fixed_compensation(session, payload)


@router.patch("/fixed-compensations/{compensation_id}", response_model=FixedCompensationRead)
async def patch_fixed_compensation(
    compensation_id: int,
    payload: FixedCompensationUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> FixedCompensation:
    return await update_fixed_compensation(session, compensation_id, payload)


@router.patch(
    "/fixed-compensations/{compensation_id}/users",
    response_model=FixedCompensationRead,
)
async def patch_fixed_compensation_users(
    compensation_id: int,
    payload: FixedCompensationUsersRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> FixedCompensation:
    return await update_fixed_compensation_users(session, compensation_id, payload)


@router.delete("/fixed-compensations/{compensation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_fixed_compensation(
    compensation_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_fixed_compensation(session, compensation_id)


@router.get("/payslips", response_model=list[PayslipRead])
async def read_payslips(
    user_id: UUID | None = Query(default=None),
    month: int | None = Query(default=None),
    year: int | None = Query(default=None),
    period: str | None = Query(default=None),
    released: bool | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[Payslip]:
    return await get_payslips(
        session, user_id=user_id, month=month, year=year, period=period, released=released
    )


@router.post("/payslips", response_model=PayslipRead, status_code=status.HTTP_201_CREATED)
async def post_payslip(
    payload: PayslipCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Payslip:
    return await get_or_create_payslip(session, payload)


@router.get("/payslips/{payslip_id}/summary", response_model=PayslipSummaryRead)
async def read_payslip_summary(
    payslip_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    return await get_payslip_summary_v2(session, payslip_id)


@router.get(
    "/payslips/{payslip_id}/summary-comparison",
    response_model=PayslipSummaryComparisonRead,
)
async def read_payslip_summary_comparison(
    payslip_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
):
    return await compare_payslip_summary(session, payslip_id)


@router.patch("/payslips/{payslip_id}", response_model=PayslipRead)
async def patch_payslip(
    payslip_id: int,
    payload: PayslipUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Payslip:
    return await update_payslip(session, payslip_id, payload)


@router.delete("/payslips/{payslip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_payslip(
    payslip_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_payslip(session, payslip_id)


@router.post("/payslips/{payslip_id}/release-toggle", response_model=PayslipRead)
async def toggle_payslip(
    payslip_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Payslip:
    return await toggle_payslip_release(session, payslip_id)


@router.post(
    "/payslips/{payslip_id}/variable-compensations",
    response_model=PayslipVariableCompensationRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_payslip_variable_compensation(
    payslip_id: int,
    payload: PayslipVariableCompensationUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayslipVariableCompensation:
    return await add_payslip_variable_compensation(session, payslip_id, payload)


@router.delete(
    "/payslips/variable-compensations/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_payslip_variable_compensation_route(
    item_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await remove_payslip_variable_compensation(session, item_id)


@router.post(
    "/payslips/{payslip_id}/variable-deductions",
    response_model=PayslipVariableDeductionRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_payslip_variable_deduction(
    payslip_id: int,
    payload: PayslipVariableDeductionUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayslipVariableDeduction:
    return await add_payslip_variable_deduction(session, payslip_id, payload)


@router.delete(
    "/payslips/variable-deductions/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_payslip_variable_deduction_route(
    item_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await remove_payslip_variable_deduction(session, item_id)


@router.get("/thirteenth-month", response_model=list[ThirteenthMonthPayoutRead])
async def read_thirteenth_month_payouts(
    year: int | None = Query(default=None),
    user_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[ThirteenthMonthPayout]:
    return await list_thirteenth_month_payouts(
        session,
        year=year,
        user_id=user_id,
        status=status_filter,
    )


@router.get("/thirteenth-month/me", response_model=list[ThirteenthMonthPayoutRead])
async def read_my_thirteenth_month_payouts(
    year: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ThirteenthMonthPayout]:
    return await list_my_thirteenth_month_payouts(session, user_id=current_user.id, year=year)


@router.post("/thirteenth-month/generate", response_model=list[ThirteenthMonthPayoutRead])
async def post_generate_thirteenth_month(
    payload: ThirteenthMonthGenerateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[ThirteenthMonthPayout]:
    return await generate_thirteenth_month_payouts(session, payload)


@router.post(
    "/thirteenth-month/{payout_id}/adjustments",
    response_model=ThirteenthMonthPayoutRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_thirteenth_month_adjustment(
    payout_id: int,
    payload: ThirteenthMonthAdjustmentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> ThirteenthMonthPayout:
    return await add_thirteenth_month_adjustment(session, payout_id, payload)


@router.delete(
    "/thirteenth-month/adjustments/{adjustment_id}",
    response_model=ThirteenthMonthPayoutRead,
)
async def delete_thirteenth_month_adjustment(
    adjustment_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> ThirteenthMonthPayout:
    return await remove_thirteenth_month_adjustment(session, adjustment_id)


@router.post(
    "/thirteenth-month/{payout_id}/release",
    response_model=ThirteenthMonthPayoutRead,
)
async def post_release_thirteenth_month(
    payout_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> ThirteenthMonthPayout:
    return await release_thirteenth_month_payout(session, payout_id)
