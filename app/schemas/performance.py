from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.schemas.user import UserRead


class QuestionnaireRead(BaseModel):
    id: int
    code: str
    title: str
    description: str | None = None
    content: dict = Field(default_factory=dict)
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionnaireCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    content: dict = Field(default_factory=dict)
    is_active: bool = True


class QuestionnaireUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    content: dict | None = None
    is_active: bool | None = None


class UserEvaluationRead(BaseModel):
    id: int
    evaluatee_id: int
    questionnaire_id: int
    quarter: str
    year: int
    is_finalized: bool
    evaluatee: UserRead | None = None
    questionnaire: QuestionnaireRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserEvaluationCreateRequest(BaseModel):
    evaluatee_id: int
    questionnaire_id: int
    quarter: str = Field(pattern="^(FQ|SQ)$")
    year: int = Field(ge=1)


class UserEvaluationUpdateRequest(BaseModel):
    questionnaire_id: int | None = None
    quarter: str | None = Field(default=None, pattern="^(FQ|SQ)$")
    year: int | None = Field(default=None, ge=1)
    is_finalized: bool | None = None


class EvaluationRead(BaseModel):
    id: int
    evaluator_id: int
    user_evaluation_id: int
    questionnaire_id: int
    positive_feedback: str | None = None
    improvement_suggestion: str | None = None
    content_data: list[dict] = Field(default_factory=list)
    date_submitted: datetime | None = None
    evaluator: UserRead | None = None
    questionnaire: QuestionnaireRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationCreateRequest(BaseModel):
    positive_feedback: str | None = None
    improvement_suggestion: str | None = None
    content_data: list[dict] = Field(default_factory=list)


class EvaluationUpdateRequest(BaseModel):
    positive_feedback: str | None = None
    improvement_suggestion: str | None = None
    content_data: list[dict] | None = None


class EvaluationSummaryRead(BaseModel):
    evaluation_id: int
    is_submitted: bool
    answered_question_count: int
    question_count: int
    domain_means: dict[str, float] = Field(default_factory=dict)
    overall_mean: float | None = None
    positive_feedback: str | None = None
    improvement_suggestion: str | None = None
    self_evaluation: bool
