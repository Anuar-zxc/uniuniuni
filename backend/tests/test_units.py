from app.schemas.ai import AnswerEvaluationAI
from app.services import heuristics
from app.services.ai.json_utils import extract_json
from app.services.evaluation import EvalInput, reconcile
from app.services.interview_engine import _allocate, thread_score
from app.services.job_service import compute_match
from app.services.readiness import status_for
from app.services.skills_catalog import extract_skills

INP = EvalInput(role="Backend", level="middle", category="technical", topic="Caching", question="q", answer="a",
                ideal_points=["cache-aside"], difficulty=3, language="en")


def _ev(**kw):
    base = {"score": 70, "correctness": 70, "depth": 70, "communication": 70, "technical_accuracy": 70}
    return AnswerEvaluationAI(**(base | kw))


def test_extract_json_handles_reasoning_and_fences():
    assert extract_json('<think>x</think>```json\n{"a": 1,}\n```') == {"a": 1}
    assert extract_json('noise {"m": "{x}"} tail') == {"m": "{x}"}


def test_skills_go_is_case_sensitive():
    assert "Go" in extract_skills("Backend in Go and Python")
    assert "Go" not in extract_skills("we go to production weekly")


def test_non_answer_is_capped_even_if_llm_is_generous():
    heur = heuristics.evaluate_heuristic(question="q", answer="не знаю", ideal_points=["x"], category="technical")
    out, meta = reconcile([_ev(score=80, correctness=80)], heur, INP)
    assert out.score <= 25 and "non_answer_capped" in meta["flags"]


def test_score_rebalanced_against_subscores():
    heur = _ev(score=60)
    out, meta = reconcile([_ev(score=95, correctness=40, depth=40, communication=40, technical_accuracy=40)], heur, INP)
    assert out.score < 80 and "rebalanced_with_subscores" in meta["flags"]


def test_severity_rederived_and_followups_bounded():
    heur = _ev(score=50)
    out, _ = reconcile([_ev(score=30, correctness=30, depth=30, communication=30, technical_accuracy=30, severity="low")], heur, INP)
    assert out.severity in ("high", "critical")
    inp = EvalInput(**(INP.__dict__ | {"followups_so_far": 2}))
    out, _ = reconcile([_ev(score=40, correctness=40, depth=40, communication=40, technical_accuracy=40, follow_up_needed=True)], heur, inp)
    assert out.follow_up_needed is False


def test_median_of_samples():
    heur = _ev(score=70)
    out, meta = reconcile([_ev(score=60), _ev(score=70), _ev(score=90)], heur, INP)
    assert meta["samples"] == 3


def test_allocation_arc():
    slots = _allocate({"technical": 0.5, "behavioral": 0.2, "hr": 0.1, "coding": 0.2}, 7)
    assert len(slots) == 7 and slots[0] == "hr" and slots[-1] == "behavioral"


def test_thread_score_weights_followups():
    class E:
        def __init__(self, s):
            self.score = s
    assert thread_score([E(40), E(80)]) == 56.0
    assert thread_score([E(70)]) == 70


def test_match_is_explainable():
    m = compute_match({"technologies": ["React", "TypeScript"], "seniority": "junior"},
                      "React React TypeScript", {"must_have": ["React", "TypeScript", "Kubernetes"], "level": "middle"})
    assert m["missing"] == ["Kubernetes"] and "React" in m["strong"] and m["level_gap"] == 1


def test_status_bands():
    assert [status_for(x) for x in (85, 70, 50, 20)] == ["READY", "ALMOST_READY", "NEEDS_WORK", "NOT_READY"]


def test_settings_on_vercel(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_PROJECT_PRODUCTION_URL", "offerready.vercel.app")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_URL", "postgres://u:p@host.neon.tech/db?sslmode=require")
    s = Settings(_env_file=None)
    assert s.database_url == "postgresql+psycopg://u:p@host.neon.tech/db?sslmode=require"
    assert s.cookie_secure is True and s.storage_backend == "none"
    assert s.frontend_url == "https://offerready.vercel.app"
    assert s.payments_sandbox is True


def test_settings_production_disables_sandbox(monkeypatch):
    from app.core.config import Settings

    monkeypatch.delenv("VERCEL", raising=False)
    s = Settings(_env_file=None, environment="production", jwt_secret="x" * 40)
    assert s.payments_sandbox is False and s.cookie_secure is True
