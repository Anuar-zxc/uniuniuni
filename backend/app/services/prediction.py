"""Interview Prediction Engine: which categories/topics are likely, with weights (the Interview Blueprint)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Question, Weakness
from app.services.seed_data import BLUEPRINTS, FAMILY_ALIASES
from app.services.skills_catalog import normalize_skill

SKILL_TOPICS: dict[str, list[str]] = {
    "JavaScript": ["JavaScript Event Loop", "JavaScript Closures"],
    "TypeScript": ["TypeScript Types"],
    "React": ["React Rendering", "React Hooks", "Frontend Architecture"],
    "Next.js": ["Next.js Rendering"],
    "CSS": ["CSS Layout"],
    "HTML": ["Browser Rendering"],
    "Browser Internals": ["Browser Rendering"],
    "Web Performance": ["Web Performance"],
    "PostgreSQL": ["Database Indexing", "SQL Transactions"],
    "MySQL": ["Database Indexing", "SQL Transactions"],
    "SQL": ["Database Indexing", "SQL Transactions", "SQL Analytics"],
    "Redis": ["Caching"],
    "Caching": ["Caching"],
    "REST API": ["REST API Design", "Authentication"],
    "Concurrency": ["Concurrency"],
    "Go": ["Concurrency"],
    "Java": ["Concurrency"],
    "Python": ["Python Internals"],
    "Kafka": ["Message Queues"],
    "RabbitMQ": ["Message Queues"],
    "Message Queues": ["Message Queues"],
    "System Design": ["URL Shortener", "Rate Limiter", "Chat System"],
    "Microservices": ["Message Queues", "Food Delivery System"],
    "Docker": ["Docker"],
    "Kubernetes": ["Kubernetes"],
    "CI/CD": ["CI/CD"],
    "Networking": ["Networking"],
    "Linux": ["Incident Response"],
    "Monitoring": ["Incident Response", "Production Debugging"],
    "Machine Learning": ["Bias-Variance", "Model Evaluation", "Gradient Descent"],
    "Deep Learning": ["Gradient Descent", "Transformers"],
    "NLP": ["Transformers"],
    "Statistics": ["A/B Testing", "Model Evaluation"],
    "Testing": ["Test Strategy"],
    "Product Management": ["Product Prioritization"],
}


def family_key(family: str | None) -> str:
    f = (family or "generic").lower()
    return f if f in BLUEPRINTS else FAMILY_ALIASES.get(f, "generic")


def level_key(level: str | None) -> str:
    lv = (level or "middle").lower()
    return {"intern": "junior", "lead": "senior"}.get(lv, lv if lv in ("junior", "middle", "senior") else "middle")


def base_weights(family: str | None, level: str | None) -> dict[str, float]:
    return dict(BLUEPRINTS[family_key(family)][level_key(level)])


def build_blueprint(
    db: Session, *, user_id: int, family: str | None, level: str | None, job_analysis: dict, resume_analysis: dict
) -> dict:
    weights = base_weights(family, level)
    must = [normalize_skill(s) for s in job_analysis.get("must_have", [])]
    text = " ".join(job_analysis.get("responsibilities", []) + job_analysis.get("interview_topics", [])).lower()
    # JD signals shift weight between categories
    if "System Design" in must or any(w in text for w in ("architecture", "архитектур", "high load", "highload", "scal")):
        weights["system_design"] = weights.get("system_design", 0) + 0.08
    if any(w in text for w in ("algorithm", "алгоритм", "leetcode", "data structures", "структуры данных")):
        weights["coding"] = weights.get("coding", 0) + 0.08
    if any(w in text for w in ("mentor", "lead", "ментор", "stakeholder", "заказчик")):
        weights["behavioral"] = weights.get("behavioral", 0) + 0.05
    # Open weaknesses raise the probability of their categories being probed again
    for w in db.scalars(select(Weakness).where(Weakness.user_id == user_id, Weakness.status != "resolved")).all():
        weights[w.category] = weights.get(w.category, 0) + (0.03 if w.severity in ("high", "critical") else 0.01)
    total = sum(weights.values()) or 1
    weights = {k: round(v / total, 3) for k, v in sorted(weights.items(), key=lambda kv: -kv[1])}

    bank_topics = {q.topic: q.category for q in db.scalars(select(Question).where(Question.is_active.is_(True))).all()}
    topics: dict[str, dict] = {}

    def add(topic: str, category: str, prob: float, source: str) -> None:
        cur = topics.get(topic)
        if cur is None or cur["probability"] < prob:
            topics[topic] = {"topic": topic, "category": category, "probability": round(min(prob, 0.97), 2), "source": source}

    for i, skill in enumerate(must):
        for t in SKILL_TOPICS.get(skill, []):
            if t in bank_topics:
                add(t, bank_topics[t], 0.85 - i * 0.03, "job")
    for skill in resume_analysis.get("technologies", [])[:10]:
        for t in SKILL_TOPICS.get(normalize_skill(skill), []):
            if t in bank_topics:
                add(t, bank_topics[t], 0.55, "cv")
    for t in job_analysis.get("interview_topics", [])[:8]:
        add(str(t)[:120], "technical", 0.7, "job")
    if resume_analysis.get("likely_questions"):
        add("Project Deep Dive", "project_deep_dive", 0.9, "cv")
    for cat in ("behavioral", "hr"):
        if cat in weights:
            for t, c in bank_topics.items():
                if c == cat:
                    add(t, c, 0.4, "common")
    ordered = sorted(topics.values(), key=lambda x: -x["probability"])[:20]
    return {"family": family_key(family), "level": level_key(level), "weights": weights, "topics": ordered}
