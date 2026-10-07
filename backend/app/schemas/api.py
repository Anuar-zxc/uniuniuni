"""Request/response schemas for the public API."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Lang = Literal["ru", "en", "kk"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- auth / profile


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=200)
    locale: Lang = "ru"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginIn(BaseModel):
    id_token: str


class UserOut(ORM):
    id: int
    email: str
    name: str | None
    role: str
    locale: str
    organization_id: int | None


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ProfileOut(ORM):
    desired_role: str | None
    role_family: str | None
    level: str | None
    stack: list[str]
    target_company: str | None
    interview_date: date | None
    language: str
    interview_type: str | None
    onboarding_completed: bool
    active_job_id: int | None


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    desired_role: str | None = Field(default=None, max_length=80)
    role_family: str | None = Field(default=None, max_length=40)
    level: Literal["junior", "middle", "senior"] | None = None
    stack: list[str] | None = Field(default=None, max_length=40)
    target_company: str | None = Field(default=None, max_length=200)
    interview_date: date | None = None
    language: Lang | None = None
    interview_type: str | None = Field(default=None, max_length=40)
    onboarding_completed: bool | None = None
    active_job_id: int | None = None
    locale: Lang | None = None


class MeOut(BaseModel):
    user: UserOut
    profile: ProfileOut | None
    plan: dict
    usage: dict


# ---------------------------------------------------------------- resume / job


class ResumeOut(ORM):
    id: int
    filename: str
    status: str
    overall_score: float | None
    analysis: dict
    is_primary: bool
    created_at: datetime


class ResumeTextIn(BaseModel):
    text: str = Field(min_length=80, max_length=30000)


class JobIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    description: str = Field(min_length=40, max_length=20000)
    source_url: str | None = Field(default=None, max_length=500)
    interview_date: date | None = None


class JobOut(ORM):
    id: int
    title: str
    company_name: str | None
    level: str | None
    description: str
    interview_date: date | None
    status: str
    analysis: dict
    match: dict
    match_score: float | None
    blueprint: dict
    created_at: datetime


class ApplicationIn(BaseModel):
    company: str = Field(max_length=200)
    role: str = Field(max_length=200)
    job_id: int | None = None
    status: Literal["saved", "applied", "recruiter", "technical", "onsite", "offer", "rejected"] = "saved"
    applied_on: date | None = None
    interview_date: date | None = None
    salary: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=5000)


class ApplicationOut(ApplicationIn, ORM):
    id: int


# ---------------------------------------------------------------- interviews


class InterviewCreateIn(BaseModel):
    job_id: int | None = None
    mode: str = "mixed"
    language: Lang | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)


class AnswerIn(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    duration_seconds: int | None = Field(default=None, ge=0, le=7200)


class SessionSummary(BaseModel):
    session_id: int
    interview_id: int
    title: str
    mode: str
    status: str
    overall_score: float | None
    started_at: datetime | None
    finished_at: datetime | None


# ---------------------------------------------------------------- weaknesses / training


class WeaknessOut(ORM):
    id: int
    topic: str
    category: str
    severity: str
    original_answer: str
    question_text: str
    correct_concept: str
    why_weak: str
    recommended_exercise: str
    status: str
    attempts: int
    first_score: float
    current_score: float
    best_score: float
    history: list
    next_retest_at: datetime | None


class TrainingTaskOut(ORM):
    id: int
    day: int
    topic: str
    category: str
    kind: str
    questions: list
    answers: list
    status: str
    score: float | None
    weakness_id: int | None


class TrainingPlanOut(BaseModel):
    id: int
    status: str
    starts_on: date
    days: int
    tasks: list[TrainingTaskOut]


class TrainingAnswerIn(BaseModel):
    index: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=6000)


# ---------------------------------------------------------------- billing


class PlanOut(ORM):
    code: str
    name: str
    prices: dict
    interval: str
    limits: dict
    features: list


class CheckoutIn(BaseModel):
    plan_code: str
    currency: Literal["KZT", "USD"] = "KZT"
    provider: str | None = None


class SandboxConfirmIn(BaseModel):
    external_id: str


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    language: Lang | None = None
