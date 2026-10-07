from fastapi import APIRouter

from app.core.deps import DB, CurrentUser
from app.models import Application, Job
from app.repositories.base import get_owned, list_owned
from app.schemas.api import ApplicationIn, ApplicationOut, JobIn, JobOut
from app.services import job_service, readiness
from app.services.resume_service import primary_resume
from app.services.usage import check_quota, increment

router = APIRouter(tags=["jobs"])


def _lang(user) -> str:
    return (user.profile.language if user.profile else None) or user.locale or "ru"


@router.post("/jobs", response_model=JobOut, status_code=201)
def create_job(body: JobIn, user: CurrentUser, db: DB):
    check_quota(db, user, "job_analyses")
    resume = primary_resume(db, user.id)
    job = job_service.create_job(db, user, title=body.title, company_name=body.company_name, description=body.description,
                                 source_url=body.source_url, interview_date=body.interview_date,
                                 resume_id=resume.id if resume else None)
    job_service.analyze_job(db, user, job, resume, _lang(user))
    increment(db, user.id, "job_analyses")
    readiness.recompute(db, user.id, trigger="job")
    db.commit()
    return job


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(user: CurrentUser, db: DB):
    return list_owned(db, Job, user.id)


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, user: CurrentUser, db: DB):
    return get_owned(db, Job, job_id, user.id)


@router.post("/jobs/{job_id}/analyze", response_model=JobOut)
def reanalyze_job(job_id: int, user: CurrentUser, db: DB):
    job = get_owned(db, Job, job_id, user.id)
    job_service.analyze_job(db, user, job, primary_resume(db, user.id), _lang(user))
    readiness.recompute(db, user.id, trigger="job")
    db.commit()
    return job


@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, user: CurrentUser, db: DB):
    job = get_owned(db, Job, job_id, user.id)
    if user.profile and user.profile.active_job_id == job.id:
        user.profile.active_job_id = None
    db.delete(job)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- application tracker


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(user: CurrentUser, db: DB):
    return list_owned(db, Application, user.id, limit=500)


@router.post("/applications", response_model=ApplicationOut, status_code=201)
def create_application(body: ApplicationIn, user: CurrentUser, db: DB):
    if body.job_id:
        get_owned(db, Job, body.job_id, user.id)
    app_ = Application(user_id=user.id, **body.model_dump())
    db.add(app_)
    db.commit()
    return app_


@router.put("/applications/{app_id}", response_model=ApplicationOut)
def update_application(app_id: int, body: ApplicationIn, user: CurrentUser, db: DB):
    app_ = get_owned(db, Application, app_id, user.id)
    for k, v in body.model_dump().items():
        setattr(app_, k, v)
    db.commit()
    return app_


@router.delete("/applications/{app_id}")
def delete_application(app_id: int, user: CurrentUser, db: DB):
    db.delete(get_owned(db, Application, app_id, user.id))
    db.commit()
    return {"ok": True}
