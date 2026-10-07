"""Interview Engine: plans the interview, phrases questions like a human interviewer, asks follow-ups,
adapts difficulty, revisits weak spots, and keeps the full context of the current interview."""

import random
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Interview,
    InterviewAnswer,
    InterviewEvaluation,
    InterviewQuestion,
    InterviewSession,
    Job,
    Profile,
    Question,
    Resume,
    User,
    Weakness,
)
from app.schemas.ai import InterviewerTurnAI
from app.services import heuristics
from app.services.ai.gateway import AIGateway
from app.services.evaluation import EvalInput, evaluate_answer
from app.services.prediction import base_weights, family_key
from app.services.usage import track
from app.services.weakness_service import due_for_retest

MODES = [
    "technical", "coding", "system_design", "behavioral", "hr", "recruiter_screening", "project_deep_dive",
    "ml", "frontend", "backend", "devops", "mixed",
]
MODE_CATEGORIES: dict[str, dict[str, float]] = {
    "technical": {"technical": 0.75, "debugging": 0.25},
    "coding": {"coding": 1.0},
    "system_design": {"system_design": 1.0},
    "behavioral": {"behavioral": 0.8, "project_deep_dive": 0.2},
    "hr": {"hr": 0.7, "behavioral": 0.3},
    "recruiter_screening": {"hr": 0.5, "behavioral": 0.3, "project_deep_dive": 0.2},
    "project_deep_dive": {"project_deep_dive": 1.0},
    "ml": {"technical": 0.6, "system_design": 0.2, "coding": 0.2},
    "frontend": {"technical": 0.7, "architecture": 0.1, "coding": 0.2},
    "backend": {"technical": 0.6, "debugging": 0.15, "coding": 0.25},
    "devops": {"technical": 0.7, "debugging": 0.3},
}
MODE_FAMILY = {"ml": "ml", "frontend": "frontend", "backend": "backend", "devops": "devops"}
MAIN_QUESTIONS = {"system_design": 2, "coding": 3, "mixed": 8}
DEFAULT_MAIN = 7
PERSONA = {
    "hr": "an experienced HR interviewer", "recruiter_screening": "a technical recruiter",
    "behavioral": "an engineering manager", "system_design": "a staff engineer",
}
GENERIC_PROJECT_POINTS = ["clear context and goal", "personal contribution", "technical decisions and trade-offs",
                          "measurable result", "what you would do differently"]


class InterviewError(ValueError):
    pass


# --------------------------------------------------------------------------- context helpers


def _context(db: Session, interview: Interview) -> dict:
    profile = db.scalar(select(Profile).where(Profile.user_id == interview.user_id))
    job = db.get(Job, interview.job_id) if interview.job_id else None
    resume = db.get(Resume, interview.resume_id) if interview.resume_id else None
    family = MODE_FAMILY.get(interview.mode) or (job.blueprint.get("family") if job and job.blueprint else None) \
        or (profile.role_family if profile else None) or (resume.analysis.get("role_family") if resume else None)
    level = (job.level if job else None) or (profile.level if profile else None) or "middle"
    role = (job.title if job else None) or (profile.desired_role if profile else None) or "Software Engineer"
    return {"profile": profile, "job": job, "resume": resume, "family": family_key(family), "level": level, "role": role,
            "company": (job.company_name if job else None) or (profile.target_company if profile else None)}


