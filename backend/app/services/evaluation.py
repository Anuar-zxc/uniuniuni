"""Evaluation Engine + consistency layer.

An answer score is never a single raw LLM number:
  1. LLM structured evaluation (strict schema, optional multi-sample median),
  2. deterministic heuristic evaluation as an independent signal,
  3. guardrails (non-answers capped, divergence blended, composite cross-check, severity derived from score).
Every adjustment is recorded in `consistency` for auditability.
"""

from dataclasses import dataclass
from statistics import median

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.ai import AnswerEvaluationAI
from app.services import heuristics
from app.services.ai.gateway import AIGateway

SEV_ORDER = ["low", "medium", "high", "critical"]
FIELDS = ["score", "correctness", "depth", "communication", "technical_accuracy"]


@dataclass
class EvalInput:
    role: str
    level: str
    category: str
    topic: str
    question: str
    answer: str
    ideal_points: list[str]
    difficulty: int
    language: str
    context: str = ""
    followups_so_far: int = 0


@dataclass
class EvalResult:
    data: AnswerEvaluationAI
    consistency: dict
    evaluator: str


def evaluate_answer(db: Session, user_id: int | None, inp: EvalInput) -> EvalResult:
    s = get_settings()
    heur = heuristics.evaluate_heuristic(
        question=inp.question, answer=inp.answer, ideal_points=inp.ideal_points,
        category=inp.category, followups_so_far=inp.followups_so_far,
    )
    gw = AIGateway(db, user_id)
    variables = {
        "role": inp.role, "level": inp.level, "category": inp.category, "topic": inp.topic,
        "question": inp.question, "answer": inp.answer[:6000], "ideal_points": "; ".join(inp.ideal_points) or "n/a",
        "difficulty": inp.difficulty, "context": inp.context or "(none)", "language": inp.language,
    }
    meta = {"question": inp.question, "answer": inp.answer, "ideal_points": inp.ideal_points,
            "category": inp.category, "followups_so_far": inp.followups_so_far}
    samples: list[AnswerEvaluationAI] = []
    statuses: list[str] = []
    for i in range(max(1, s.ai_eval_samples)):
        out, status = gw.run_json(
            "evaluate_answer", variables, AnswerEvaluationAI, meta=meta, fallback=lambda: heur,
            temperature=0.0 if i == 0 else 0.4, model=s.ai_eval_model or None,
        )
        samples.append(out)
        statuses.append(status)
        if status == "fallback":
            break
    llm_ok = [x for x, st in zip(samples, statuses, strict=True) if st != "fallback"]
    if not llm_ok:
        return EvalResult(heur, {"flags": ["llm_unavailable_heuristic_used"], "heuristic_score": heur.score}, "heuristic")
    return EvalResult(*reconcile(llm_ok, heur, inp), "llm")


def reconcile(samples: list[AnswerEvaluationAI], heur: AnswerEvaluationAI, inp: EvalInput) -> tuple[AnswerEvaluationAI, dict]:
    flags: list[str] = []
    base = samples[0].model_copy(deep=True)
    if len(samples) > 1:
        for f in FIELDS:
            setattr(base, f, median(getattr(x, f) for x in samples))
        spread = max(x.score for x in samples) - min(x.score for x in samples)
        if spread > 20:
            flags.append(f"sample_spread_{round(spread)}")
        base.follow_up_needed = sum(x.follow_up_needed for x in samples) * 2 >= len(samples)

    llm_score = base.score
    # 1) Non-answers can never score well, whatever the LLM says.
    if heur.score <= 10 and base.score > 25:
        base.score = min(base.score, 25)
        base.correctness = min(base.correctness, 25)
        flags.append("non_answer_capped")
    # 2) Composite cross-check: overall must agree with its own sub-scores.
    composite = 0.35 * base.correctness + 0.25 * base.depth + 0.15 * base.communication + 0.25 * base.technical_accuracy
    if abs(base.score - composite) > 15:
        base.score = round((base.score + composite) / 2, 1)
        flags.append("rebalanced_with_subscores")
    # 3) Strong divergence from the independent heuristic: pull slightly towards it.
    if abs(base.score - heur.score) > 40:
        base.score = round(0.8 * base.score + 0.2 * heur.score, 1)
        flags.append("divergent_from_heuristic")
    # 4) Severity must be consistent with the final score (allow 1 level of LLM judgement).
    derived = heuristics.severity_for(base.score)
    if abs(SEV_ORDER.index(base.severity) - SEV_ORDER.index(derived)) > 1:
        base.severity = derived
        flags.append("severity_rederived")
    # 5) Follow-up policy: strong answers move on; weak non-empty answers get probed (bounded).
    max_fu = 4 if inp.category == "system_design" else 2
    if inp.followups_so_far >= max_fu:
        base.follow_up_needed = False
    elif base.score >= 85:
        base.follow_up_needed = False
    elif base.score < 70 and heur.score > 10 and not base.follow_up_needed:
        base.follow_up_needed = True
        base.follow_up_reason = heur.follow_up_reason if heur.follow_up_reason != "none" else "shallow"
        flags.append("follow_up_forced")
    if base.follow_up_needed and base.follow_up_reason == "none":
        base.follow_up_reason = "probe"
    if not base.missing_points and heur.missing_points and base.score < 70:
        base.missing_points = heur.missing_points
    base.score = round(max(0.0, min(100.0, base.score)), 1)
    return base, {"flags": flags, "llm_score": llm_score, "heuristic_score": heur.score, "samples": len(samples)}
