from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.schemas.user import UserRead


class SharedResourceUploaderRead(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str

    model_config = ConfigDict(from_attributes=True)


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
    evaluatee_id: UUID
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
    evaluatee_id: UUID
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
    evaluator_id: UUID
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
    evaluator_id: UUID | None = None
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


class EvaluationAssignmentRequest(BaseModel):
    evaluator_id: UUID


class UserEvaluationDomainSummaryRead(BaseModel):
    domain_key: str
    self_rating_mean: float
    peer_rating_mean: float


class UserEvaluationAggregateRead(BaseModel):
    user_evaluation_id: int
    evaluatee_id: UUID
    questionnaire_id: int
    quarter: str
    year: int
    is_finalized: bool
    self_rating_overall_mean: float
    peer_rating_overall_mean: float
    domains: list[UserEvaluationDomainSummaryRead] = Field(default_factory=list)
    peer_positive_feedback: list[str] = Field(default_factory=list)
    peer_improvement_suggestions: list[str] = Field(default_factory=list)


class SharedResourceRead(BaseModel):
    id: int
    uploader_id: UUID
    uploader: SharedResourceUploaderRead | None = None
    resource_name: str
    description: str | None = None
    original_filename: str
    content_type: str | None = None
    size_bytes: int
    is_confidential: bool
    shared_user_ids: list[UUID] = Field(default_factory=list)
    confidential_access_user_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SharedResourceCreateRequest(BaseModel):
    resource_name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    storage_key: str = Field(min_length=1, max_length=500)
    original_filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=255)
    size_bytes: int = Field(default=0, ge=0)
    shared_user_ids: list[UUID] = Field(default_factory=list)
    is_confidential: bool = False
    confidential_access_user_ids: list[UUID] = Field(default_factory=list)


class SharedResourceUpdateRequest(BaseModel):
    resource_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_confidential: bool | None = None


class SharedResourceAccessUpdateRequest(BaseModel):
    user_id: UUID


class SharedResourceAccessReplaceRequest(BaseModel):
    shared_user_ids: list[UUID] = Field(default_factory=list)
    confidential_access_user_ids: list[UUID] = Field(default_factory=list)


class AnnouncementRead(BaseModel):
    id: int
    author_id: UUID
    title: str
    summary: str | None = None
    content: str
    status: str
    published_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    summary: str | None = None
    content: str = Field(min_length=1)


class AnnouncementUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    summary: str | None = None
    content: str | None = Field(default=None, min_length=1)


class PollChoiceCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=255)


class PollChoiceRead(BaseModel):
    id: int
    poll_id: int
    text: str
    position: int
    vote_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PollRead(BaseModel):
    id: int
    author_id: UUID
    question: str
    description: str | None = None
    allow_multiple_choices: bool
    status: str
    published_at: datetime | None = None
    closed_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    choices: list[PollChoiceRead] = Field(default_factory=list)
    user_vote_choice_ids: list[int] = Field(default_factory=list)


class PollCreateRequest(BaseModel):
    question: str = Field(min_length=1, max_length=255)
    description: str | None = None
    allow_multiple_choices: bool = False
    choices: list[PollChoiceCreateRequest] = Field(min_length=2)


class PollUpdateRequest(BaseModel):
    question: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    allow_multiple_choices: bool | None = None


class PollVoteSubmitRequest(BaseModel):
    choice_ids: list[int] = Field(min_length=1)


class FeedItemRead(BaseModel):
    item_type: str
    announcement: AnnouncementRead | None = None
    poll: PollRead | None = None
