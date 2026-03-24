from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.time import utc_now
from app.models.performance import Evaluation, Questionnaire, UserEvaluation
from app.repositories.performance import (
    EvaluationRepository,
    QuestionnaireRepository,
    UserEvaluationRepository,
)
from app.repositories.users import UserRepository
from app.schemas.performance import (
    EvaluationCreateRequest,
    EvaluationSummaryRead,
    EvaluationUpdateRequest,
    QuestionnaireCreateRequest,
    QuestionnaireUpdateRequest,
    UserEvaluationCreateRequest,
    UserEvaluationUpdateRequest,
)


def _questionnaire_content(questionnaire: Questionnaire) -> list[dict[str, object]]:
    content = questionnaire.content if isinstance(questionnaire.content, dict) else {}
    data = content.get("questionnaire_content", [])
    if not isinstance(data, list):
        return []
    return [domain for domain in data if isinstance(domain, dict)]


def _copy_questionnaire_content(questionnaire: Questionnaire) -> list[dict]:
    return [dict(domain) for domain in _questionnaire_content(questionnaire)]


def _current_domain_key(domain: dict, index: int) -> str:
    domain_number = domain.get("domain_number")
    if domain_number is not None:
        return str(domain_number)
    domain_name = domain.get("domain_name")
    if domain_name:
        return str(domain_name)
    return f"domain_{index + 1}"


def _rating_value(value: object) -> float:
    if value in (None, "", False):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return 0.0


def _evaluation_summary(
    evaluation: Evaluation,
) -> tuple[int, int, dict[str, float], float | None]:
    content_data = evaluation.content_data or []
    question_count = 0
    answered_question_count = 0
    domain_means: dict[str, float] = {}
    means: list[float] = []

    for index, domain in enumerate(content_data):
        questions = domain.get("questions") or []
        if not isinstance(questions, list):
            continue
        domain_question_count = len(questions)
        question_count += domain_question_count
        rating_total = 0.0
        for question in questions:
            rating = question.get("rating") if isinstance(question, dict) else None
            if rating not in (None, "", False):
                answered_question_count += 1
                rating_total += _rating_value(rating)
        if domain_question_count:
            mean = round(rating_total / domain_question_count, 2)
            domain_means[_current_domain_key(domain, index)] = mean
            means.append(mean)

    overall_mean = round(sum(means) / len(means), 2) if means else None
    return answered_question_count, question_count, domain_means, overall_mean


async def list_questionnaires(
    session: AsyncSession, include_inactive: bool = False
) -> list[Questionnaire]:
    return await QuestionnaireRepository(session).list(include_inactive=include_inactive)


async def create_questionnaire(
    session: AsyncSession, payload: QuestionnaireCreateRequest
) -> Questionnaire:
    repository = QuestionnaireRepository(session)
    code = payload.code.strip().upper()
    if await repository.get_by_code(code):
        raise ConflictError("Questionnaire code already exists.")
    questionnaire = Questionnaire(
        code=code,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        content=payload.content,
        is_active=payload.is_active,
    )
    return await repository.create(questionnaire)


async def update_questionnaire(
    session: AsyncSession, questionnaire_id: int, payload: QuestionnaireUpdateRequest
) -> Questionnaire:
    repository = QuestionnaireRepository(session)
    questionnaire = await repository.get_by_id(questionnaire_id)
    if questionnaire is None:
        raise NotFoundError("Questionnaire not found.")
    if payload.code is not None:
        code = payload.code.strip().upper()
        existing = await repository.get_by_code(code)
        if existing is not None and existing.id != questionnaire_id:
            raise ConflictError("Questionnaire code already exists.")
        questionnaire.code = code
    if payload.title is not None:
        questionnaire.title = payload.title.strip()
    if payload.description is not None:
        questionnaire.description = payload.description.strip() if payload.description else None
    if payload.content is not None:
        questionnaire.content = payload.content
    if payload.is_active is not None:
        questionnaire.is_active = payload.is_active
    return await repository.save(questionnaire)


