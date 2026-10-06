"""Smoke-check the configured LLM provider: `cd backend && python -m scripts.check_llm`."""

from app.core.config import get_settings
from app.schemas.ai import AnswerEvaluationAI
from app.services.ai.gateway import AIGateway

s = get_settings()
print(f"provider={s.ai_provider} model={s.ai_model}")
gw = AIGateway(db=None)
print("chat:", gw.run_text("chat", {"message": "Say hi in one short sentence.", "language": "ru"})[:200])
ev, status = gw.run_json(
    "evaluate_answer",
    {"role": "Backend Engineer", "level": "middle", "category": "technical", "topic": "Database Indexing",
     "question": "How do database indexes work?", "answer": "They use B-trees so lookups are logarithmic, but writes get slower.",
     "ideal_points": "B-tree; faster reads; slower writes; EXPLAIN", "difficulty": 3, "context": "(none)", "language": "ru"},
    AnswerEvaluationAI,
)
print(f"evaluate_answer status={status} score={ev.score} severity={ev.severity} follow_up={ev.follow_up_needed}")
