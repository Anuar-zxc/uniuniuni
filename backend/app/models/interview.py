from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import IdMixin, JSONType, TimestampMixin


class Interview(IdMixin, TimestampMixin, Base):
    """An interview target: job + mode + language. Each run is an InterviewSession (retests = new sessions)."""

    __tablename__ = "interviews"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    mode: Mapped[str] = mapped_column(String(30))
    language: Mapped[str] = mapped_column(String(5), default="ru")


class InterviewSession(IdMixin, TimestampMixin, Base):
    __tablename__ = "interview_sessions"

    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")  # in_progress|completed|abandoned
    difficulty: Mapped[int] = mapped_column(Integer, default=3)  # 1..5, adapts during the session
    start_difficulty: Mapped[int] = mapped_column(Integer, default=3)
    planned_main: Mapped[int] = mapped_column(Integer, default=8)
    plan: Mapped[list] = mapped_column(JSONType, default=list)  # [{category, topic, source, weakness_id}]
    current_question_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    category_scores: Mapped[dict] = mapped_column(JSONType, default=dict)
    report: Mapped[dict] = mapped_column(JSONType, default=dict)


class InterviewQuestion(IdMixin, TimestampMixin, Base):
    __tablename__ = "interview_questions"

    session_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True)
    order: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20), default="main")  # main|followup
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[str] = mapped_column(String(40))
    topic: Mapped[str] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    source: Mapped[str] = mapped_column(String(20), default="bank")  # bank|cv|jd|weakness|llm
    weakness_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ideal_points: Mapped[list] = mapped_column(JSONType, default=list)


class InterviewAnswer(IdMixin, TimestampMixin, Base):
    __tablename__ = "interview_answers"

    session_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("interview_questions.id", ondelete="CASCADE"), unique=True)
    text: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)


class InterviewEvaluation(IdMixin, TimestampMixin, Base):
    __tablename__ = "interview_evaluations"

    session_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True)
    answer_id: Mapped[int] = mapped_column(ForeignKey("interview_answers.id", ondelete="CASCADE"), unique=True)
    question_id: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(40))
    topic: Mapped[str] = mapped_column(String(120))
    score: Mapped[float] = mapped_column(Float)
    correctness: Mapped[float] = mapped_column(Float)
    depth: Mapped[float] = mapped_column(Float)
    communication: Mapped[float] = mapped_column(Float)
    technical_accuracy: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(10))
    follow_up_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    missing_points: Mapped[list] = mapped_column(JSONType, default=list)
    skills_detected: Mapped[list] = mapped_column(JSONType, default=list)
    mistakes: Mapped[list] = mapped_column(JSONType, default=list)
    correct_concept: Mapped[str | None] = mapped_column(Text, nullable=True)
    consistency: Mapped[dict] = mapped_column(JSONType, default=dict)
    evaluator: Mapped[str] = mapped_column(String(60), default="llm")