async def delete_questionnaire(session: AsyncSession, questionnaire_id: int) -> None:
    repository = QuestionnaireRepository(session)
    questionnaire = await repository.get_by_id(questionnaire_id)
    if questionnaire is None:
        raise NotFoundError("Questionnaire not found.")
    await repository.delete(questionnaire)


async def list_user_evaluations(
    session: AsyncSession,
    evaluatee_id: int | None = None,
    questionnaire_id: int | None = None,
    quarter: str | None = None,
    year: int | None = None,
    is_finalized: bool | None = None,
) -> list[UserEvaluation]:
    return await UserEvaluationRepository(session).list(
        evaluatee_id=evaluatee_id,
        questionnaire_id=questionnaire_id,
        quarter=quarter,
        year=year,
        is_finalized=is_finalized,
    )


async def create_user_evaluation(
    session: AsyncSession, payload: UserEvaluationCreateRequest
) -> UserEvaluation:
    user_repository = UserRepository(session)
    questionnaire_repository = QuestionnaireRepository(session)
    user = await user_repository.get_by_id(payload.evaluatee_id)
    if user is None:
        raise NotFoundError("User not found.")
    questionnaire = await questionnaire_repository.get_by_id(payload.questionnaire_id)
    if questionnaire is None:
        raise NotFoundError("Questionnaire not found.")

    repository = UserEvaluationRepository(session)
    existing = await repository.get_by_identity(
        payload.evaluatee_id,
        payload.questionnaire_id,
        payload.quarter,
        payload.year,
    )
    if existing is not None:
        raise ConflictError("User evaluation already exists.")

    item = UserEvaluation(
        evaluatee_id=payload.evaluatee_id,
        questionnaire_id=payload.questionnaire_id,
        quarter=payload.quarter,
        year=payload.year,
        is_finalized=False,
    )
    return await repository.create(item)


async def update_user_evaluation(
    session: AsyncSession, user_evaluation_id: int, payload: UserEvaluationUpdateRequest
) -> UserEvaluation:
    repository = UserEvaluationRepository(session)
    item = await repository.get_by_id(user_evaluation_id)
    if item is None:
        raise NotFoundError("User evaluation not found.")
    if payload.questionnaire_id is not None:
        questionnaire = await QuestionnaireRepository(session).get_by_id(payload.questionnaire_id)
        if questionnaire is None:
            raise NotFoundError("Questionnaire not found.")
        item.questionnaire_id = payload.questionnaire_id
    if payload.quarter is not None:
        item.quarter = payload.quarter
    if payload.year is not None:
        item.year = payload.year
    if payload.is_finalized is not None:
        item.is_finalized = payload.is_finalized
    return await repository.save(item)


async def toggle_user_evaluation_finalized(
    session: AsyncSession, user_evaluation_id: int
) -> UserEvaluation:
    repository = UserEvaluationRepository(session)
    item = await repository.get_by_id(user_evaluation_id)
    if item is None:
        raise NotFoundError("User evaluation not found.")
    item.is_finalized = not item.is_finalized
    return await repository.save(item)


async def reset_user_evaluation(
    session: AsyncSession, user_evaluation_id: int
) -> UserEvaluation:
    repository = UserEvaluationRepository(session)
    item = await repository.get_by_id(user_evaluation_id)
    if item is None:
        raise NotFoundError("User evaluation not found.")
    item.is_finalized = False
    for evaluation in item.evaluations:
        questionnaire = evaluation.questionnaire
        evaluation.content_data = _copy_questionnaire_content(questionnaire)
        evaluation.positive_feedback = None
        evaluation.improvement_suggestion = None
        evaluation.date_submitted = None
    return await repository.save(item)


async def delete_user_evaluation(session: AsyncSession, user_evaluation_id: int) -> None:
    repository = UserEvaluationRepository(session)
    item = await repository.get_by_id(user_evaluation_id)
    if item is None:
        raise NotFoundError("User evaluation not found.")
    await repository.delete(item)


async def list_evaluations(
    session: AsyncSession,
    user_evaluation_id: int | None = None,
    evaluator_id: int | None = None,
    is_submitted: bool | None = None,
) -> list[Evaluation]:
    return await EvaluationRepository(session).list(
        user_evaluation_id=user_evaluation_id,
        evaluator_id=evaluator_id,
        is_submitted=is_submitted,
    )


