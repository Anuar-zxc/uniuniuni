from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import IdMixin, JSONType, TimestampMixin


class Question(IdMixin, TimestampMixin, Base):
    """Curated question bank, managed in admin."""

    __tablename__ = "questions"

    category: Mapped[str] = mapped_column(String(40), index=True)
    topic: Mapped[str] = mapped_column(String(120), index=True)
    role_family: Mapped[str] = mapped_column(String(40), default="any")
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    text: Mapped[str] = mapped_column(Text)
    ideal_points: Mapped[list] = mapped_column(JSONType, default=list)
    language: Mapped[str] = mapped_column(String(5), default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Prompt(IdMixin, TimestampMixin, Base):
    """Versioned prompt templates. Exactly one active version per key."""

    __tablename__ = "prompts"
    __table_args__ = (UniqueConstraint("key", "version"),)

    key: Mapped[str] = mapped_column(String(60), index=True)
    version: Mapped[int] = mapped_column(Integer)
    system: Mapped[str] = mapped_column(Text)
    user_template: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AIRequest(IdMixin, TimestampMixin, Base):
    __tablename__ = "ai_requests"

    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    task: Mapped[str] = mapped_column(String(60), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(80))
    prompt_key: Mapped[str | None] = mapped_column(String(60), nullable=True)
    prompt_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ok")  # ok|error|invalid|fallback
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)


class Plan(IdMixin, TimestampMixin, Base):
    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(30), unique=True)  # free|pro|premium|org
    name: Mapped[str] = mapped_column(String(80))
    prices: Mapped[dict] = mapped_column(JSONType, default=dict)  # {"KZT": 4990, "USD": 12}
    interval: Mapped[str] = mapped_column(String(10), default="month")
    limits: Mapped[dict] = mapped_column(JSONType, default=dict)  # {"interviews": 1, ...}; -1 = unlimited
    features: Mapped[list] = mapped_column(JSONType, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Subscription(IdMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    organization_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plan_code: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|active|past_due|canceled
    provider: Mapped[str] = mapped_column(String(30))
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="KZT")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Payment(IdMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    subscription_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider: Mapped[str] = mapped_column(String(30))
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|succeeded|failed|refunded
    raw: Mapped[dict] = mapped_column(JSONType, default=dict)


class Usage(IdMixin, TimestampMixin, Base):
    __tablename__ = "usage"
    __table_args__ = (UniqueConstraint("user_id", "period", "metric"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    metric: Mapped[str] = mapped_column(String(40))
    count: Mapped[int] = mapped_column(Integer, default=0)


class AuditLog(IdMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    actor_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str | None] = mapped_column(String(60), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    meta: Mapped[dict] = mapped_column(JSONType, default=dict)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Event(IdMixin, TimestampMixin, Base):
    """Product analytics events (activation, first interview, conversion, ...)."""

    __tablename__ = "events"

    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(60), index=True)
    props: Mapped[dict] = mapped_column(JSONType, default=dict)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
