"""AI Gateway HTTP surface (§27). Thin wrappers over the same services the product flows use."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.deps import DB, CurrentUser
from app.models import InterviewSession, Job, Resume
from app.repositories.base import get_owned
from app.schemas.api import AnswerIn, ChatIn
from app.services import interview_engine, job_service, resume_service, training_service
from app.services.ai.gateway import AIError, AIGateway
from app.services.evaluation import EvalInput, evaluate_answer
from app.services.resume_service import primary_resume
from app.services.usage import check_quota

router = APIRouter(prefix="/ai", tags=["ai"])


def _lang(user, override=None) -> str:
    return override or (user.profile.language if user.profile else None) or user.locale or "ru"


@router.post("/chat")
def chat(body: ChatIn, user: CurrentUser, db: DB):
    try:
        reply = AIGateway(db, user.id).run_text("chat", {"message": body.message, "language": _lang(user, body.language)})
    except AIError as e:
        db.commit()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI provider unavailable") from e
    db.commit()
    return {"reply": reply}


class InterviewTurnIn(AnswerIn):
    session_id: int


@router.post("/interview")
def interview_turn(body: InterviewTurnIn, user: CurrentUser, db: DB):
    session = get_owned(db, InterviewSession, body.session_id, user.id)
    try:
        interview_engine.submit_answer(db, user, session, body.text, body.duration_seconds)
    except interview_engine.InterviewError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    db.commit()
    return interview_engine.session_state(db, session)


class EvaluateIn(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    answer: str = Field(min_length=1, max_length=8000)
    category: str = "technical"
    topic: str = "General"
    ideal_points: list[str] = Field(default_factory=list, max_length=12)
    role: str = "Software Engineer"
    level: str = "middle"
    difficulty: int = Field(default=3, ge=1, le=5)


@router.post("/evaluate")
def evaluate(body: EvaluateIn, user: CurrentUser, db: DB):
    check_quota(db, user, "training_answers")
    res = evaluate_answer(db, user.id, EvalInput(
        role=body.role, level=body.level, category=body.category, topic=body.topic, question=body.question,
        answer=body.answer, ideal_points=body.ideal_points, difficulty=body.difficulty, language=_lang(user), followups_so_far=0,
    ))
    db.commit()
    return {"evaluation": res.data.model_dump(), "consistency": res.consistency, "evaluator": res.evaluator}


class ResumeRef(BaseModel):
    resume_id: int


@router.post("/analyze-resume")
def analyze_resume(body: ResumeRef, user: CurrentUser, db: DB):
    check_quota(db, user, "resume_analyses")
    resume = get_owned(db, Resume, body.resume_id, user.id)
    resume_service.analyze_resume(db, user, resume, _lang(user))
    db.commit()
    return resume.analysis


class JobRef(BaseModel):
    job_id: int


@router.post("/analyze-job")
def analyze_job(body: JobRef, user: CurrentUser, db: DB):
    job = get_owned(db, Job, body.job_id, user.id)
    job_service.analyze_job(db, user, job, primary_resume(db, user.id), _lang(user))
    db.commit()
    return {"analysis": job.analysis, "match": job.match, "blueprint": job.blueprint}


@router.post("/generate-plan")
def generate_plan(user: CurrentUser, db: DB):
    plan = training_service.generate_plan(db, user, job_id=user.profile.active_job_id if user.profile else None,
                                          source_session_id=None, language=_lang(user))
    db.commit()
    return {"plan_id": plan.id}
