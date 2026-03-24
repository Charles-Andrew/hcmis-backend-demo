import anyio
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.department import Department
from app.models.performance import Evaluation, Questionnaire, UserEvaluation
from app.models.user import User
from app.schemas.performance import (
    EvaluationCreateRequest,
    EvaluationUpdateRequest,
    QuestionnaireCreateRequest,
    UserEvaluationCreateRequest,
)
from app.services import performance as performance_service


class FakeUserRepository:
    users: dict[int, User] = {}

    def __init__(self, session):
        self.session = session

    async def get_by_id(self, user_id: int):
        return self.users.get(user_id)


class FakeQuestionnaireRepository:
    items: dict[int, Questionnaire] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(self, include_inactive: bool = False):
        items = list(self.items.values())
        if not include_inactive:
            items = [item for item in items if item.is_active]
        return items

    async def get_by_id(self, questionnaire_id: int):
        return self.items.get(questionnaire_id)

    async def get_by_code(self, code: str):
        for item in self.items.values():
            if item.code == code.upper():
                return item
        return None

    async def create(self, questionnaire: Questionnaire):
        questionnaire.id = self.next_id
        self.next_id += 1
        questionnaire.created_at = questionnaire.created_at or utc_now()
        questionnaire.updated_at = questionnaire.updated_at or utc_now()
        self.items[questionnaire.id] = questionnaire
        return questionnaire

    async def save(self, questionnaire: Questionnaire):
        questionnaire.updated_at = utc_now()
        self.items[questionnaire.id] = questionnaire
        return questionnaire

    async def delete(self, questionnaire: Questionnaire):
        self.items.pop(questionnaire.id, None)


class FakeUserEvaluationRepository:
    items: dict[int, UserEvaluation] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(
        self,
        evaluatee_id=None,
        questionnaire_id=None,
        quarter=None,
        year=None,
        is_finalized=None,
    ):
        items = list(self.items.values())
        if evaluatee_id is not None:
            items = [item for item in items if item.evaluatee_id == evaluatee_id]
        if questionnaire_id is not None:
            items = [item for item in items if item.questionnaire_id == questionnaire_id]
        if quarter is not None:
            items = [item for item in items if item.quarter == quarter]
        if year is not None:
            items = [item for item in items if item.year == year]
        if is_finalized is not None:
            items = [item for item in items if item.is_finalized == is_finalized]
        return items

    async def get_by_id(self, user_evaluation_id: int):
        return self.items.get(user_evaluation_id)

    async def get_by_identity(self, evaluatee_id: int, questionnaire_id: int, quarter: str, year: int):
        for item in self.items.values():
            if (
                item.evaluatee_id == evaluatee_id
                and item.questionnaire_id == questionnaire_id
                and item.quarter == quarter
                and item.year == year
            ):
                return item
        return None

    async def create(self, item: UserEvaluation):
        item.id = self.next_id
        self.next_id += 1
        item.created_at = item.created_at or utc_now()
        item.updated_at = item.updated_at or utc_now()
        item.evaluatee = FakeUserRepository.users[item.evaluatee_id]
        item.questionnaire = FakeQuestionnaireRepository.items[item.questionnaire_id]
        item.evaluations = []
        self.items[item.id] = item
        return item

    async def save(self, item: UserEvaluation):
        item.updated_at = utc_now()
        self.items[item.id] = item
        return item

    async def delete(self, item: UserEvaluation):
        self.items.pop(item.id, None)


class FakeEvaluationRepository:
    items: dict[int, Evaluation] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(self, user_evaluation_id=None, evaluator_id=None, is_submitted=None):
        items = list(self.items.values())
        if user_evaluation_id is not None:
            items = [item for item in items if item.user_evaluation_id == user_evaluation_id]
        if evaluator_id is not None:
            items = [item for item in items if item.evaluator_id == evaluator_id]
        if is_submitted is not None:
            items = [item for item in items if (item.date_submitted is not None) == is_submitted]
        return items

    async def get_by_id(self, evaluation_id: int):
        return self.items.get(evaluation_id)

    async def get_by_identity(self, user_evaluation_id: int, evaluator_id: int):
        for item in self.items.values():
            if item.user_evaluation_id == user_evaluation_id and item.evaluator_id == evaluator_id:
                return item
        return None

    async def create(self, item: Evaluation):
        item.id = self.next_id
        self.next_id += 1
        item.created_at = item.created_at or utc_now()
        item.updated_at = item.updated_at or utc_now()
        item.evaluator = FakeUserRepository.users[item.evaluator_id]
        item.user_evaluation = FakeUserEvaluationRepository.items[item.user_evaluation_id]
        item.questionnaire = FakeQuestionnaireRepository.items[item.questionnaire_id]
        self.items[item.id] = item
        FakeUserEvaluationRepository.items[item.user_evaluation_id].evaluations.append(item)
        return item

    async def save(self, item: Evaluation):
        item.updated_at = utc_now()
        self.items[item.id] = item
        return item

    async def delete(self, item: Evaluation):
        self.items.pop(item.id, None)


