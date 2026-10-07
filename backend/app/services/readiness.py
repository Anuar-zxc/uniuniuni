"""Interview Readiness: weighted, recency-aware, difficulty-adjusted, penalised by critical weaknesses.

score = 0.85 * (Σ w_c * est_c  −  weakness_penalty)  +  0.15 * job_match       (when a job match exists)
est_c  = Bayesian-shrunk weighted mean of evidence in category c, where each evaluation is weighted by
         recency (half-life 14 days), by session (latest session counts more) and adjusted by difficulty
         relative to the target interview. Categories with no evidence shrink towards a low prior (unknown = risk).
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InterviewEvaluation, InterviewQuestion, InterviewSession, Job, Profile, ReadinessSnapshot, TrainingTask, Weakness
from app.services.prediction import base_weights

PRIOR = 35.0
PRIOR_STRENGTH = 1.0
HALF_LIFE_DAYS = 14
SEVERITY_PENALTY = {"critical": 5.0, "high": 3.0, "medium": 1.0, "low": 0.0}
CATEGORY_GROUP = {"debugging": "technical", "architecture": "system_design", "domain": "technical",
                  "situational": "behavioral", "communication": "behavioral"}


def status_for(score: float) -> str:
    if score >= 80:
        return "READY"
    if score >= 65:
        return "ALMOST_READY"
    if score >= 45:
        return "NEEDS_WORK"
    return "NOT_READY"


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _weights_for(db: Session, user_id: int, job: Job | None) -> dict[str, float]:
    if job and job.blueprint.get("weights"):
        return dict(job.blueprint["weights"])
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    return base_weights(profile.role_family if profile else None, profile.level if profile else None)


def compute(db: Session, user_id: int, job: Job | None) -> dict:
    now = datetime.now(UTC)
    weights: dict[str, float] = {}
    for k, v in _weights_for(db, user_id, job).items():
        g = CATEGORY_GROUP.get(k, k)
        weights[g] = weights.get(g, 0.0) + v
    target_diff = (job.analysis or {}).get("expected_difficulty", 3) if job else 3

    sessions = db.scalars(
        select(InterviewSession).where(InterviewSession.user_id == user_id, InterviewSession.status == "completed")
        .order_by(InterviewSession.finished_at.desc())
    ).all()
    latest_id = sessions[0].id if sessions else None
    evidence: dict[str, list[tuple[float, float]]] = {}

    if sessions:
        rows = db.execute(
            select(InterviewEvaluation, InterviewQuestion.difficulty, InterviewSession.id)
            .join(InterviewQuestion, InterviewQuestion.id == InterviewEvaluation.question_id)
            .join(InterviewSession, InterviewSession.id == InterviewEvaluation.session_id)
            .where(InterviewSession.user_id == user_id, InterviewSession.status == "completed")
        ).all()
        for ev, qdiff, sid in rows:
            age = (now - _aware(ev.created_at)).total_seconds() / 86400
            w = 0.5 ** (age / HALF_LIFE_DAYS) * (1.5 if sid == latest_id else 1.0)
            adj = ev.score * (1 + 0.05 * ((qdiff or 3) - target_diff))
            cat = CATEGORY_GROUP.get(ev.category, ev.category)
            evidence.setdefault(cat, []).append((max(0.0, min(100.0, adj)), w))

    for t in db.scalars(select(TrainingTask).where(TrainingTask.user_id == user_id, TrainingTask.status == "completed")).all():
        if t.score is None or t.completed_at is None:
            continue
        age = (now - _aware(t.completed_at)).total_seconds() / 86400
        cat = CATEGORY_GROUP.get(t.category, t.category)
        evidence.setdefault(cat, []).append((t.score, 0.6 * 0.5 ** (age / HALF_LIFE_DAYS)))  # practice counts less

    categories: dict[str, dict] = {}
    for cat in set(weights) | set(evidence):
        ev = evidence.get(cat, [])
        sw = sum(w for _, w in ev)
        est = (sum(s * w for s, w in ev) + PRIOR * PRIOR_STRENGTH) / (sw + PRIOR_STRENGTH)
        categories[cat] = {"score": round(est, 1), "weight": weights.get(cat, 0.0), "evidence": len(ev),
                           "confidence": "high" if sw >= 3 else "medium" if sw >= 1 else "low"}

    total_w = sum(weights.values()) or 1
    base = sum(categories[c]["score"] * w for c, w in weights.items()) / total_w

    weaknesses = db.scalars(select(Weakness).where(Weakness.user_id == user_id, Weakness.status != "resolved")).all()
    penalty = 0.0
    for wk in weaknesses:
        cat = CATEGORY_GROUP.get(wk.category, wk.category)
        factor = 1.0 if weights.get(cat, 0) >= 0.1 else 0.5
        penalty += SEVERITY_PENALTY.get(wk.severity, 0) * factor
    penalty = min(penalty, 15.0)

    core = max(0.0, base - penalty)
    match = job.match_score if job and job.match_score is not None else None
    score = 0.85 * core + 0.15 * match if match is not None else core
    score = round(max(0.0, min(100.0, score)), 1)

    n_evidence = sum(c["evidence"] for c in categories.values())
    risks = _risks(categories, weights, weaknesses, job)
    return {
        "score": score,
        "status": status_for(score),
        "confidence": "high" if n_evidence >= 15 else "medium" if n_evidence >= 5 else "low",
        "breakdown": {"categories": categories, "base": round(base, 1), "weakness_penalty": round(penalty, 1),
                      "job_match": match, "sessions": len(sessions)},
        "risks": risks,
    }


def _risks(categories: dict, weights: dict, weaknesses: list[Weakness], job: Job | None) -> list[dict]:
    risks: list[dict] = []
    for wk in sorted(weaknesses, key=lambda w: ({"critical": 0, "high": 1}.get(w.severity, 2), w.current_score)):
        if wk.severity in ("critical", "high"):
            cat_w = weights.get(CATEGORY_GROUP.get(wk.category, wk.category), 0.05)
            impact = SEVERITY_PENALTY[wk.severity] * 10 + (100 - wk.current_score) * cat_w
            risks.append({"type": "weakness", "title": wk.topic, "category": wk.category,
                          "detail": f"{round(wk.current_score)}/100 after {wk.attempts} attempt(s)", "impact": round(impact, 1)})
    for cat, w in weights.items():
        c = categories.get(cat, {})
        gap = (100 - c.get("score", PRIOR)) * w
        if c.get("evidence", 0) == 0 and w >= 0.1:
            risks.append({"type": "untested", "title": cat, "category": cat, "detail": "not practised yet", "impact": round(gap, 1)})
        elif c.get("score", 100) < 65:
            risks.append({"type": "category", "title": cat, "category": cat,
                          "detail": f"{round(c['score'])}/100", "impact": round(gap, 1)})
    if job and job.match:
        for skill in job.match.get("missing", [])[:3]:
            risks.append({"type": "missing_skill", "title": skill, "category": "technical",
                          "detail": "required by the vacancy, not found in CV", "impact": 25.0})
    seen, out = set(), []
    for r in sorted(risks, key=lambda r: -r["impact"]):
        if r["title"] not in seen:
            seen.add(r["title"])
            out.append(r)
    return out[:3]


def recompute(db: Session, user_id: int, trigger: str) -> ReadinessSnapshot:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    job = db.get(Job, profile.active_job_id) if profile and profile.active_job_id else None
    result = compute(db, user_id, job)
    snap = ReadinessSnapshot(
        user_id=user_id, job_id=job.id if job else None, score=result["score"], status=result["status"],
        breakdown=result["breakdown"] | {"confidence": result["confidence"]}, risks=result["risks"], trigger=trigger,
    )
    db.add(snap)
    db.flush()
    return snap


def latest(db: Session, user_id: int) -> ReadinessSnapshot | None:
    return db.scalar(
        select(ReadinessSnapshot).where(ReadinessSnapshot.user_id == user_id).order_by(ReadinessSnapshot.id.desc()).limit(1)
    )
