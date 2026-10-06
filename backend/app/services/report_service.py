"""Post-interview report: scores per dimension, narrative, Error Memory update, training plan, readiness."""

import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Interview,
    InterviewAnswer,
    InterviewEvaluation,
    InterviewQuestion,
    InterviewSession,
    Job,
    User,
    UserSkill,
)
from app.schemas.ai import ReportNarrativeAI
from app.services import readiness, training_service, weakness_service
from app.services.ai.gateway import AIGateway
from app.services.interview_engine import _context, thread_score
from app.services.usage import track

HEDGE_RE = re.compile(r"\b(maybe|probably|i think|i guess|not sure|наверное|кажется|возможно|вроде|может быть|не уверен|мүмкін|сияқты)\b", re.I)

DIMENSIONS = ["technical_knowledge", "problem_solving", "communication", "system_design", "coding", "behavioral",
              "confidence", "depth", "accuracy"]


def _mean(xs: list[float]) -> float | None:
    return round(sum(xs) / len(xs), 1) if xs else None


def build_report(db: Session, user: User, session: InterviewSession) -> dict:
    interview = db.get(Interview, session.interview_id)
    ctx = _context(db, interview)
    lang = interview.language
    qs = db.scalars(select(InterviewQuestion).where(InterviewQuestion.session_id == session.id).order_by(InterviewQuestion.order)).all()
    evals = {e.question_id: e for e in db.scalars(select(InterviewEvaluation).where(InterviewEvaluation.session_id == session.id))}
    answers = {a.question_id: a for a in db.scalars(select(InterviewAnswer).where(InterviewAnswer.session_id == session.id))}
    evs = list(evals.values())

    # threads → per-topic and per-category scores
    threads: list[dict] = []
    for main in [q for q in qs if q.kind == "main" and q.id in evals]:
        members = [main, *[q for q in qs if q.parent_id == main.id and q.id in evals]]
        t_evals = [evals[m.id] for m in members]
        threads.append({"main": main, "evals": t_evals, "score": thread_score(t_evals)})
    cat_scores: dict[str, list[float]] = {}
    for t in threads:
        cat_scores.setdefault(t["main"].category, []).append(t["score"])
    category_scores = {c: _mean(v) for c, v in cat_scores.items()}

    weights = (ctx["job"].blueprint.get("weights") if ctx["job"] and ctx["job"].blueprint else None) or {}
    present = {c: weights.get(c, 0.1) for c in category_scores}
    tw = sum(present.values()) or 1
    overall = round(sum(category_scores[c] * w for c, w in present.items()) / tw, 1) if present else 0.0

    def by_cats(cats: tuple, attr: str = "score") -> float | None:
        return _mean([getattr(e, attr) for e in evs if e.category in cats])

    all_answers = " ".join(a.text for a in answers.values())
    hedges = len(HEDGE_RE.findall(all_answers))
    idk = sum(1 for e in evs if e.score <= 10)
    confidence = max(0.0, min(100.0, 90 - hedges * 4 - idk * 10)) if evs else None
    dims = {
        "technical_knowledge": by_cats(("technical", "debugging", "architecture", "domain"), "correctness"),
        "problem_solving": by_cats(("coding", "debugging", "system_design", "situational")) or _mean([e.depth for e in evs]),
        "communication": _mean([e.communication for e in evs]),
        "system_design": category_scores.get("system_design"),
        "coding": category_scores.get("coding"),
        "behavioral": by_cats(("behavioral", "hr", "project_deep_dive")),
        "confidence": confidence,
        "depth": _mean([e.depth for e in evs]),
        "accuracy": _mean([e.technical_accuracy for e in evs]),
    }

    digest = []
    for t in threads:
        m = t["main"]
        for e in t["evals"]:
            q = next(q for q in qs if q.id == e.question_id)
            digest.append({
                "category": m.category, "topic": m.topic, "question": q.text[:300],
                "answer": answers[q.id].text[:400] if q.id in answers else "", "score": e.score,
                "missing_points": e.missing_points[:4], "mistakes": e.mistakes[:3],
            })
    gw = AIGateway(db, user.id)
    narrative, _ = gw.run_json(
        "interview_report",
        {"role": ctx["role"], "level": ctx["level"], "mode": interview.mode,
         "scores_json": json.dumps(category_scores), "digest": json.dumps(digest, ensure_ascii=False)[:12000],
         "language": lang},
        ReportNarrativeAI,
        meta={"category_scores": category_scores, "evaluations": digest, "overall": overall},
        fallback=lambda: ReportNarrativeAI(summary=f"{overall}/100"),
        max_tokens=2000,
    )
    narr_by_cat = {c.category: c for c in narrative.categories}

    # dimension details with real examples from the transcript
    def examples_for(cats: tuple) -> dict:
        rel = [d for d in digest if d["category"] in cats]
        if not rel:
            return {}
        best, worst = max(rel, key=lambda d: d["score"]), min(rel, key=lambda d: d["score"])
        return {"best": {"question": best["question"], "answer": best["answer"], "score": best["score"]},
                "worst": {"question": worst["question"], "answer": worst["answer"], "score": worst["score"],
                          "missing_points": worst["missing_points"]}}

    dim_cats = {
        "technical_knowledge": ("technical", "debugging", "architecture", "domain"), "problem_solving": ("coding", "debugging", "system_design"),
        "system_design": ("system_design",), "coding": ("coding",), "behavioral": ("behavioral", "hr", "project_deep_dive"),
    }
    dimensions = []
    for d in DIMENSIONS:
        if dims[d] is None:
            continue
        cats = dim_cats.get(d, tuple(category_scores))
        n = [narr_by_cat[c] for c in cats if c in narr_by_cat]
        dimensions.append({
            "key": d, "score": dims[d],
            "strengths": [s for x in n for s in x.strengths][:3],
            "weaknesses": [s for x in n for s in x.weaknesses][:3],
            "recommendations": [s for x in n for s in x.recommendations][:3],
            "examples": examples_for(cats),
        })

    # Error Memory
    stored = []
    for t in threads:
        m, worst = t["main"], min(t["evals"], key=lambda e: e.score)
        w = weakness_service.record_attempt(
            db, user_id=user.id, topic=m.topic, category=m.category, score=t["score"],
            severity=worst.severity if t["score"] < 70 else "low", question=m.text,
            answer=answers[m.id].text if m.id in answers else "", correct_concept=worst.correct_concept or "",
            mistakes=worst.mistakes, missing_points=worst.missing_points, language=lang,
            source="retest" if m.weakness_id else "interview",
        )
        if w is not None:
            stored.append(w.id)
    _update_user_skills(db, user.id, threads)

    prev = db.scalar(
        select(InterviewSession).where(InterviewSession.interview_id == interview.id, InterviewSession.status == "completed",
                                       InterviewSession.id != session.id).order_by(InterviewSession.id.desc()).limit(1)
    )
    session.overall_score = overall
    session.category_scores = category_scores
    plan = training_service.generate_plan(db, user, job_id=interview.job_id, source_session_id=session.id, language=lang)
    snap = readiness.recompute(db, user.id, trigger="interview")
    report = {
        "overall": overall, "summary": narrative.summary, "top_recommendations": narrative.top_recommendations,
        "category_scores": category_scores, "dimensions": dimensions,
        "topics": [{"topic": t["main"].topic, "category": t["main"].category, "score": t["score"],
                    "followups": len(t["evals"]) - 1, "retest": bool(t["main"].weakness_id)} for t in threads],
        "weakness_ids": stored, "training_plan_id": plan.id,
        "readiness": {"score": snap.score, "status": snap.status},
        "previous_overall": prev.overall_score if prev else None,
        "difficulty": {"start": session.start_difficulty, "end": session.difficulty},
    }
    session.report = report
    first = db.scalar(select(InterviewSession.id).where(InterviewSession.user_id == user.id, InterviewSession.status == "completed",
                                                       InterviewSession.id != session.id).limit(1)) is None
    track(db, user.id, "interview_completed", session_id=session.id, overall=overall, first=first,
          readiness=snap.score)
    db.flush()
    return report


def _update_user_skills(db: Session, user_id: int, threads: list[dict]) -> None:
    for t in threads:
        m = t["main"]
        row = db.scalar(select(UserSkill).where(UserSkill.user_id == user_id, UserSkill.topic == m.topic))
        if row is None:
            row = UserSkill(user_id=user_id, topic=m.topic, category=m.category, score=t["score"], samples=1)
            db.add(row)
        else:  # exponential moving average favours recent performance
            row.score = round(0.6 * t["score"] + 0.4 * row.score, 1)
            row.samples += 1


def job_of(db: Session, session: InterviewSession) -> Job | None:
    interview = db.get(Interview, session.interview_id)
    return db.get(Job, interview.job_id) if interview and interview.job_id else None
