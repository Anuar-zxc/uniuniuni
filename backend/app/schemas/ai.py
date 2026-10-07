"""Strict schemas for every structured LLM output. Lenient on shape, strict on ranges."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal["low", "medium", "high", "critical"]
CATEGORIES = [
    "technical", "coding", "system_design", "project_deep_dive", "behavioral", "hr",
    "communication", "architecture", "debugging", "situational", "domain",
]


def _clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, v))


def _norm_category(v: str) -> str:
    v = (v or "technical").strip().lower().replace(" ", "_").replace("-", "_")
    return v if v in CATEGORIES else "technical"


class ResumeScores(BaseModel):
    ats: float = 50
    technical: float = 50
    impact: float = 50
    clarity: float = 50
    experience: float = 50

    @field_validator("*", mode="before")
    @classmethod
    def clamp(cls, v):
        return _clamp(v)


class ResumeProject(BaseModel):
    name: str = ""
    summary: str = ""
    technologies: list[str] = Field(default_factory=list)


class BulletQuestions(BaseModel):
    bullet: str
    questions: list[str] = Field(default_factory=list)


class ResumeAnalysisAI(BaseModel):
    candidate_name: str | None = None
    headline: str | None = None
    seniority: Literal["intern", "junior", "middle", "senior", "lead"] = "junior"
    years_experience: float = 0
    domain: str | None = None
    role_family: str | None = None
    technologies: list[str] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    suspicious_claims: list[str] = Field(default_factory=list)
    measurable_impact: list[str] = Field(default_factory=list)
    technical_depth: str | None = None
    communication_signals: list[str] = Field(default_factory=list)
    scores: ResumeScores = Field(default_factory=ResumeScores)
    likely_questions: list[BulletQuestions] = Field(default_factory=list)

    @field_validator("seniority", mode="before")
    @classmethod
    def norm_seniority(cls, v):
        v = str(v or "junior").lower()
        for s in ("intern", "junior", "middle", "senior", "lead"):
            if s in v:
                return s
        return "junior"

    @field_validator("years_experience", mode="before")
    @classmethod
    def norm_years(cls, v):
        return _clamp(v, 0, 50)


class JobAnalysisAI(BaseModel):
    title: str | None = None
    company: str | None = None
    level: Literal["junior", "middle", "senior", "lead"] | None = None
    role_family: str | None = None
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    interview_topics: list[str] = Field(default_factory=list)
    likely_stages: list[str] = Field(default_factory=list)
    expected_difficulty: int = 3
    weak_matches: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("level", mode="before")
    @classmethod
    def norm_level(cls, v):
        if not v:
            return None
        v = str(v).lower()
        for s in ("junior", "middle", "senior", "lead"):
            if s in v:
                return s
        return None

    @field_validator("expected_difficulty", mode="before")
    @classmethod
    def norm_diff(cls, v):
        return int(_clamp(v, 1, 5))


class AnswerEvaluationAI(BaseModel):
    score: float
    correctness: float
    depth: float
    communication: float
    technical_accuracy: float
    missing_points: list[str] = Field(default_factory=list)
    follow_up_needed: bool = False
    follow_up_reason: Literal["shallow", "generic", "contested", "error", "probe", "none"] = "none"
    severity: Severity = "low"
    skills_detected: list[str] = Field(default_factory=list)
    mistakes: list[str] = Field(default_factory=list)
    correct_concept: str = ""
    feedback: str = ""

    @field_validator("score", "correctness", "depth", "communication", "technical_accuracy", mode="before")
    @classmethod
    def clamp(cls, v):
        return _clamp(v)

    @field_validator("severity", mode="before")
    @classmethod
    def norm_sev(cls, v):
        v = str(v or "low").lower()
        return v if v in ("low", "medium", "high", "critical") else "medium"

    @field_validator("follow_up_reason", mode="before")
    @classmethod
    def norm_reason(cls, v):
        v = str(v or "none").lower()
        return v if v in ("shallow", "generic", "contested", "error", "probe", "none") else "probe"


class InterviewerTurnAI(BaseModel):
    message: str


class CategoryNarrative(BaseModel):
    category: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    @field_validator("category", mode="before")
    @classmethod
    def norm(cls, v):
        return _norm_category(v)


class ReportNarrativeAI(BaseModel):
    summary: str = ""
    categories: list[CategoryNarrative] = Field(default_factory=list)
    top_recommendations: list[str] = Field(default_factory=list)


class PracticeQuestion(BaseModel):
    text: str
    ideal_points: list[str] = Field(default_factory=list)


class TrainingQuestionsAI(BaseModel):
    questions: list[PracticeQuestion] = Field(default_factory=list)


class WeaknessInsightAI(BaseModel):
    correct_concept: str = ""
    why_weak: str = ""
    recommended_exercise: str = ""
