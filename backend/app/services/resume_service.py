from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Profile, Resume, User
from app.schemas.ai import ResumeAnalysisAI
from app.services import heuristics
from app.services.ai.gateway import AIGateway
from app.services.resume_parser import extract_text, validate_upload
from app.services.storage import get_storage
from app.services.usage import track

SCORE_WEIGHTS = {"ats": 0.2, "technical": 0.25, "impact": 0.2, "clarity": 0.15, "experience": 0.2}
LLM_WEIGHT = 0.6  # consistency: blend LLM scores with deterministic signals


def create_resume(db: Session, user: User, filename: str, content_type: str, data: bytes) -> Resume:
    s = get_settings()
    ext = validate_upload(filename, data, s.max_upload_mb)
    text = extract_text(ext, data)
    key = get_storage().save(data, f"resumes/{user.id}", ext)
    return _persist(db, user, filename, content_type or "application/octet-stream", text, key)


def create_resume_from_text(db: Session, user: User, text: str) -> Resume:
    text = text.strip()[:30000]
    if len(text) < 80:
        raise ValueError("Resume text is too short")
    return _persist(db, user, "pasted.txt", "text/plain", text, None)


def _persist(db: Session, user: User, filename: str, content_type: str, text: str, key: str | None) -> Resume:
    db.execute(update(Resume).where(Resume.user_id == user.id).values(is_primary=False))
    resume = Resume(user_id=user.id, filename=filename[:255], content_type=content_type[:120], storage_key=key,
                    text=text, is_primary=True)
    db.add(resume)
    db.flush()
    track(db, user.id, "cv_uploaded", resume_id=resume.id)
    return resume


def analyze_resume(db: Session, user: User, resume: Resume, language: str) -> Resume:
    heur = heuristics.resume_heuristics(resume.text, language)
    gw = AIGateway(db, user.id)
    ai, status = gw.run_json(
        "analyze_resume",
        {"resume_text": resume.text[:14000], "language": language},
        ResumeAnalysisAI,
        meta={"resume_text": resume.text},
        fallback=lambda: heur,
        max_tokens=2500,
    )
    # Consistency layer: blend scores and union deterministic facts the LLM may have missed.
    blended = {}
    for k in SCORE_WEIGHTS:
        llm_v, h_v = getattr(ai.scores, k), getattr(heur.scores, k)
        blended[k] = round(llm_v if status == "fallback" else LLM_WEIGHT * llm_v + (1 - LLM_WEIGHT) * h_v, 1)
    techs = list(dict.fromkeys([*ai.technologies, *heur.technologies]))
    if not ai.likely_questions:
        ai.likely_questions = heur.likely_questions
    if not ai.years_experience and heur.years_experience:
        ai.years_experience = heur.years_experience
    overall = round(sum(blended[k] * w for k, w in SCORE_WEIGHTS.items()), 1)

    analysis = ai.model_dump()
    analysis.update({"technologies": techs, "scores": blended, "overall": overall, "ai_status": status,
                     "role_family": ai.role_family or heur.role_family})
    resume.analysis = analysis
    resume.overall_score = overall
    resume.status = "analyzed"
    _autofill_profile(db, user, analysis)
    track(db, user.id, "cv_analyzed", resume_id=resume.id, overall=overall, ai_status=status)
    db.flush()
    return resume


def _autofill_profile(db: Session, user: User, analysis: dict) -> None:
    """Frictionless onboarding: AI fills the profile, the user only corrects it."""
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        profile = Profile(user_id=user.id, language=user.locale)
        db.add(profile)
    if not profile.stack:
        profile.stack = analysis.get("technologies", [])[:15]
    if not profile.level:
        sen = analysis.get("seniority")
        profile.level = {"intern": "junior", "lead": "senior"}.get(sen, sen)
    if not profile.role_family and analysis.get("role_family"):
        profile.role_family = analysis["role_family"]
    if not profile.desired_role and analysis.get("headline"):
        profile.desired_role = str(analysis["headline"])[:80]
    if not user.name and analysis.get("candidate_name"):
        user.name = str(analysis["candidate_name"])[:200]


def primary_resume(db: Session, user_id: int) -> Resume | None:
    return db.scalar(
        select(Resume).where(Resume.user_id == user_id).order_by(Resume.is_primary.desc(), Resume.id.desc()).limit(1)
    )
