from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import DB, CurrentUser
from app.models import ReadinessSnapshot, TrainingPlan, TrainingTask, Weakness
from app.repositories.base import get_owned
from app.schemas.api import TrainingAnswerIn, TrainingPlanOut, TrainingTaskOut, WeaknessOut
from app.services import dashboard_service, readiness, training_service
from app.services.usage import check_quota, increment
from app.services.weakness_service import recurring

router = APIRouter(tags=["progress"])


def _lang(user) -> str:
    return (user.profile.language if user.profile else None) or user.locale or "ru"


@router.get("/dashboard")
def dashboard(user: CurrentUser, db: DB):
    data = dashboard_service.build(db, user)
    db.commit()
    return data


@router.get("/readiness")
def get_readiness(user: CurrentUser, db: DB):
    snap = readiness.latest(db, user.id) or readiness.recompute(db, user.id, trigger="manual")
    history = db.scalars(select(ReadinessSnapshot).where(ReadinessSnapshot.user_id == user.id).order_by(ReadinessSnapshot.id)).all()
    db.commit()
    return {"score": snap.score, "status": snap.status, "breakdown": snap.breakdown, "risks": snap.risks,
            "history": [{"at": s.created_at, "score": s.score, "trigger": s.trigger} for s in history[-60:]]}


@router.post("/readiness/recompute")
def recompute_readiness(user: CurrentUser, db: DB):
    snap = readiness.recompute(db, user.id, trigger="manual")
    db.commit()
    return {"score": snap.score, "status": snap.status, "breakdown": snap.breakdown, "risks": snap.risks}


@router.get("/weaknesses", response_model=list[WeaknessOut])
def list_weaknesses(user: CurrentUser, db: DB):
    return recurring(db, user.id)


@router.get("/weaknesses/{weakness_id}", response_model=WeaknessOut)
def get_weakness(weakness_id: int, user: CurrentUser, db: DB):
    return get_owned(db, Weakness, weakness_id, user.id)


@router.get("/training", response_model=TrainingPlanOut | None)
def active_plan(user: CurrentUser, db: DB):
    plan = db.scalar(select(TrainingPlan).where(TrainingPlan.user_id == user.id, TrainingPlan.status.in_(["active", "completed"]))
                     .order_by(TrainingPlan.id.desc()).limit(1))
    if plan is None:
        return None
    tasks = db.scalars(select(TrainingTask).where(TrainingTask.plan_id == plan.id).order_by(TrainingTask.day)).all()
    return TrainingPlanOut(id=plan.id, status=plan.status, starts_on=plan.starts_on, days=plan.days,
                           tasks=[TrainingTaskOut.model_validate(t) for t in tasks])


@router.post("/training/generate", response_model=TrainingPlanOut)
def generate_plan(user: CurrentUser, db: DB):
    profile = user.profile
    training_service.generate_plan(db, user, job_id=profile.active_job_id if profile else None,
                                          source_session_id=None, language=_lang(user))
    db.commit()
    return active_plan(user, db)


@router.post("/training/tasks/{task_id}/answer", response_model=TrainingTaskOut)
def answer_task(task_id: int, body: TrainingAnswerIn, user: CurrentUser, db: DB):
    check_quota(db, user, "training_answers")
    task = get_owned(db, TrainingTask, task_id, user.id)
    try:
        training_service.answer_task(db, user, task, body.index, body.text, _lang(user))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    increment(db, user.id, "training_answers")
    db.commit()
    return task