def _reset():
    FakeUserRepository.users = {}
    FakeQuestionnaireRepository.items = {}
    FakeQuestionnaireRepository.next_id = 1
    FakeUserEvaluationRepository.items = {}
    FakeUserEvaluationRepository.next_id = 1
    FakeEvaluationRepository.items = {}
    FakeEvaluationRepository.next_id = 1


def _seed():
    dept = Department(id=1, name="Operations", code="OPS", is_active=True, workweek=[])
    user = User(
        id=1,
        email="employee@example.com",
        password_hash="hashed",
        first_name="Employee",
        last_name="One",
        department_id=1,
        is_active=True,
        is_superuser=False,
        can_modify_shift=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    user.department = dept
    peer = User(
        id=2,
        email="peer@example.com",
        password_hash="hashed",
        first_name="Peer",
        last_name="Two",
        department_id=1,
        is_active=True,
        is_superuser=False,
        can_modify_shift=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    peer.department = dept
    FakeUserRepository.users[1] = user
    FakeUserRepository.users[2] = peer


def test_questionnaire_and_user_evaluation_flow(monkeypatch):
    _reset()
    _seed()
    monkeypatch.setattr(performance_service, "QuestionnaireRepository", FakeQuestionnaireRepository)
    monkeypatch.setattr(performance_service, "UserEvaluationRepository", FakeUserEvaluationRepository)
    monkeypatch.setattr(performance_service, "EvaluationRepository", FakeEvaluationRepository)
    monkeypatch.setattr(performance_service, "UserRepository", FakeUserRepository)

    questionnaire = anyio.run(
        performance_service.create_questionnaire,
        cast(AsyncSession, object()),
        QuestionnaireCreateRequest(
            code="pe-2026",
            title="Performance Evaluation 2026",
            content={
                "questionnaire_content": [
                    {
                        "domain_number": "1",
                        "questions": [
                            {"indicator_number": "1", "rating": None},
                            {"indicator_number": "2", "rating": None},
                        ],
                    }
                ]
            },
        ),
    )
    assert questionnaire.code == "PE-2026"

    user_evaluation = anyio.run(
        performance_service.create_user_evaluation,
        cast(AsyncSession, object()),
        UserEvaluationCreateRequest(
            evaluatee_id=1,
            questionnaire_id=questionnaire.id,
            quarter="FQ",
            year=2026,
        ),
    )
    assert user_evaluation.evaluatee_id == 1
    assert user_evaluation.is_finalized is False

    finalized = anyio.run(
        performance_service.toggle_user_evaluation_finalized,
        cast(AsyncSession, object()),
        user_evaluation.id,
    )
    assert finalized.is_finalized is True


def test_evaluation_summary_and_reset(monkeypatch):
    _reset()
    _seed()
    monkeypatch.setattr(performance_service, "QuestionnaireRepository", FakeQuestionnaireRepository)
    monkeypatch.setattr(performance_service, "UserEvaluationRepository", FakeUserEvaluationRepository)
    monkeypatch.setattr(performance_service, "EvaluationRepository", FakeEvaluationRepository)
    monkeypatch.setattr(performance_service, "UserRepository", FakeUserRepository)

    questionnaire = anyio.run(
        performance_service.create_questionnaire,
        cast(AsyncSession, object()),
        QuestionnaireCreateRequest(
            code="PE-2026",
            title="Performance Evaluation 2026",
            content={
                "questionnaire_content": [
                    {
                        "domain_number": "1",
                        "questions": [
                            {"indicator_number": "1", "rating": None},
                            {"indicator_number": "2", "rating": None},
                        ],
                    }
                ]
            },
        ),
    )
    user_evaluation = anyio.run(
        performance_service.create_user_evaluation,
        cast(AsyncSession, object()),
        UserEvaluationCreateRequest(
            evaluatee_id=1,
            questionnaire_id=questionnaire.id,
            quarter="FQ",
            year=2026,
        ),
    )

    evaluation = anyio.run(
        performance_service.create_evaluation,
        cast(AsyncSession, object()),
        user_evaluation.id,
        1,
        EvaluationCreateRequest(
            content_data=[
                {
                    "domain_number": "1",
                    "questions": [
                        {"indicator_number": "1", "rating": 3},
                        {"indicator_number": "2", "rating": 5},
                    ],
                }
            ],
        ),
    )
    updated = anyio.run(
        performance_service.update_evaluation,
        cast(AsyncSession, object()),
        evaluation.id,
        EvaluationUpdateRequest(positive_feedback="Good", improvement_suggestion="Keep going"),
    )
    assert updated.positive_feedback == "Good"

    submitted = anyio.run(
        performance_service.submit_evaluation,
        cast(AsyncSession, object()),
        evaluation.id,
    )
    assert submitted.date_submitted is not None

    summary = anyio.run(
        performance_service.get_evaluation_summary,
        cast(AsyncSession, object()),
        evaluation.id,
    )
    assert summary.answered_question_count == 2
    assert summary.question_count == 2
    assert summary.overall_mean == 4.0
    assert summary.self_evaluation is True

    reset = anyio.run(
        performance_service.reset_evaluation,
        cast(AsyncSession, object()),
        evaluation.id,
    )
    assert reset.date_submitted is None
    assert reset.positive_feedback is None
