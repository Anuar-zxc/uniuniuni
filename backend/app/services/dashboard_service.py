from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Application, InterviewSession, Job, Profile, ReadinessSnapshot, TrainingTask, User, Weakness
from app.services import readiness
from app.services.resume_service import primary_resume
from app.services.weakness_service import due_for_retest, recurring

WEAKEST_CATEGORY_MODE = {"system_design": "system_design", "coding": "coding", "behavioral": "behavioral",
                         "hr": "hr", "project_deep_dive": "project_deep_dive"}


def next_best_action(db: Session, user: User, profile: Profile | None, job: Job | None, snap: ReadinessSnapshot | None) -> dict:
    if primary_resume(db, user.id) is None:
        return {"action": "upload_resume", "href": "/resume"}
    if job is None:
        return {"action": "add_job", "href": "/jobs/new"}
    completed = db.scalar(select(func.count(InterviewSession.id)).where(InterviewSession.user_id == user.id, InterviewSession.status == "completed"))
    if not completed:
        return {"action": "start_interview", "mode": "mixed", "href": f"/interviews/new?job={job.id}&mode=mixed"}
    task = db.scalar(select(TrainingTask).where(TrainingTask.user_id == user.id, TrainingTask.status != "completed")
                     .order_by(TrainingTask.plan_id.desc(), TrainingTask.day).limit(1))
    due = due_for_retest(db, user.id, limit=1)
    if due and (task is None or task.weakness_id != due[0].id):
        return {"action": "retest", "topic": due[0].topic, "href": f"/interviews/new?job={job.id}&mode=mixed"}
    if task is not None:
        return {"action": "do_training", "topic": task.topic, "task_id": task.id, "href": f"/training#task-{task.id}"}
    if snap and snap.score < 80:
        cats = snap.breakdown.get("categories", {})
        weakest = min(cats.items(), key=lambda kv: kv[1].get("score", 100) if kv[1].get("weight", 0) >= 0.1 else 100, default=None)
        mode = WEAKEST_CATEGORY_MODE.get(weakest[0], "technical") if weakest else "mixed"
        return {"action": "start_interview", "mode": mode, "href": f"/interviews/new?job={job.id}&mode={mode}"}
    return {"action": "keep_sharp", "mode": "mixed", "href": f"/interviews/new?job={job.id}&mode=mixed"}


def build(db: Session, user: User) -> dict:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    job = db.get(Job, profile.active_job_id) if profile and profile.active_job_id else None
    snap = readiness.latest(db, user.id)
    if snap is None and primary_resume(db, user.id) is not None:
        snap = readiness.recompute(db, user.id, trigger="dashboard")
    history = db.scalars(select(ReadinessSnapshot).where(ReadinessSnapshot.user_id == user.id).order_by(ReadinessSnapshot.id)).all()
    last = db.scalar(select(InterviewSession).where(InterviewSession.user_id == user.id, InterviewSession.status == "completed")
                     .order_by(InterviewSession.id.desc()).limit(1))
    interview_date = (job.interview_date if job else None) or (profile.interview_date if profile else None)
    weak = [w for w in recurring(db, user.id) if w.status != "resolved"][:3]
    tasks = db.scalars(select(TrainingTask).where(TrainingTask.user_id == user.id, TrainingTask.status != "completed")
                       .order_by(TrainingTask.plan_id.desc(), TrainingTask.day).limit(3)).all()
    apps = dict(db.execute(select(Application.status, func.count(Application.id)).where(Application.user_id == user.id)
                           .group_by(Application.status)).all())
    resolved = db.scalar(select(func.count(Weakness.id)).where(Weakness.user_id == user.id, Weakness.status == "resolved")) or 0
    return {
        "readiness": {"score": snap.score, "status": snap.status, "risks": snap.risks,
                      "confidence": snap.breakdown.get("confidence"), "categories": snap.breakdown.get("categories", {})}
        if snap else None,
        "target": {"job_id": job.id, "title": job.title, "company": job.company_name, "match_score": job.match_score}
        if job else None,
        "upcoming_interview": {"date": interview_date.isoformat(), "days_left": (interview_date - date.today()).days}
        if interview_date else None,
        "latest_interview": {"session_id": last.id, "score": last.overall_score,
                             "finished_at": last.finished_at.isoformat() if last.finished_at else None} if last else None,
        "weakest": [{"id": w.id, "topic": w.topic, "severity": w.severity, "current_score": w.current_score,
                     "first_score": w.first_score, "status": w.status} for w in weak],
        "progress": [{"at": s.created_at.isoformat(), "score": s.score} for s in history[-30:]],
        "recommended_training": [{"id": t.id, "day": t.day, "topic": t.topic, "category": t.category, "status": t.status} for t in tasks],
        "applications": apps,
        "resolved_weaknesses": resolved,
        "next_best_action": next_best_action(db, user, profile, job, snap),
    }
