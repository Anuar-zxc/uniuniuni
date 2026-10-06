from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import IdMixin, JSONType, TimestampMixin


class Weakness(IdMixin, TimestampMixin, Base):
    """Error Memory: one row per (user, topic); updated on every new attempt."""

    __tablename__ = "weaknesses"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(10))  # low|medium|high|critical
    original_answer: Mapped[str] = mapped_column(Text, default="")
    question_text: Mapped[str] = mapped_column(Text, default="")
    correct_concept: Mapped[str] = mapped_column(Text, default="")
    why_weak: Mapped[str] = mapped_column(Text, default="")
    recommended_exercise: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|improving|resolved
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    first_score: Mapped[float] = mapped_column(Float)
    current_score: Mapped[float] = mapped_column(Float)
    best_score: Mapped[float] = mapped_column(Float)
    history: Mapped[list] = mapped_column(JSONType, default=list)  # [{at, score, source}]
    next_retest_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrainingPlan(IdMixin, TimestampMixin, Base):
    __tablename__ = "training_plans"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_session_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|completed|archived
    starts_on: Mapped[date] = mapped_column(Date)
    days: Mapped[int] = mapped_column(Integer, default=5)


class TrainingTask(IdMixin, TimestampMixin, Base):
    __tablename__ = "training_tasks"

    plan_id: Mapped[int] = mapped_column(ForeignKey("training_plans.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day: Mapped[int] = mapped_column(Integer)
    topic: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40))
    weakness_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kind: Mapped[str] = mapped_column(String(20), default="questions")  # questions|case
    questions: Mapped[list] = mapped_column(JSONType, default=list)  # [{text, ideal_points}]
    answers: Mapped[list] = mapped_column(JSONType, default=list)  # [{index, text, score, feedback}]
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|in_progress|completed
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReadinessSnapshot(IdMixin, TimestampMixin, Base):
    __tablename__ = "readiness_snapshots"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20))
    breakdown: Mapped[dict] = mapped_column(JSONType, default=dict)
    risks: Mapped[list] = mapped_column(JSONType, default=list)
    trigger: Mapped[str] = mapped_column(String(30), default="interview")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
