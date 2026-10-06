"""Error Memory: persistent, per-topic record of mistakes with attempts, progress and spaced retests."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Weakness
from app.services.heuristics import severity_for

RETEST_DAYS = [1, 3, 7, 14, 30]
WEAK_THRESHOLD = 70
RESOLVED_THRESHOLD = 80

EXERCISES = {
    "technical": {
        "en": "Write a 5-sentence explanation of {topic} from memory, then answer 3 practice questions out loud.",
        "ru": "Напишите по памяти объяснение «{topic}» в 5 предложениях, затем ответьте вслух на 3 тренировочных вопроса.",
        "kk": "«{topic}» тақырыбын 5 сөйлеммен жатқа жазып, 3 жаттығу сұрағына дауыстап жауап беріңіз.",
    },
    "coding": {
        "en": "Solve 2 problems on {topic}; state complexity before coding and test edge cases.",
        "ru": "Решите 2 задачи на «{topic}»: до кода назовите сложность, затем проверьте граничные случаи.",
        "kk": "«{topic}» бойынша 2 есеп шығарыңыз: алдымен күрделілігін айтып, шекаралық жағдайларды тексеріңіз.",
    },
    "system_design": {
        "en": "Run a 30-minute self-review of {topic}: requirements, estimates, API, data model, scaling, trade-offs.",
        "ru": "Проведите 30-минутный разбор «{topic}»: требования, оценки, API, модель данных, масштабирование, trade-off'ы.",
        "kk": "«{topic}» бойынша 30 минуттық талдау: талаптар, бағалау, API, деректер моделі, масштабтау, trade-off.",
    },
    "behavioral": {
        "en": "Prepare a STAR story for {topic} with a measurable result; rehearse it in under 2 minutes.",
        "ru": "Подготовьте STAR-историю на тему «{topic}» с измеримым результатом; расскажите её быстрее чем за 2 минуты.",
        "kk": "«{topic}» тақырыбына өлшенетін нәтижесі бар STAR-оқиға дайындап, 2 минутқа жетпей айтып шығыңыз.",
    },
}


def exercise_for(category: str, topic: str, lang: str) -> str:
    key = category if category in EXERCISES else ("behavioral" if category in ("hr", "project_deep_dive", "situational") else "technical")
    table = EXERCISES[key]
    return (table.get(lang) or table["en"]).format(topic=topic)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def record_attempt(
    db: Session, *, user_id: int, topic: str, category: str, score: float, severity: str,
    question: str, answer: str, correct_concept: str, mistakes: list[str], missing_points: list[str],
    language: str, source: str,
) -> Weakness | None:
    now = datetime.now(UTC)
    w = db.scalar(select(Weakness).where(Weakness.user_id == user_id, Weakness.topic == topic))
    is_weak = score < WEAK_THRESHOLD or severity in ("high", "critical")
    if w is None:
        if not is_weak:
            return None
        why = "; ".join([*mistakes, *[f"missing: {m}" for m in missing_points]][:5])
        w = Weakness(
            user_id=user_id, topic=topic, category=category, severity=severity, question_text=question[:4000],
            original_answer=answer[:4000], correct_concept=correct_concept[:4000], why_weak=why[:2000],
            recommended_exercise=exercise_for(category, topic, language), attempts=1, first_score=score,
            current_score=score, best_score=score, status="open",
            history=[{"at": now.isoformat(), "score": score, "source": source}],
            next_retest_at=now + timedelta(days=RETEST_DAYS[0]),
        )
        db.add(w)
        db.flush()
        return w

    w.attempts += 1
    w.current_score = score
    w.best_score = max(w.best_score, score)
    w.history = [*(w.history or []), {"at": now.isoformat(), "score": score, "source": source}][-30:]
    if correct_concept and not w.correct_concept:
        w.correct_concept = correct_concept[:4000]
    if score >= RESOLVED_THRESHOLD and w.attempts >= 2:
        w.status = "resolved"
        w.severity = "low"
        w.next_retest_at = None
    else:
        w.status = "improving" if score >= w.first_score + 10 else "open"
        w.severity = severity_for(score)
        w.next_retest_at = now + timedelta(days=RETEST_DAYS[min(w.attempts - 1, len(RETEST_DAYS) - 1)])
        if is_weak:
            w.original_answer = answer[:4000]
            w.question_text = question[:4000]
    db.flush()
    return w


def due_for_retest(db: Session, user_id: int, limit: int = 2) -> list[Weakness]:
    now = datetime.now(UTC)
    rows = db.scalars(
        select(Weakness).where(Weakness.user_id == user_id, Weakness.status != "resolved").order_by(Weakness.current_score)
    ).all()
    due = [w for w in rows if w.next_retest_at is None or _aware(w.next_retest_at) <= now]
    return due[:limit]


def recurring(db: Session, user_id: int) -> list[Weakness]:
    rows = db.scalars(select(Weakness).where(Weakness.user_id == user_id)).all()
    sev = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(rows, key=lambda w: (w.status == "resolved", sev.get(w.severity, 4), -w.attempts, w.current_score))
