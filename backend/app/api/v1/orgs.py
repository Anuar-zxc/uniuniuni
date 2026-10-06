"""B2B: organization dashboard for universities, bootcamps, agencies and companies."""

from collections import Counter

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core.deps import DB, CurrentUser
from app.models import InterviewSession, Organization, ReadinessSnapshot, User, Weakness

router = APIRouter(prefix="/orgs", tags=["organizations"])


@router.get("/{org_id}/dashboard")
def org_dashboard(org_id: int, user: CurrentUser, db: DB):
    org = db.get(Organization, org_id)
    allowed = user.role == "admin" or (user.organization_id == org_id and user.org_role == "manager")
    if org is None or not allowed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    members = db.scalars(select(User).where(User.organization_id == org_id)).all()
    ids = [m.id for m in members]
    latest: dict[int, float] = {}
    first: dict[int, float] = {}
    for s in db.scalars(select(ReadinessSnapshot).where(ReadinessSnapshot.user_id.in_(ids)).order_by(ReadinessSnapshot.id)) if ids else []:
        first.setdefault(s.user_id, s.score)
        latest[s.user_id] = s.score
    weak = Counter(w.topic for w in db.scalars(select(Weakness).where(Weakness.user_id.in_(ids), Weakness.status != "resolved"))) if ids else Counter()
    interviews = db.scalar(select(func.count(InterviewSession.id)).where(InterviewSession.user_id.in_(ids), InterviewSession.status == "completed")) if ids else 0
    return {
        "organization": {"id": org.id, "name": org.name, "kind": org.kind, "seats": org.seats},
        "users": [{"id": m.id, "name": m.name, "email": m.email, "readiness": latest.get(m.id),
                   "progress": round(latest[m.id] - first[m.id], 1) if m.id in latest else None} for m in members],
        "average_readiness": round(sum(latest.values()) / len(latest), 1) if latest else None,
        "common_weaknesses": [{"topic": t, "users": n} for t, n in weak.most_common(10)],
        "interviews_completed": interviews or 0,
    }
