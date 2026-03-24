from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, require_staff_user
from app.models.payroll import (
    FixedCompensation,
    Job,
    PayrollSetting,
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
    JobRead,
    JobUpsertRequest,
    Mp2Read,
    Mp2UpdateRequest,
    PayrollSettingRead,
    PayrollSettingUpdateRequest,
    PayslipCreateRequest,
    PayslipRead,
    PayslipSummaryRead,
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
from app.services.payroll import (
    add_payslip_variable_compensation,
    add_payslip_variable_deduction,
    add_thirteenth_month_pay_variable_deduction,
    create_fixed_compensation,
    create_job,
    create_thirteenth_month_pay,
    delete_fixed_compensation,
    delete_job,
    delete_thirteenth_month_pay,
    get_mp2,
    get_payslips,
    get_or_create_payslip,
    get_payslip_summary,
    get_settings,
    list_fixed_compensations,
    list_jobs,
    list_thirteenth_month_pays,
    remove_payslip_variable_compensation,
    remove_payslip_variable_deduction,
    remove_thirteenth_month_pay_variable_deduction,
    toggle_payslip_release,
    toggle_thirteenth_month_pay_release,
    update_fixed_compensation,
    update_fixed_compensation_users,
    update_job,
    update_mp2,
    update_payslip,
    update_settings,
    update_thirteenth_month_pay,
)

router = APIRouter(prefix="/payroll", tags=["payroll"])


@router.get("/settings", response_model=PayrollSettingRead)
async def read_settings(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollSetting:
    return await get_settings(session)


@router.patch("/settings", response_model=PayrollSettingRead)
async def patch_settings(
    payload: PayrollSettingUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> PayrollSetting:
    return await update_settings(session, payload)


@router.get("/mp2", response_model=Mp2Read)
async def read_mp2(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Mp2Read:
    mp2 = await get_mp2(session)
    return Mp2Read.model_validate(mp2)


@router.put("/mp2", response_model=Mp2Read)
async def put_mp2(
    payload: Mp2UpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Mp2Read:
    mp2 = await update_mp2(session, amount=payload.amount, user_ids=payload.user_ids)
    return Mp2Read.model_validate(mp2)


@router.get("/jobs", response_model=list[JobRead])
async def read_jobs(
    department_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[Job]:
    return await list_jobs(session, department_id=department_id)


@router.post("/jobs", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def post_job(
    payload: JobUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Job:
    return await create_job(session, payload)


@router.patch("/jobs/{job_id}", response_model=JobRead)
async def patch_job(
    job_id: int,
    payload: JobUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Job:
    return await update_job(session, job_id, payload)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_job(
    job_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_job(session, job_id)


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
    user_id: int | None = Query(default=None),
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
    user_id: int | None = Query(default=None),
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
