from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, require_staff_user
from app.core.time import utc_now
from app.models.payroll import (
    FixedCompensation,
    Mp2Enrollment,
    PayrollItemType,
    PayrollPolicyVersion,
    PayrollRun,
    PayrollRunInput,
    PayrollRunItem,
    Position,
    Payslip,
    PayslipVariableCompensation,
    PayslipVariableDeduction,
    ThirteenthMonthPay,
    ThirteenthMonthPayVariableDeduction,
)
from app.models.user import User
from app.schemas.payroll import (
    FixedCompensationRead,
    FixedCompensationUpsertRequest,
    FixedCompensationUsersRequest,
    Mp2EnrollmentCreateRequest,
    Mp2EnrollmentRead,
    Mp2EnrollmentUpdateRequest,
    PayrollItemTypeRead,
    PayrollItemTypeUpsertRequest,
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
    PayrollRunCreateRequest,
    PayrollRunInputCreateRequest,
    PayrollRunInputRead,
    PayrollRunInputUpdateRequest,
    PayrollRunItemRead,
    PayrollRunRead,
    PayslipCreateRequest,
    PayslipRead,
    PayslipSummaryRead,
    PayslipSummaryComparisonRead,
    PayslipUpdateRequest,
    PayslipVariableCompensationRead,
    PayslipVariableCompensationUpsertRequest,
    PayslipVariableDeductionRead,
    PayslipVariableDeductionUpsertRequest,
    ThirteenthMonthPayCreateRequest,
    ThirteenthMonthPayRead,
    ThirteenthMonthPayUpdateRequest,
    ThirteenthMonthPayVariableDeductionRead,
    ThirteenthMonthPayVariableDeductionUpsertRequest,
)
from app.services.payroll_engine import compare_payslip_summary
from app.services.payroll_workflow import (
    activate_policy_version,
    approve_payroll_run,
    create_payroll_run,
    delete_policy_version,
    create_policy_version,
    get_policy_version_rules,
    get_policy_version_sources,
    list_payroll_run_items,
    list_payroll_runs,
    list_policy_versions,
    post_payroll_run as post_payroll_run_workflow,
    release_payroll_run,
    seed_ph_policy_baseline,
    seed_ph_policy_official_core,
    update_policy_version_sources,
    update_policy_version_rules,
    validate_payroll_run,
)
from app.services.payroll import (
    add_payslip_variable_compensation,
    add_payslip_variable_deduction,
    add_thirteenth_month_pay_variable_deduction,
    create_payroll_item_type,
    create_payroll_run_input,
    create_fixed_compensation,
    create_position,
    create_mp2_enrollment,
    create_thirteenth_month_pay,
    delete_fixed_compensation,
    delete_position,
    delete_thirteenth_month_pay,
    get_payslips,
    get_or_create_payslip,
    get_payslip_summary,
    list_payroll_item_types,
    list_payroll_run_inputs,
    list_fixed_compensations,
    list_mp2_enrollments,
    list_positions,
    list_thirteenth_month_pays,
    remove_payslip_variable_compensation,
    remove_payslip_variable_deduction,
    remove_thirteenth_month_pay_variable_deduction,
    delete_payroll_run_input,
    toggle_payslip_release,
    toggle_thirteenth_month_pay_release,
    update_payroll_item_type,
    update_fixed_compensation,
    update_fixed_compensation_users,
    end_mp2_enrollment,
    update_mp2_enrollment,
    update_position,
    update_payslip,
    update_payroll_run_input,
    update_thirteenth_month_pay,
)

router = APIRouter(prefix="/payroll", tags=["payroll"])


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
    return await end_mp2_enrollment(session, enrollment_id, utc_now().date())


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


