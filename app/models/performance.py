from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.time import utc_now
from app.models.base import Base


class Questionnaire(Base):
    __tablename__ = "questionnaires"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user_evaluations = relationship(
        "UserEvaluation",
        back_populates="questionnaire",
        cascade="all, delete-orphan",
    )
    evaluations = relationship("Evaluation", back_populates="questionnaire")


class UserEvaluation(Base):
    __tablename__ = "user_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "evaluatee_id",
            "questionnaire_id",
            "quarter",
            "year",
            name="uq_user_evaluations_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    evaluatee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    questionnaire_id: Mapped[int] = mapped_column(ForeignKey("questionnaires.id"), index=True)
    quarter: Mapped[str] = mapped_column(String(2), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    evaluatee = relationship("User")
    questionnaire = relationship("Questionnaire", back_populates="user_evaluations")
    evaluations = relationship(
        "Evaluation",
        back_populates="user_evaluation",
        cascade="all, delete-orphan",
    )


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        UniqueConstraint(
            "user_evaluation_id",
            "evaluator_id",
            name="uq_evaluations_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    evaluator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    user_evaluation_id: Mapped[int] = mapped_column(ForeignKey("user_evaluations.id"), index=True)
    questionnaire_id: Mapped[int] = mapped_column(ForeignKey("questionnaires.id"), index=True)
    positive_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    improvement_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_data: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    date_submitted: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    evaluator = relationship("User")
    user_evaluation = relationship("UserEvaluation", back_populates="evaluations")
    questionnaire = relationship("Questionnaire", back_populates="evaluations")
