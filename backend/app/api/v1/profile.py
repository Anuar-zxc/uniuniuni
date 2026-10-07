from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core.deps import DB, CurrentUser, client_ip
from app.models import (
    AIRequest,
    Application,
    AuditLog,
    Event,
    Interview,
    InterviewAnswer,
    InterviewSession,
    Job,
    Profile,
    ReadinessSnapshot,
    Resume,
    Weakness,
)
from app.repositories.base import get_owned
from app.schemas.api import MeOut, ProfileIn, ProfileOut, UserOut
from app.services.storage import get_storage
from app.services.usage import current_plan, get_usage, track

router = APIRouter(prefix="/profile", tags=["profile"])


def _me(db, user) -> MeOut:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    plan = current_plan(db, user)
    usage = {m: {"used": get_usage(db, user.id, m), "limit": lim} for m, lim in (plan.limits or {}).items()}
    return MeOut(user=UserOut.model_validate(user), profile=ProfileOut.model_validate(profile) if profile else None,
                 plan={"code": plan.code, "name": plan.name, "features": plan.features}, usage=usage)


@router.get("", response_model=MeOut)
def get_me(user: CurrentUser, db: DB):
    return _me(db, user)


@router.patch("", response_model=MeOut)
def update_me(body: ProfileIn, user: CurrentUser, db: DB):
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        profile = Profile(user_id=user.id, language=user.locale)
        db.add(profile)
    data = body.model_dump(exclude_unset=True)
    if "name" in data:
        user.name = data.pop("name")
    if "locale" in data:
        user.locale = data.pop("locale")
    if data.get("active_job_id"):
        get_owned(db, Job, data["active_job_id"], user.id)
    was_done = profile.onboarding_completed
    for k, v in data.items():
        setattr(profile, k, v)
    if profile.onboarding_completed and not was_done:
        track(db, user.id, "onboarding_completed")
    db.commit()
    return _me(db, user)


@router.get("/export")
def export_data(user: CurrentUser, db: DB, request: Request):
    """GDPR-style data export of everything we store about the user."""

    def rows(model, cols):
        return [{c: getattr(r, c) for c in cols} for r in db.scalars(select(model).where(model.user_id == user.id))]

    db.add(AuditLog(actor_id=user.id, action="privacy.export", ip=client_ip(request)))
    db.commit()
    return {
        "user": UserOut.model_validate(user).model_dump(),
        "resumes": rows(Resume, ["id", "filename", "text", "analysis", "created_at"]),
        "jobs": rows(Job, ["id", "title", "company_name", "description", "analysis", "match", "created_at"]),
        "interviews": rows(Interview, ["id", "title", "mode", "language", "created_at"]),
        "sessions": rows(InterviewSession, ["id", "interview_id", "status", "overall_score", "report", "created_at"]),
        "weaknesses": rows(Weakness, ["id", "topic", "category", "severity", "status", "attempts", "history"]),
        "readiness": rows(ReadinessSnapshot, ["id", "score", "status", "created_at"]),
        "applications": rows(Application, ["id", "company", "role", "status", "notes"]),
    }


@router.delete("", status_code=200)
def delete_account(user: CurrentUser, db: DB, request: Request):
    """Right to erasure: deletes the account, files and all personal data (cascades)."""
    storage = get_storage()
    for r in db.scalars(select(Resume).where(Resume.user_id == user.id)):
        if r.storage_key:
            storage.delete(r.storage_key)
    session_ids = db.scalars(select(InterviewSession.id).where(InterviewSession.user_id == user.id)).all()
    if session_ids:
        for a in db.scalars(select(InterviewAnswer).where(InterviewAnswer.session_id.in_(session_ids))):
            db.delete(a)
    for model in (AIRequest, Event):
        for row in db.scalars(select(model).where(model.user_id == user.id)):
            db.delete(row)
    db.add(AuditLog(actor_id=None, action="privacy.account_deleted", entity="user", entity_id=str(user.id), ip=client_ip(request)))
    db.delete(user)
    db.commit()
    return {"ok": True}
