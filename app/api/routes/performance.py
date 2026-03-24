from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, require_staff_user
from app.models.performance import Evaluation, Questionnaire, UserEvaluation
from app.models.user import User
from app.schemas.performance import (
    EvaluationCreateRequest,
    EvaluationRead,
    EvaluationSummaryRead,
    EvaluationUpdateRequest,
    QuestionnaireCreateRequest,
    QuestionnaireRead,
    QuestionnaireUpdateRequest,
    UserEvaluationCreateRequest,
    UserEvaluationRead,
    UserEvaluationUpdateRequest,
)
from app.services.performance import (
    create_evaluation,
    create_questionnaire,
    create_user_evaluation,
    delete_evaluation,
    delete_questionnaire,
    delete_user_evaluation,
    get_evaluation_summary,
    list_evaluations,
    list_questionnaires,
    list_user_evaluations,
    reset_evaluation,
    reset_user_evaluation,
    submit_evaluation,
    toggle_user_evaluation_finalized,
    update_evaluation,
    update_questionnaire,
    update_user_evaluation,
)

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/questionnaires", response_model=list[QuestionnaireRead])
async def read_questionnaires(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[Questionnaire]:
    return await list_questionnaires(session)


@router.post(
    "/questionnaires",
    response_model=QuestionnaireRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_questionnaire(
    payload: QuestionnaireCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Questionnaire:
    return await create_questionnaire(session, payload)


@router.patch("/questionnaires/{questionnaire_id}", response_model=QuestionnaireRead)
async def patch_questionnaire(
    questionnaire_id: int,
    payload: QuestionnaireUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> Questionnaire:
    return await update_questionnaire(session, questionnaire_id, payload)


@router.delete("/questionnaires/{questionnaire_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_questionnaire(
    questionnaire_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_questionnaire(session, questionnaire_id)


@router.get("/user-evaluations", response_model=list[UserEvaluationRead])
async def read_user_evaluations(
    evaluatee_id: int | None = None,
    questionnaire_id: int | None = None,
    quarter: str | None = None,
    year: int | None = None,
    is_finalized: bool | None = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[UserEvaluation]:
    return await list_user_evaluations(
        session,
        evaluatee_id=evaluatee_id,
        questionnaire_id=questionnaire_id,
        quarter=quarter,
        year=year,
        is_finalized=is_finalized,
    )


@router.post(
    "/user-evaluations",
    response_model=UserEvaluationRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_user_evaluation(
    payload: UserEvaluationCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> UserEvaluation:
    return await create_user_evaluation(session, payload)


@router.patch("/user-evaluations/{user_evaluation_id}", response_model=UserEvaluationRead)
async def patch_user_evaluation(
    user_evaluation_id: int,
    payload: UserEvaluationUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> UserEvaluation:
    return await update_user_evaluation(session, user_evaluation_id, payload)


@router.post("/user-evaluations/{user_evaluation_id}/finalize-toggle", response_model=UserEvaluationRead)
async def toggle_user_evaluation(
    user_evaluation_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> UserEvaluation:
    return await toggle_user_evaluation_finalized(session, user_evaluation_id)


@router.post("/user-evaluations/{user_evaluation_id}/reset", response_model=UserEvaluationRead)
async def reset_user_evaluation_route(
    user_evaluation_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> UserEvaluation:
    return await reset_user_evaluation(session, user_evaluation_id)


@router.delete("/user-evaluations/{user_evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_evaluation(
    user_evaluation_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_staff_user),
) -> None:
    await delete_user_evaluation(session, user_evaluation_id)


@router.get("/user-evaluations/{user_evaluation_id}/evaluations", response_model=list[EvaluationRead])
async def read_evaluations(
    user_evaluation_id: int,
    evaluator_id: int | None = None,
    is_submitted: bool | None = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[Evaluation]:
    return await list_evaluations(
        session,
        user_evaluation_id=user_evaluation_id,
        evaluator_id=evaluator_id,
        is_submitted=is_submitted,
    )


@router.post(
    "/user-evaluations/{user_evaluation_id}/evaluations",
    response_model=EvaluationRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_evaluation(
    user_evaluation_id: int,
    payload: EvaluationCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Evaluation:
    return await create_evaluation(session, user_evaluation_id, current_user.id, payload)


@router.patch("/evaluations/{evaluation_id}", response_model=EvaluationRead)
async def patch_evaluation(
    evaluation_id: int,
    payload: EvaluationUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Evaluation:
    return await update_evaluation(session, evaluation_id, payload)


@router.post("/evaluations/{evaluation_id}/submit", response_model=EvaluationRead)
async def submit_evaluation_route(
    evaluation_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Evaluation:
    return await submit_evaluation(session, evaluation_id)


@router.post("/evaluations/{evaluation_id}/reset", response_model=EvaluationRead)
async def reset_evaluation_route(
    evaluation_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Evaluation:
    return await reset_evaluation(session, evaluation_id)


@router.get("/evaluations/{evaluation_id}/summary", response_model=EvaluationSummaryRead)
async def read_evaluation_summary(
    evaluation_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> EvaluationSummaryRead:
    return await get_evaluation_summary(session, evaluation_id)


@router.delete("/evaluations/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_evaluation(
    evaluation_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    await delete_evaluation(session, evaluation_id)
