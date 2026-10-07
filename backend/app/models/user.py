from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, JSONType, TimestampMixin


class Organization(IdMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(40), default="company")  # university|bootcamp|school|agency|company
    seats: Mapped[int] = mapped_column(Integer, default=10)


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user")  # user | admin
    auth_provider: Mapped[str] = mapped_column(String(20), default="password")
    locale: Mapped[str] = mapped_column(String(5), default="ru")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    org_role: Mapped[str | None] = mapped_column(String(20), nullable=True)  # member | manager

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class Profile(IdMixin, TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    desired_role: Mapped[str | None] = mapped_column(String(80), nullable=True)
    role_family: Mapped[str | None] = mapped_column(String(40), nullable=True)
    level: Mapped[str | None] = mapped_column(String(20), nullable=True)  # junior|middle|senior
    stack: Mapped[list] = mapped_column(JSONType, default=list)
    target_company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    interview_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="ru")
    interview_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    active_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped[User] = relationship(back_populates="profile")