@router.get("/item-types", response_model=list[PayrollItemTypeRead])
async def read_payroll_item_types(
    active_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[PayrollItemType]:
    return await list_payroll_item_types(session, active_only=active_only)


@router.post(
    "/item-types",
    response_model=PayrollItemTypeRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_payroll_item_type(
    payload: PayrollItemTypeUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollItemType:
    return await create_payroll_item_type(session, payload)


@router.patch("/item-types/{item_type_id}", response_model=PayrollItemTypeRead)
async def patch_payroll_item_type(
    item_type_id: int,
    payload: PayrollItemTypeUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollItemType:
    return await update_payroll_item_type(session, item_type_id, payload)


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


@router.get("/runs", response_model=list[PayrollRunRead])
async def read_payroll_runs(
    month: int | None = Query(default=None),
    year: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[PayrollRun]:
    return await list_payroll_runs(session, month=month, year=year)


@router.post("/runs", response_model=PayrollRunRead, status_code=status.HTTP_201_CREATED)
async def post_payroll_run(
    payload: PayrollRunCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollRun:
    return await create_payroll_run(session, payload, created_by=current_user.id)


@router.post("/runs/{payroll_run_id}/validate", response_model=PayrollRunRead)
async def validate_run(
    payroll_run_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollRun:
    return await validate_payroll_run(session, payroll_run_id)


@router.post("/runs/{payroll_run_id}/approve", response_model=PayrollRunRead)
async def approve_run(
    payroll_run_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollRun:
    return await approve_payroll_run(session, payroll_run_id, approved_by=current_user.id)


@router.post("/runs/{payroll_run_id}/post", response_model=PayrollRunRead)
async def post_run(
    payroll_run_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollRun:
    return await post_payroll_run_workflow(session, payroll_run_id)


@router.post("/runs/{payroll_run_id}/release", response_model=PayrollRunRead)
async def release_run(
    payroll_run_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollRun:
    return await release_payroll_run(session, payroll_run_id)


@router.get("/runs/{payroll_run_id}/items", response_model=list[PayrollRunItemRead])
async def read_payroll_run_items(
    payroll_run_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[PayrollRunItem]:
    return await list_payroll_run_items(session, payroll_run_id)


@router.get("/runs/{payroll_run_id}/inputs", response_model=list[PayrollRunInputRead])
async def read_payroll_run_inputs(
    payroll_run_id: int,
    user_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[PayrollRunInput]:
    return await list_payroll_run_inputs(session, payroll_run_id, user_id=user_id)


@router.post(
    "/runs/{payroll_run_id}/inputs",
    response_model=PayrollRunInputRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_payroll_run_input(
    payroll_run_id: int,
    payload: PayrollRunInputCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollRunInput:
    return await create_payroll_run_input(
        session,
        payroll_run_id,
        payload,
        created_by=current_user.id,
    )


@router.patch("/run-inputs/{run_input_id}", response_model=PayrollRunInputRead)
async def patch_payroll_run_input(
    run_input_id: int,
    payload: PayrollRunInputUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollRunInput:
    return await update_payroll_run_input(session, run_input_id, payload, actor_id=current_user.id)


@router.delete("/run-inputs/{run_input_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_payroll_run_input(
    run_input_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_payroll_run_input(session, run_input_id, actor_id=current_user.id)


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
    return await get_payslip_summary(session, payslip_id)


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


@router.get("/thirteenth-month-pays", response_model=list[ThirteenthMonthPayRead])
async def read_thirteenth_month_pays(
    user_id: UUID | None = Query(default=None),
    month: int | None = Query(default=None),
    year: int | None = Query(default=None),
    released: bool | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> list[ThirteenthMonthPay]:
    return await list_thirteenth_month_pays(
        session, user_id=user_id, month=month, year=year, released=released
    )


@router.post(
    "/thirteenth-month-pays",
    response_model=ThirteenthMonthPayRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_thirteenth_month_pay(
    payload: ThirteenthMonthPayCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> ThirteenthMonthPay:
    return await create_thirteenth_month_pay(session, payload)


@router.patch("/thirteenth-month-pays/{item_id}", response_model=ThirteenthMonthPayRead)
async def patch_thirteenth_month_pay(
    item_id: int,
    payload: ThirteenthMonthPayUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> ThirteenthMonthPay:
    return await update_thirteenth_month_pay(session, item_id, payload)


@router.post(
    "/thirteenth-month-pays/{item_id}/release-toggle",
    response_model=ThirteenthMonthPayRead,
)
async def toggle_thirteenth_month_pay(
    item_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> ThirteenthMonthPay:
    return await toggle_thirteenth_month_pay_release(session, item_id)


@router.delete("/thirteenth-month-pays/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_thirteenth_month_pay_route(
    item_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_thirteenth_month_pay(session, item_id)


@router.post(
    "/thirteenth-month-pays/{item_id}/variable-deductions",
    response_model=ThirteenthMonthPayVariableDeductionRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_thirteenth_month_pay_variable_deduction(
    item_id: int,
    payload: ThirteenthMonthPayVariableDeductionUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> ThirteenthMonthPayVariableDeduction:
    return await add_thirteenth_month_pay_variable_deduction(session, item_id, payload)


@router.delete(
    "/thirteenth-month-pays/variable-deductions/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_thirteenth_month_pay_variable_deduction_route(
    item_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await remove_thirteenth_month_pay_variable_deduction(session, item_id)
