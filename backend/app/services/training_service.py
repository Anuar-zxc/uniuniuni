"""Personalized training plans built from Error Memory; every task ends with an evaluated check (retest)."""

from datetime import UTC, date, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Profile, Question, TrainingPlan, TrainingTask, User, Weakness
from app.schemas.ai import PracticeQuestion, TrainingQuestionsAI
from app.services import readiness, weakness_service
from app.services.ai.gateway import AIGateway
from app.services.evaluation import EvalInput, evaluate_answer
from app.services.usage import track

SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _bank_questions(db: Session, topic: str, category: str, n: int) -> list[PracticeQuestion]:
    rows = db.scalars(select(Question).where(Question.is_active.is_(True), Question.topic == topic).limit(n)).all()
    if len(rows) < n:
        more = db.scalars(
            select(Question).where(Question.is_active.is_(True), Question.category == category, Question.topic != topic).limit(n - len(rows))
        ).all()
        rows = [*rows, *more]
    return [PracticeQuestion(text=q.text, ideal_points=q.ideal_points) for q in rows]


def _questions_for(db: Session, user: User, w: Weakness | None, topic: str, category: str, level: str, lang: str) -> tuple[str, list[dict]]:
    kind = "case" if category == "system_design" else "questions"
    count = 1 if kind == "case" else (5 if w and w.severity in ("critical", "high") else 3)
    fallback_q = _bank_questions(db, topic, category, count)
    if w and w.question_text and len(fallback_q) < count:
        fallback_q.insert(0, PracticeQuestion(text=w.question_text, ideal_points=[]))
    gap = (w.why_weak or w.correct_concept) if w else "general practice"
    gw = AIGateway(db, user.id)
    out, _ = gw.run_json(
        "training_questions",
        {"topic": topic, "category": category, "level": level, "gap": gap[:800], "count": count, "language": lang},
        TrainingQuestionsAI,
        meta={"fallback_questions": [q.model_dump() for q in fallback_q]},
        fallback=lambda: TrainingQuestionsAI(questions=fallback_q),
    )
    qs = out.questions[:count] or fallback_q
    return kind, [q.model_dump() for q in qs]


def generate_plan(db: Session, user: User, *, job_id: int | None, source_session_id: int | None, language: str) -> TrainingPlan:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    level = (profile.level if profile else None) or "middle"
    db.execute(update(TrainingPlan).where(TrainingPlan.user_id == user.id, TrainingPlan.status == "active").values(status="archived"))

    weaknesses = sorted(
        db.scalars(select(Weakness).where(Weakness.user_id == user.id, Weakness.status != "resolved")).all(),
        key=lambda w: (SEV_RANK.get(w.severity, 4), w.current_score),
    )[:6]
    items: list[tuple[Weakness | None, str, str]] = [(w, w.topic, w.category) for w in weaknesses]
    if len(items) < 3:  # pad with the weakest blueprint categories
        snap = readiness.latest(db, user.id)
        cats = (snap.breakdown.get("categories", {}) if snap else {}) or {}
        weakest = sorted(cats.items(), key=lambda kv: kv[1].get("score", 50))
        used = {c for _, _, c in items}
        for cat, _ in weakest:
            if cat in used:
                continue
            q = db.scalar(select(Question).where(Question.category == cat, Question.is_active.is_(True)).limit(1))
            if q:
                items.append((None, q.topic, cat))
                used.add(cat)
            if len(items) >= 3:
                break
    if not items:
        items = [(None, "Project Deep Dive", "project_deep_dive"), (None, "Conflict", "behavioral")]

    plan = TrainingPlan(user_id=user.id, job_id=job_id, source_session_id=source_session_id,
                        starts_on=date.today(), days=len(items))
    db.add(plan)
    db.flush()
    for day, (w, topic, category) in enumerate(items, start=1):
        kind, questions = _questions_for(db, user, w, topic, category, level, language)
        db.add(TrainingTask(plan_id=plan.id, user_id=user.id, day=day, topic=topic, category=category,
                            weakness_id=w.id if w else None, kind=kind, questions=questions))
    db.flush()
    track(db, user.id, "training_plan_generated", plan_id=plan.id, days=len(items))
    return plan


def answer_task(db: Session, user: User, task: TrainingTask, index: int, text: str, language: str) -> TrainingTask:
    if index < 0 or index >= len(task.questions):
        raise ValueError("Invalid question index")
    q = task.questions[index]
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    res = evaluate_answer(db, user.id, EvalInput(
        role=(profile.desired_role if profile else None) or "Software Engineer",
        level=(profile.level if profile else None) or "middle", category=task.category, topic=task.topic,
        question=q["text"], answer=text, ideal_points=q.get("ideal_points", []), difficulty=3, language=language,
        followups_so_far=2,  # practice mode: no follow-ups
    ))
    answers = [a for a in (task.answers or []) if a["index"] != index]
    answers.append({
        "index": index, "text": text[:6000], "score": res.data.score, "feedback": res.data.feedback,
        "missing_points": res.data.missing_points, "correct_concept": res.data.correct_concept,
    })
    task.answers = sorted(answers, key=lambda a: a["index"])
    task.status = "in_progress"
    if len(task.answers) >= len(task.questions):
        task.status = "completed"
        task.completed_at = datetime.now(UTC)
        task.score = round(sum(a["score"] for a in task.answers) / len(task.answers), 1)
        worst = min(task.answers, key=lambda a: a["score"])
        weakness_service.record_attempt(
            db, user_id=user.id, topic=task.topic, category=task.category, score=task.score,
            severity="low" if task.score >= 75 else "medium" if task.score >= 55 else "high",
            question=task.questions[worst["index"]]["text"], answer=worst["text"],
            correct_concept=worst.get("correct_concept", ""), mistakes=[], missing_points=worst.get("missing_points", []),
            language=language, source="training",
        )
        readiness.recompute(db, user.id, trigger="training")
        track(db, user.id, "training_task_completed", task_id=task.id, score=task.score)
        plan = db.get(TrainingPlan, task.plan_id)
        if plan and all(t.status == "completed" for t in db.scalars(select(TrainingTask).where(TrainingTask.plan_id == plan.id))):
            plan.status = "completed"
    db.flush()
    return task
