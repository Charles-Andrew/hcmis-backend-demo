from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.performance import Evaluation, Questionnaire, UserEvaluation
from app.models.user import User


class QuestionnaireRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, include_inactive: bool = False) -> list[Questionnaire]:
        statement = select(Questionnaire).order_by(Questionnaire.title)
        if not include_inactive:
            statement = statement.where(Questionnaire.is_active.is_(True))
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, questionnaire_id: int) -> Questionnaire | None:
        result = await self.session.execute(
            select(Questionnaire).where(Questionnaire.id == questionnaire_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Questionnaire | None:
        result = await self.session.execute(
            select(Questionnaire).where(Questionnaire.code == code.upper())
        )
        return result.scalar_one_or_none()

    async def create(self, questionnaire: Questionnaire) -> Questionnaire:
        self.session.add(questionnaire)
        await self.session.commit()
        await self.session.refresh(questionnaire)
        return questionnaire

    async def save(self, questionnaire: Questionnaire) -> Questionnaire:
        await self.session.commit()
        await self.session.refresh(questionnaire)
        return questionnaire

    async def delete(self, questionnaire: Questionnaire) -> None:
        await self.session.delete(questionnaire)
        await self.session.commit()


class UserEvaluationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        evaluatee_id: int | None = None,
        questionnaire_id: int | None = None,
        quarter: str | None = None,
        year: int | None = None,
        is_finalized: bool | None = None,
    ) -> list[UserEvaluation]:
        statement = (
            select(UserEvaluation)
            .options(
                selectinload(UserEvaluation.evaluatee).selectinload(User.department),
                selectinload(UserEvaluation.questionnaire),
                selectinload(UserEvaluation.evaluations),
            )
            .order_by(UserEvaluation.year.desc(), UserEvaluation.quarter.desc())
        )
        if evaluatee_id is not None:
            statement = statement.where(UserEvaluation.evaluatee_id == evaluatee_id)
        if questionnaire_id is not None:
            statement = statement.where(UserEvaluation.questionnaire_id == questionnaire_id)
        if quarter is not None:
            statement = statement.where(UserEvaluation.quarter == quarter)
        if year is not None:
            statement = statement.where(UserEvaluation.year == year)
        if is_finalized is not None:
            statement = statement.where(UserEvaluation.is_finalized.is_(is_finalized))
        result = await self.session.execute(statement)
        return list(result.scalars().unique().all())

    async def get_by_id(self, user_evaluation_id: int) -> UserEvaluation | None:
        result = await self.session.execute(
            select(UserEvaluation)
            .options(
                selectinload(UserEvaluation.evaluatee).selectinload(User.department),
                selectinload(UserEvaluation.questionnaire),
                selectinload(UserEvaluation.evaluations)
                .selectinload(Evaluation.evaluator)
                .selectinload(User.department),
                selectinload(UserEvaluation.evaluations).selectinload(Evaluation.questionnaire),
            )
            .where(UserEvaluation.id == user_evaluation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_identity(
        self,
        evaluatee_id: int,
        questionnaire_id: int,
        quarter: str,
        year: int,
    ) -> UserEvaluation | None:
        result = await self.session.execute(
            select(UserEvaluation).where(
                UserEvaluation.evaluatee_id == evaluatee_id,
                UserEvaluation.questionnaire_id == questionnaire_id,
                UserEvaluation.quarter == quarter,
                UserEvaluation.year == year,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, item: UserEvaluation) -> UserEvaluation:
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def save(self, item: UserEvaluation) -> UserEvaluation:
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def delete(self, item: UserEvaluation) -> None:
        await self.session.delete(item)
        await self.session.commit()


class EvaluationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        user_evaluation_id: int | None = None,
        evaluator_id: int | None = None,
        is_submitted: bool | None = None,
    ) -> list[Evaluation]:
        statement = (
            select(Evaluation)
            .options(
                selectinload(Evaluation.evaluator).selectinload(User.department),
                selectinload(Evaluation.user_evaluation)
                .selectinload(UserEvaluation.evaluatee)
                .selectinload(User.department),
                selectinload(Evaluation.user_evaluation).selectinload(UserEvaluation.questionnaire),
                selectinload(Evaluation.questionnaire),
            )
            .order_by(Evaluation.created_at.desc())
        )
        if user_evaluation_id is not None:
            statement = statement.where(Evaluation.user_evaluation_id == user_evaluation_id)
        if evaluator_id is not None:
            statement = statement.where(Evaluation.evaluator_id == evaluator_id)
        if is_submitted is not None:
            if is_submitted:
                statement = statement.where(Evaluation.date_submitted.is_not(None))
            else:
                statement = statement.where(Evaluation.date_submitted.is_(None))
        result = await self.session.execute(statement)
        return list(result.scalars().unique().all())

    async def get_by_id(self, evaluation_id: int) -> Evaluation | None:
        result = await self.session.execute(
            select(Evaluation)
            .options(
                selectinload(Evaluation.evaluator).selectinload(User.department),
                selectinload(Evaluation.user_evaluation)
                .selectinload(UserEvaluation.evaluatee)
                .selectinload(User.department),
                selectinload(Evaluation.user_evaluation).selectinload(UserEvaluation.questionnaire),
                selectinload(Evaluation.questionnaire),
            )
            .where(Evaluation.id == evaluation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_identity(self, user_evaluation_id: int, evaluator_id: int) -> Evaluation | None:
        result = await self.session.execute(
            select(Evaluation).where(
                Evaluation.user_evaluation_id == user_evaluation_id,
                Evaluation.evaluator_id == evaluator_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, item: Evaluation) -> Evaluation:
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def save(self, item: Evaluation) -> Evaluation:
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def delete(self, item: Evaluation) -> None:
        await self.session.delete(item)
        await self.session.commit()