def _allocate(weights: dict[str, float], n: int) -> list[str]:
    total = sum(weights.values()) or 1
    raw = {k: v / total * n for k, v in weights.items()}
    counts = {k: int(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - counts[k], reverse=True)[: n - sum(counts.values())]:
        counts[k] += 1
    order = sorted(weights, key=lambda k: -weights[k])
    slots: list[str] = []
    # interleave so the interview flows across categories, starting with the heaviest
    while len(slots) < n and any(c > 0 for c in counts.values()):
        for k in order:
            if counts.get(k, 0) > 0:
                slots.append(k)
                counts[k] -= 1
    # conventional interview arc: warm-up (hr / project) first, behavioral near the end
    warm = next((s for s in slots if s in ("hr", "project_deep_dive")), None)
    if warm:
        slots.remove(warm)
    others = [s for s in slots if s != "behavioral"]
    behavioral = [s for s in slots if s == "behavioral"]
    return ([warm] if warm else []) + others + behavioral


def _build_plan(db: Session, user_id: int, interview: Interview, ctx: dict) -> list[dict]:
    n = MAIN_QUESTIONS.get(interview.mode, DEFAULT_MAIN)
    if interview.mode == "mixed":
        weights = (ctx["job"].blueprint.get("weights") if ctx["job"] and ctx["job"].blueprint else None) \
            or base_weights(ctx["family"], ctx["level"])
    else:
        weights = MODE_CATEGORIES[interview.mode]
    plan: list[dict] = []
    for w in due_for_retest(db, user_id, limit=2):
        if interview.mode == "mixed" or w.category in weights:
            plan.append({"category": w.category, "topic": w.topic, "source": "weakness", "weakness_id": w.id})
    for cat in _allocate(weights, max(0, n - len(plan))):
        plan.append({"category": cat, "topic": None, "source": "bank", "weakness_id": None})
    return plan[:n]


def _recent_topics(db: Session, user_id: int, limit_sessions: int = 2) -> set[str]:
    ids = db.scalars(
        select(InterviewSession.id).where(InterviewSession.user_id == user_id).order_by(InterviewSession.id.desc()).limit(limit_sessions + 1)
    ).all()
    if not ids:
        return set()
    return set(db.scalars(select(InterviewQuestion.topic).where(InterviewQuestion.session_id.in_(ids))).all())


def _pick_bank_question(db: Session, session: InterviewSession, slot: dict, ctx: dict, asked_topics: set[str]) -> dict:
    cat = slot["category"]
    rng = random.Random(session.id * 1000 + len(asked_topics))
    if slot.get("weakness_id"):
        q = db.scalar(select(Question).where(Question.topic == slot["topic"], Question.is_active.is_(True)).limit(1))
        if q:
            return {"text": q.text, "topic": q.topic, "ideal_points": q.ideal_points, "difficulty": q.difficulty, "source": "weakness"}
        w = db.get(Weakness, slot["weakness_id"])
        return {"text": w.question_text if w else slot["topic"], "topic": slot["topic"], "ideal_points": [],
                "difficulty": session.difficulty, "source": "weakness"}
    if cat == "project_deep_dive" and ctx["resume"] is not None:
        lq = [x for x in (ctx["resume"].analysis or {}).get("likely_questions", []) if x.get("bullet")]
        unused = [x for x in lq if f"CV: {x['bullet'][:100]}" not in asked_topics]
        if unused:
            item = unused[0]
            first_q = (item.get("questions") or ["Tell me more about this."])[0]
            return {"text": f"“{item['bullet']}” — {first_q}", "topic": f"CV: {item['bullet'][:100]}",
                    "ideal_points": GENERIC_PROJECT_POINTS, "difficulty": session.difficulty, "source": "cv"}
    family = ctx["family"]
    families = ["any", family] + (["frontend", "backend"] if family == "fullstack" else [])
    if family == "ml":
        families.append("data")
    stmt = select(Question).where(Question.is_active.is_(True), Question.category == cat, Question.role_family.in_(families))
    candidates = db.scalars(stmt).all() or db.scalars(
        select(Question).where(Question.is_active.is_(True), Question.category == cat)
    ).all()
    fresh = [q for q in candidates if q.topic not in asked_topics] or candidates
    if not fresh:
        fresh = db.scalars(select(Question).where(Question.is_active.is_(True), Question.category == "technical")).all()
    if not fresh:
        raise InterviewError("Question bank is empty — run the seed")
    job_topics = {t["topic"] for t in (ctx["job"].blueprint.get("topics", []) if ctx["job"] and ctx["job"].blueprint else [])}

    def rank(q: Question) -> tuple:
        return (0 if q.topic in job_topics else 1, abs(q.difficulty - session.difficulty), rng.random())

    q = sorted(fresh, key=rank)[0]
    return {"text": q.text, "topic": q.topic, "ideal_points": q.ideal_points, "difficulty": q.difficulty,
            "source": "jd" if q.topic in job_topics else "bank"}


def _history(db: Session, session_id: int, max_turns: int = 12) -> str:
    qs = db.scalars(select(InterviewQuestion).where(InterviewQuestion.session_id == session_id).order_by(InterviewQuestion.order)).all()
    answers = {a.question_id: a.text for a in db.scalars(select(InterviewAnswer).where(InterviewAnswer.session_id == session_id))}
    lines: list[str] = []
    for q in qs[-max_turns:]:
        lines.append(f"Interviewer: {q.text}")
        if q.id in answers:
            lines.append(f"Candidate: {answers[q.id][:1500]}")
    return "\n".join(lines) or "(the interview is just starting)"


def _interviewer_says(db: Session, user_id: int, interview: Interview, session: InterviewSession, ctx: dict,
                      *, action: str, seed: str = "", reason: str = "", missing: list[str] | None = None,
                      first: bool = False) -> str:
    lang = interview.language
    if action == "ask_main":
        instruction = ("Open the interview with a one-sentence greeting, then ask" if first else
                       "Briefly acknowledge the previous answer neutrally (no evaluation), then ask") + \
            f" this question in your own words, keeping its technical meaning exactly: «{seed}»"
        fallback = f"{heuristics.phrase('intro' if first else 'ack', lang)} {seed}"
    elif action == "follow_up":
        hints = {"shallow": "the answer was too shallow — ask them to go deeper on the mechanism",
                 "generic": "the answer was generic — ask for a concrete example from their own experience",
                 "contested": "they made a debatable claim — ask why they believe it",
                 "error": "they made an error — do NOT correct it; ask a question that lets them find it themselves",
                 "probe": "the answer was decent — probe trade-offs, edge cases or scale"}
        instruction = f"Ask ONE follow-up question: {hints.get(reason, hints['probe'])}."
        if missing:
            instruction += f" Aspects they missed (never reveal them directly): {'; '.join(missing[:3])}."
        fallback = heuristics.phrase(reason if reason in heuristics.PHRASES else "probe", lang)
    else:
        instruction = "Close the interview politely in 1-2 sentences. Do not give scores or feedback."
        fallback = heuristics.phrase("closing", lang)
    gw = AIGateway(db, user_id)
    out, _ = gw.run_json(
        "interviewer_turn",
        {
            "interviewer_persona": PERSONA.get(interview.mode, "a senior engineer"),
            "mode": interview.mode.replace("_", " "), "role": ctx["role"], "level": ctx["level"],
            "company_clause": f" at {ctx['company']}" if ctx["company"] else "",
            "history": _history(db, session.id), "instruction": instruction, "difficulty": session.difficulty,
            "extra": "", "language": lang,
        },
        InterviewerTurnAI,
        meta={"action": action, "question_seed": seed, "reason": reason, "first": first},
        fallback=lambda: InterviewerTurnAI(message=fallback),
        temperature=0.6, max_tokens=400,
    )
    return out.message.strip() or fallback


# --------------------------------------------------------------------------- public API


def create_interview(db: Session, user: User, *, job_id: int | None, mode: str, language: str) -> Interview:
    if mode not in MODES:
        raise InterviewError(f"Unknown mode {mode}")
    job = db.get(Job, job_id) if job_id else None
    if job is not None and job.user_id != user.id:
        raise InterviewError("Job not found")
    resume = db.scalar(select(Resume).where(Resume.user_id == user.id).order_by(Resume.is_primary.desc(), Resume.id.desc()).limit(1))
    title = f"{mode.replace('_', ' ').title()} — {job.title if job else 'General'}"
    interview = Interview(user_id=user.id, job_id=job.id if job else None, resume_id=resume.id if resume else None,
                          title=title[:200], mode=mode, language=language)
    db.add(interview)
    db.flush()
    return interview


def start_session(db: Session, user: User, interview: Interview, difficulty: int | None = None) -> InterviewSession:
    ctx = _context(db, interview)
    if difficulty is None:
        exp = (ctx["job"].analysis or {}).get("expected_difficulty") if ctx["job"] else None
        difficulty = exp or {"junior": 2, "middle": 3, "senior": 4, "lead": 4}.get(ctx["level"], 3)
    session = InterviewSession(interview_id=interview.id, user_id=user.id, difficulty=difficulty, start_difficulty=difficulty,
                               started_at=datetime.now(UTC), status="in_progress")
    db.add(session)
    db.flush()
    session.plan = _build_plan(db, user.id, interview, ctx)
    session.planned_main = len(session.plan)
    _ask_main(db, user.id, interview, session, ctx, first=True)
    track(db, user.id, "interview_started", session_id=session.id, mode=interview.mode)
    return session


def _main_asked(db: Session, session_id: int) -> int:
    return len(db.scalars(select(InterviewQuestion.id).where(InterviewQuestion.session_id == session_id, InterviewQuestion.kind == "main")).all())


def _next_order(db: Session, session_id: int) -> int:
    return len(db.scalars(select(InterviewQuestion.id).where(InterviewQuestion.session_id == session_id)).all()) + 1


def _ask_main(db: Session, user_id: int, interview: Interview, session: InterviewSession, ctx: dict, first: bool = False) -> InterviewQuestion:
    idx = _main_asked(db, session.id)
    slot = session.plan[idx]
    asked = _recent_topics(db, user_id) if idx == 0 else set(
        db.scalars(select(InterviewQuestion.topic).where(InterviewQuestion.session_id == session.id)).all()
    ) | _recent_topics(db, user_id)
    picked = _pick_bank_question(db, session, slot, ctx, asked)
    text = _interviewer_says(db, user_id, interview, session, ctx, action="ask_main", seed=picked["text"], first=first)
    q = InterviewQuestion(
        session_id=session.id, order=_next_order(db, session.id), kind="main", category=slot["category"],
        topic=picked["topic"], text=text, difficulty=picked["difficulty"], source=picked["source"],
        weakness_id=slot.get("weakness_id"), ideal_points=picked["ideal_points"],
    )
    db.add(q)
    db.flush()
    session.current_question_id = q.id
    return q


def _thread(db: Session, main: InterviewQuestion) -> list[InterviewQuestion]:
    followups = db.scalars(
        select(InterviewQuestion).where(InterviewQuestion.parent_id == main.id).order_by(InterviewQuestion.order)
    ).all()
    return [main, *followups]


def thread_score(evals: list[InterviewEvaluation]) -> float:
    """Main answer 60%, follow-ups 40% — recovering on a follow-up counts, but so does stumbling."""
    if not evals:
        return 0.0
    main, rest = evals[0].score, [e.score for e in evals[1:]]
    return round(0.6 * main + 0.4 * (sum(rest) / len(rest)), 1) if rest else main


def submit_answer(db: Session, user: User, session: InterviewSession, text: str, duration: int | None) -> InterviewSession:
    if session.status != "in_progress":
        raise InterviewError("Interview is not in progress")
    text = (text or "").strip()
    if not text:
        raise InterviewError("Answer is empty")
    q = db.get(InterviewQuestion, session.current_question_id) if session.current_question_id else None
    if q is None:
        raise InterviewError("No active question")
    if db.scalar(select(InterviewAnswer).where(InterviewAnswer.question_id == q.id)):
        raise InterviewError("Question already answered")
    interview = db.get(Interview, session.interview_id)
    ctx = _context(db, interview)

    answer = InterviewAnswer(session_id=session.id, question_id=q.id, text=text[:8000], duration_seconds=duration)
    db.add(answer)
    db.flush()

    main = q if q.kind == "main" else db.get(InterviewQuestion, q.parent_id)
    thread = _thread(db, main)
    answers = {a.question_id: a.text for a in db.scalars(select(InterviewAnswer).where(InterviewAnswer.question_id.in_([t.id for t in thread])))}
    context = "\n".join(f"Q: {t.text}\nA: {answers.get(t.id, '')[:1200]}" for t in thread if t.id != q.id)
    followups_so_far = len(thread) - 1
    res = evaluate_answer(db, user.id, EvalInput(
        role=ctx["role"], level=ctx["level"], category=q.category, topic=q.topic, question=q.text, answer=text,
        ideal_points=q.ideal_points or main.ideal_points or [], difficulty=q.difficulty, language=interview.language,
        context=context, followups_so_far=followups_so_far,
    ))
    d = res.data
    db.add(InterviewEvaluation(
        session_id=session.id, answer_id=answer.id, question_id=q.id, category=q.category, topic=q.topic,
        score=d.score, correctness=d.correctness, depth=d.depth, communication=d.communication,
        technical_accuracy=d.technical_accuracy, severity=d.severity, follow_up_needed=d.follow_up_needed,
        follow_up_reason=d.follow_up_reason, missing_points=d.missing_points, skills_detected=d.skills_detected,
        mistakes=d.mistakes, correct_concept=d.correct_concept, consistency=res.consistency, evaluator=res.evaluator,
    ))
    db.flush()

    if d.follow_up_needed:
        fu_text = _interviewer_says(db, user.id, interview, session, ctx, action="follow_up",
                                    reason=d.follow_up_reason, missing=d.missing_points)
        fu = InterviewQuestion(
            session_id=session.id, order=_next_order(db, session.id), kind="followup", parent_id=main.id,
            category=main.category, topic=main.topic, text=fu_text, difficulty=main.difficulty, source="llm",
            weakness_id=main.weakness_id, ideal_points=d.missing_points or main.ideal_points,
        )
        db.add(fu)
        db.flush()
        session.current_question_id = fu.id
        return session

    # thread finished → adapt difficulty, then continue or close
    evals = db.scalars(
        select(InterviewEvaluation).where(InterviewEvaluation.question_id.in_([t.id for t in thread])).order_by(InterviewEvaluation.id)
    ).all()
    ts = thread_score(list(evals))
    if ts >= 80:
        session.difficulty = min(5, session.difficulty + 1)
    elif ts < 45:
        session.difficulty = max(1, session.difficulty - 1)
    if _main_asked(db, session.id) < session.planned_main:
        _ask_main(db, user.id, interview, session, ctx)
        return session
    return finish(db, user, session)


def finish(db: Session, user: User, session: InterviewSession) -> InterviewSession:
    from app.services.report_service import build_report

    if session.status != "in_progress":
        return session
    answered = db.scalars(select(InterviewAnswer.id).where(InterviewAnswer.session_id == session.id)).all()
    session.finished_at = datetime.now(UTC)
    session.current_question_id = None
    if not answered:
        session.status = "abandoned"
        db.flush()
        return session
    session.status = "completed"
    db.flush()
    build_report(db, user, session)
    return session


def session_state(db: Session, session: InterviewSession) -> dict:
    interview = db.get(Interview, session.interview_id)
    qs = db.scalars(select(InterviewQuestion).where(InterviewQuestion.session_id == session.id).order_by(InterviewQuestion.order)).all()
    answers = {a.question_id: a for a in db.scalars(select(InterviewAnswer).where(InterviewAnswer.session_id == session.id))}
    transcript = []
    for q in qs:
        transcript.append({"role": "interviewer", "text": q.text, "question_id": q.id, "kind": q.kind,
                           "category": q.category, "topic": q.topic})
        if q.id in answers:
            transcript.append({"role": "candidate", "text": answers[q.id].text, "question_id": q.id})
    current = next((q for q in qs if q.id == session.current_question_id), None)
    main_done = len([q for q in qs if q.kind == "main" and (q.id in answers)])
    return {
        "session_id": session.id, "interview_id": interview.id, "title": interview.title, "mode": interview.mode,
        "language": interview.language, "status": session.status, "difficulty": session.difficulty,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "finished_at": session.finished_at.isoformat() if session.finished_at else None,
        "progress": {"main_done": main_done, "planned_main": session.planned_main},
        "stage": current.category if current else None,
        "current_question": ({"id": current.id, "text": current.text, "kind": current.kind, "category": current.category,
                              "topic": current.topic} if current else None),
        "transcript": transcript,
        "overall_score": session.overall_score,
    }