async def create_evaluation(
    session: AsyncSession,
    user_evaluation_id: int,
    evaluator_id: int,
    payload: EvaluationCreateRequest,
) -> Evaluation:
    user_repository = UserRepository(session)
    evaluator = await user_repository.get_by_id(evaluator_id)
    if evaluator is None:
        raise NotFoundError("User not found.")

    user_evaluation_repository = UserEvaluationRepository(session)
    user_evaluation = await user_evaluation_repository.get_by_id(user_evaluation_id)
    if user_evaluation is None:
        raise NotFoundError("User evaluation not found.")

    repository = EvaluationRepository(session)
    existing = await repository.get_by_identity(user_evaluation_id, evaluator_id)
    if existing is not None:
        return await update_evaluation(
            session,
            existing.id,
            EvaluationUpdateRequest(
                positive_feedback=payload.positive_feedback,
                improvement_suggestion=payload.improvement_suggestion,
                content_data=payload.content_data,
            ),
        )

    questionnaire = user_evaluation.questionnaire
    item = Evaluation(
        evaluator_id=evaluator_id,
        user_evaluation_id=user_evaluation_id,
        questionnaire_id=user_evaluation.questionnaire_id,
        content_data=payload.content_data or _copy_questionnaire_content(questionnaire),
        positive_feedback=payload.positive_feedback.strip() if payload.positive_feedback else None,
        improvement_suggestion=(
            payload.improvement_suggestion.strip() if payload.improvement_suggestion else None
        ),
    )
    return await repository.create(item)


async def update_evaluation(
    session: AsyncSession, evaluation_id: int, payload: EvaluationUpdateRequest
) -> Evaluation:
    repository = EvaluationRepository(session)
    item = await repository.get_by_id(evaluation_id)
    if item is None:
        raise NotFoundError("Evaluation not found.")
    if payload.content_data is not None:
        item.content_data = payload.content_data
    if payload.positive_feedback is not None:
        item.positive_feedback = payload.positive_feedback.strip() or None
    if payload.improvement_suggestion is not None:
        item.improvement_suggestion = payload.improvement_suggestion.strip() or None
    return await repository.save(item)


async def submit_evaluation(session: AsyncSession, evaluation_id: int) -> Evaluation:
    repository = EvaluationRepository(session)
    item = await repository.get_by_id(evaluation_id)
    if item is None:
        raise NotFoundError("Evaluation not found.")
    item.date_submitted = utc_now()
    return await repository.save(item)


async def reset_evaluation(session: AsyncSession, evaluation_id: int) -> Evaluation:
    repository = EvaluationRepository(session)
    item = await repository.get_by_id(evaluation_id)
    if item is None:
        raise NotFoundError("Evaluation not found.")
    questionnaire = item.questionnaire
    item.content_data = _copy_questionnaire_content(questionnaire)
    item.positive_feedback = None
    item.improvement_suggestion = None
    item.date_submitted = None
    return await repository.save(item)


async def delete_evaluation(session: AsyncSession, evaluation_id: int) -> None:
    repository = EvaluationRepository(session)
    item = await repository.get_by_id(evaluation_id)
    if item is None:
        raise NotFoundError("Evaluation not found.")
    await repository.delete(item)


async def get_evaluation_summary(session: AsyncSession, evaluation_id: int) -> EvaluationSummaryRead:
    repository = EvaluationRepository(session)
    item = await repository.get_by_id(evaluation_id)
    if item is None:
        raise NotFoundError("Evaluation not found.")
    answered_question_count, question_count, domain_means, overall_mean = _evaluation_summary(item)
    return EvaluationSummaryRead(
        evaluation_id=item.id,
        is_submitted=item.date_submitted is not None,
        answered_question_count=answered_question_count,
        question_count=question_count,
        domain_means=domain_means,
        overall_mean=overall_mean,
        positive_feedback=item.positive_feedback,
        improvement_suggestion=item.improvement_suggestion,
        self_evaluation=bool(item.evaluator_id == item.user_evaluation.evaluatee_id),
    )
