from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import IdMixin, JSONType, TimestampMixin


class Resume(IdMixin, TimestampMixin, Base):
    __tablename__ = "resumes"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    storage_key: Mapped[str | None] = mapped_column(String(400), nullable=True)
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="uploaded")  # uploaded|analyzed|failed
    analysis: Mapped[dict] = mapped_column(JSONType, default=dict)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)


class Company(IdMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(200), unique=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    website: Mapped[str | None] = mapped_column(String(300), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Only legitimate public or user-provided information; never invented insider details.
    public_interview_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class RoleCatalog(IdMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    family: Mapped[str] = mapped_column(String(40))
    blueprint: Mapped[dict] = mapped_column(JSONType, default=dict)  # {level: {category: weight}}


class Skill(IdMixin, TimestampMixin, Base):
    __tablename__ = "skills"

    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40))
    aliases: Mapped[list] = mapped_column(JSONType, default=list)


class UserSkill(IdMixin, TimestampMixin, Base):
    __tablename__ = "user_skills"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40))
    score: Mapped[float] = mapped_column(Float, default=0)
    samples: Mapped[int] = mapped_column(Integer, default=0)


class Job(IdMixin, TimestampMixin, Base):
    __tablename__ = "jobs"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    interview_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="created")  # created|analyzed|failed
    analysis: Mapped[dict] = mapped_column(JSONType, default=dict)
    match: Mapped[dict] = mapped_column(JSONType, default=dict)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    blueprint: Mapped[dict] = mapped_column(JSONType, default=dict)


class Application(IdMixin, TimestampMixin, Base):
    __tablename__ = "applications"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    company: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="saved")
    applied_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    interview_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    salary: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
