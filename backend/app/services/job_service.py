import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Job, Profile, Resume, User
from app.schemas.ai import JobAnalysisAI
from app.services import heuristics
from app.services.ai.gateway import AIGateway
from app.services.prediction import build_blueprint
from app.services.skills_catalog import extract_skills, normalize_skill
from app.services.usage import track

LEVELS = ["junior", "middle", "senior", "lead"]


def create_job(db: Session, user: User, *, title: str | None, company_name: str | None, description: str,
               source_url: str | None, interview_date, resume_id: int | None) -> Job:
    company = None
    if company_name:
        company = db.scalar(select(Company).where(Company.name.ilike(company_name.strip())))
    job = Job(
        user_id=user.id, title=(title or "Untitled role")[:200], company_name=company_name, description=description,
        source_url=source_url, interview_date=interview_date, resume_id=resume_id,
        company_id=company.id if company else None,
    )
    db.add(job)
    db.flush()
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is not None:
        profile.active_job_id = job.id
        if interview_date:
            profile.interview_date = interview_date
        if company_name and not profile.target_company:
            profile.target_company = company_name
    track(db, user.id, "job_added", job_id=job.id)
    return job


def analyze_job(db: Session, user: User, job: Job, resume: Resume | None, language: str) -> Job:
    heur = heuristics.job_heuristics(job.description)
    resume_analysis = resume.analysis if resume and resume.analysis else {}
    cand_summary = (
        f"{resume_analysis.get('seniority', 'unknown')} {resume_analysis.get('role_family', '')}, "
        f"skills: {', '.join(resume_analysis.get('technologies', [])[:20])}"
        if resume_analysis else "no CV yet"
    )
    gw = AIGateway(db, user.id)
    ai, status = gw.run_json(
        "analyze_job",
        {"job_text": job.description[:10000], "candidate_summary": cand_summary, "language": language},
        JobAnalysisAI,
        meta={"job_text": job.description},
        fallback=lambda: heur,
    )
    # Consistency: union LLM skills with deterministic extraction so nothing explicit is lost
    ai.must_have = _dedupe([*ai.must_have, *[s for s in heur.must_have if s not in ai.nice_to_have]])
    ai.nice_to_have = [s for s in _dedupe([*ai.nice_to_have, *heur.nice_to_have]) if s not in ai.must_have]
    ai.level = ai.level or heur.level
    ai.role_family = ai.role_family or heur.role_family
    if not ai.likely_stages:
        ai.likely_stages = heur.likely_stages
    analysis = ai.model_dump() | {"ai_status": status}
    job.analysis = analysis
    if not job.level:
        job.level = ai.level
    if job.title in (None, "", "Untitled role") and ai.title:
        job.title = ai.title[:200]
    if not job.company_name and ai.company:
        job.company_name = ai.company[:200]

    if resume is not None:
        job.resume_id = resume.id
        job.match = compute_match(resume_analysis, resume.text, analysis)
        job.match_score = job.match["score"]
    job.blueprint = build_blueprint(
        db, user_id=user.id, family=ai.role_family or resume_analysis.get("role_family"),
        level=job.level or resume_analysis.get("seniority"), job_analysis=analysis, resume_analysis=resume_analysis,
    )
    job.status = "analyzed"
    track(db, user.id, "job_analyzed", job_id=job.id, match=job.match_score, ai_status=status)
    db.flush()
    return job


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for s in items:
        c = normalize_skill(str(s))
        if c.lower() not in seen and c:
            seen.add(c.lower())
            out.append(c)
    return out


def compute_match(resume_analysis: dict, resume_text: str, job_analysis: dict) -> dict:
    """Deterministic, explainable match score. Strong = evidence in CV; weak = thin evidence; missing = absent."""
    cand = {normalize_skill(s).lower() for s in resume_analysis.get("technologies", [])}
    cand |= {s.lower() for s in extract_skills(resume_text)}
    for p in resume_analysis.get("projects", []):
        cand |= {normalize_skill(t).lower() for t in p.get("technologies", [])}
    llm_weak = {normalize_skill(s).lower() for s in job_analysis.get("weak_matches", [])}
    text_low = resume_text.lower()

    def evidence(skill: str) -> int:
        return len(re.findall(re.escape(skill.lower()), text_low))

    must = _dedupe(job_analysis.get("must_have", []))
    nice = _dedupe(job_analysis.get("nice_to_have", []))
    strong, weak, missing = [], [], []
    for s in must:
        if s.lower() not in cand:
            missing.append(s)
        elif evidence(s) >= 2 and s.lower() not in llm_weak:
            strong.append(s)
        else:
            weak.append(s)
    nice_have = [s for s in nice if s.lower() in cand]

    must_cov = (len(strong) + 0.5 * len(weak)) / len(must) if must else 0.6
    nice_cov = len(nice_have) / len(nice) if nice else 0.5
    cand_level = {"intern": 0, "junior": 0, "middle": 1, "senior": 2, "lead": 3}.get(resume_analysis.get("seniority", "junior"), 0)
    job_level = {"junior": 0, "middle": 1, "senior": 2, "lead": 3}.get(job_analysis.get("level") or "", cand_level)
    gap = job_level - cand_level
    level_fit = 1.0 if gap <= 0 else (0.65 if gap == 1 else 0.35)
    score = round(100 * (0.7 * must_cov + 0.15 * nice_cov + 0.15 * level_fit), 1)
    return {
        "score": score,
        "strong": strong,
        "weak": weak,
        "missing": missing,
        "nice_to_have_matched": nice_have,
        "level_gap": gap,
        "expected_difficulty": job_analysis.get("expected_difficulty", 3),
        "likely_stages": job_analysis.get("likely_stages", []),
        "potential_topics": job_analysis.get("interview_topics", [])[:10],
    }
