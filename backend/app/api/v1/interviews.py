from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import DB, CurrentUser
from app.models import Interview, InterviewSession
from app.repositories.base import get_owned
from app.schemas.api import AnswerIn, InterviewCreateIn, SessionSummary
from app.services import interview_engine as engine
from app.services.usage import check_quota, increment

router = APIRouter(prefix="/interviews", tags=["interviews"])


def _lang(user) -> str:
    return (user.profile.language if user.profile else None) or user.locale or "ru"


@router.get("/modes")
def modes():
    return {"modes": engine.MODES}


@router.post("", status_code=201)
def create_and_start(body: InterviewCreateIn, user: CurrentUser, db: DB):
    check_quota(db, user, "interviews")
    try:
        interview = engine.create_interview(db, user, job_id=body.job_id, mode=body.mode, language=body.language or _lang(user))
        session = engine.start_session(db, user, interview, body.difficulty)
    except engine.InterviewError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    increment(db, user.id, "interviews")
    db.commit()
    return engine.session_state(db, session)


@router.post("/{interview_id}/retest", status_code=201)
def retest(interview_id: int, user: CurrentUser, db: DB):
    """Run the same interview target again (new session) to measure progress."""
    check_quota(db, user, "interviews")
    interview = get_owned(db, Interview, interview_id, user.id)
    session = engine.start_session(db, user, interview)
    increment(db, user.id, "interviews")
    db.commit()
    return engine.session_state(db, session)


@router.get("/sessions", response_model=list[SessionSummary])
def list_sessions(user: CurrentUser, db: DB):
    rows = db.execute(
        select(InterviewSession, Interview).join(Interview, Interview.id == InterviewSession.interview_id)
        .where(InterviewSession.user_id == user.id).order_by(InterviewSession.id.desc()).limit(100)
    ).all()
    return [SessionSummary(session_id=s.id, interview_id=i.id, title=i.title, mode=i.mode, status=s.status,
                           overall_score=s.overall_score, started_at=s.started_at, finished_at=s.finished_at) for s, i in rows]


@router.get("/sessions/{session_id}")
def get_session(session_id: int, user: CurrentUser, db: DB):
    return engine.session_state(db, get_owned(db, InterviewSession, session_id, user.id))


@router.post("/sessions/{session_id}/answer")
def answer(session_id: int, body: AnswerIn, user: CurrentUser, db: DB):
    session = get_owned(db, InterviewSession, session_id, user.id)
    try:
        engine.submit_answer(db, user, session, body.text, body.duration_seconds)
    except engine.InterviewError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    db.commit()
    return engine.session_state(db, session)


@router.post("/sessions/{session_id}/finish")
def finish(session_id: int, user: CurrentUser, db: DB):
    session = get_owned(db, InterviewSession, session_id, user.id)
    engine.finish(db, user, session)
    db.commit()
    return engine.session_state(db, session)


@router.get("/sessions/{session_id}/report")
def report(session_id: int, user: CurrentUser, db: DB):
    session = get_owned(db, InterviewSession, session_id, user.id)
    if session.status != "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Interview is not completed yet")
    interview = db.get(Interview, session.interview_id)
    history = db.scalars(
        select(InterviewSession).where(InterviewSession.interview_id == interview.id, InterviewSession.status == "completed")
        .order_by(InterviewSession.id)
    ).all()
    return {
        **session.report,
        "session_id": session.id, "interview_id": interview.id, "title": interview.title, "mode": interview.mode,
        "finished_at": session.finished_at, "transcript": engine.session_state(db, session)["transcript"],
        "attempts": [{"session_id": s.id, "score": s.overall_score, "category_scores": s.category_scores,
                      "finished_at": s.finished_at} for s in history],
    }
