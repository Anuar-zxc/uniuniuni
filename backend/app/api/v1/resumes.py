from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.core.deps import DB, CurrentUser
from app.models import Resume
from app.repositories.base import get_owned, list_owned
from app.schemas.api import ResumeOut, ResumeTextIn
from app.services import readiness, resume_service
from app.services.resume_parser import ResumeParseError
from app.services.storage import get_storage
from app.services.usage import check_quota, increment

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _lang(db, user) -> str:
    return (user.profile.language if user.profile else None) or user.locale or "ru"


def _analyze(db, user, resume: Resume) -> Resume:
    check_quota(db, user, "resume_analyses")
    resume_service.analyze_resume(db, user, resume, _lang(db, user))
    increment(db, user.id, "resume_analyses")
    readiness.recompute(db, user.id, trigger="resume")
    db.commit()
    return resume


@router.post("", response_model=ResumeOut, status_code=201)
def upload_resume(user: CurrentUser, db: DB, file: UploadFile = File(...)):
    check_quota(db, user, "resume_analyses")
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)  # sync route: runs in threadpool, never blocks the event loop
    try:
        resume = resume_service.create_resume(db, user, file.filename or "cv", file.content_type or "", data)
    except ResumeParseError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e
    return _analyze(db, user, resume)


@router.post("/text", response_model=ResumeOut, status_code=201)
def paste_resume(body: ResumeTextIn, user: CurrentUser, db: DB):
    check_quota(db, user, "resume_analyses")
    try:
        resume = resume_service.create_resume_from_text(db, user, body.text)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e
    return _analyze(db, user, resume)


@router.get("", response_model=list[ResumeOut])
def list_resumes(user: CurrentUser, db: DB):
    return list_owned(db, Resume, user.id)


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: int, user: CurrentUser, db: DB):
    return get_owned(db, Resume, resume_id, user.id)


@router.post("/{resume_id}/analyze", response_model=ResumeOut)
def reanalyze(resume_id: int, user: CurrentUser, db: DB):
    return _analyze(db, user, get_owned(db, Resume, resume_id, user.id))


@router.delete("/{resume_id}")
def delete_resume(resume_id: int, user: CurrentUser, db: DB):
    resume = get_owned(db, Resume, resume_id, user.id)
    if resume.storage_key:
        get_storage().delete(resume.storage_key)
    db.delete(resume)
    db.commit()
    return {"ok": True}
