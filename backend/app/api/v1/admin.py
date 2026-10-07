from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, update

from app.core.deps import DB, AdminUser, client_ip
from app.models import (
    AIRequest,
    AuditLog,
    Company,
    Event,
    InterviewSession,
    Payment,
    Plan,
    Prompt,
    Question,
    ReadinessSnapshot,
    RoleCatalog,
    Skill,
    Subscription,
    User,
    Weakness,
)
from app.repositories.base import get_or_404
from app.services.ai.prompts import DEFAULT_PROMPTS

router = APIRouter(prefix="/admin", tags=["admin"])


def _audit(db, admin: User, request: Request, action: str, entity: str, entity_id, meta: dict | None = None):
    db.add(AuditLog(actor_id=admin.id, action=action, entity=entity, entity_id=str(entity_id), meta=meta or {}, ip=client_ip(request)))


def _row(obj, cols: list[str]) -> dict:
    return {c: getattr(obj, c) for c in cols}


# ---------------------------------------------------------------- overview & analytics


@router.get("/overview")
def overview(admin: AdminUser, db: DB):
    since = datetime.now(UTC) - timedelta(days=30)
    users = db.scalar(select(func.count(User.id))) or 0

    def users_with(event: str) -> int:
        return db.scalar(select(func.count(func.distinct(Event.user_id))).where(Event.name == event)) or 0

    signed, cv, job, first_iv = users_with("signed_up"), users_with("cv_uploaded"), users_with("job_added"), users_with("interview_completed")
    paid = db.scalar(select(func.count(func.distinct(Subscription.user_id))).where(Subscription.status == "active",
                                                                                   Subscription.plan_code != "free")) or 0
    ai_cost = db.scalar(select(func.coalesce(func.sum(AIRequest.cost_usd), 0)).where(AIRequest.created_at >= since)) or 0
    completed = db.scalar(select(func.count(InterviewSession.id)).where(InterviewSession.status == "completed")) or 0
    revenue = db.execute(select(Payment.currency, func.sum(Payment.amount)).where(Payment.status == "succeeded").group_by(Payment.currency)).all()

    # North Star: share of users with ≥2 readiness snapshots whose readiness rose by ≥15 points
    first_last = db.execute(
        select(ReadinessSnapshot.user_id, func.min(ReadinessSnapshot.score), func.max(ReadinessSnapshot.score), func.count(ReadinessSnapshot.id))
        .group_by(ReadinessSnapshot.user_id)
    ).all()
    improved = sum(1 for _, lo, hi, n in first_last if n >= 2 and hi - lo >= 15)
    resolved = db.scalar(select(func.count(Weakness.id)).where(Weakness.status == "resolved")) or 0
    total_w = db.scalar(select(func.count(Weakness.id))) or 0
    return {
        "users": users,
        "funnel": {"signed_up": signed, "cv_uploaded": cv, "job_added": job, "first_interview_completed": first_iv, "paid": paid},
        "activation_rate": round(first_iv / signed, 3) if signed else 0,
        "conversion_free_to_paid": round(paid / signed, 3) if signed else 0,
        "interviews_completed": completed,
        "interviews_per_user": round(completed / users, 2) if users else 0,
        "north_star_readiness_improved_share": round(improved / users, 3) if users else 0,
        "weakness_resolution_rate": round(resolved / total_w, 3) if total_w else 0,
        "ai_cost_usd_30d": round(float(ai_cost), 4),
        "cost_per_interview_usd": round(float(ai_cost) / completed, 4) if completed else 0,
        "revenue": {cur: float(total) for cur, total in revenue},
    }


@router.get("/ai/usage")
def ai_usage(admin: AdminUser, db: DB, days: int = 30):
    since = datetime.now(UTC) - timedelta(days=days)
    rows = db.execute(
        select(AIRequest.task, AIRequest.provider, AIRequest.model, func.count(AIRequest.id), func.sum(AIRequest.input_tokens),
               func.sum(AIRequest.output_tokens), func.sum(AIRequest.cost_usd), func.avg(AIRequest.latency_ms))
        .where(AIRequest.created_at >= since).group_by(AIRequest.task, AIRequest.provider, AIRequest.model)
    ).all()
    status_rows = db.execute(select(AIRequest.status, func.count(AIRequest.id)).where(AIRequest.created_at >= since).group_by(AIRequest.status)).all()
    return {
        "by_task": [{"task": t, "provider": p, "model": m, "requests": n, "input_tokens": int(i or 0), "output_tokens": int(o or 0),
                     "cost_usd": round(float(c or 0), 4), "avg_latency_ms": int(lat or 0)} for t, p, m, n, i, o, c, lat in rows],
        "by_status": dict(status_rows),
    }


@router.get("/ai/failures")
def ai_failures(admin: AdminUser, db: DB, include_reviewed: bool = False):
    stmt = select(AIRequest).where(AIRequest.status.in_(["error", "invalid", "fallback"]))
    if not include_reviewed:
        stmt = stmt.where(AIRequest.reviewed.is_(False))
    rows = db.scalars(stmt.order_by(AIRequest.id.desc()).limit(200)).all()
    return [_row(r, ["id", "task", "provider", "model", "status", "error", "response_excerpt", "prompt_key", "prompt_version", "created_at"]) for r in rows]


@router.post("/ai/failures/{req_id}/review")
def review_failure(req_id: int, admin: AdminUser, db: DB):
    get_or_404(db, AIRequest, req_id).reviewed = True
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- users & subscriptions


@router.get("/users")
def users(admin: AdminUser, db: DB, q: str | None = None, limit: int = 100):
    stmt = select(User)
    if q:
        stmt = stmt.where(or_(User.email.ilike(f"%{q}%"), User.name.ilike(f"%{q}%")))
    rows = db.scalars(stmt.order_by(User.id.desc()).limit(min(limit, 500))).all()
    return [_row(u, ["id", "email", "name", "role", "is_active", "locale", "organization_id", "created_at"]) for u in rows]


class UserPatch(BaseModel):
    role: str | None = Field(default=None, pattern="^(user|admin)$")
    is_active: bool | None = None
    organization_id: int | None = None


@router.patch("/users/{user_id}")
def patch_user(user_id: int, body: UserPatch, admin: AdminUser, db: DB, request: Request):
    u = get_or_404(db, User, user_id)
    if u.id == admin.id and body.role == "user":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot demote yourself")
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(u, k, v)
    _audit(db, admin, request, "admin.user_update", "user", u.id, changes)
    db.commit()
    return {"ok": True}


@router.get("/subscriptions")
def subscriptions(admin: AdminUser, db: DB):
    rows = db.scalars(select(Subscription).order_by(Subscription.id.desc()).limit(300)).all()
    return [_row(s, ["id", "user_id", "organization_id", "plan_code", "status", "provider", "currency", "current_period_end", "created_at"]) for s in rows]


class SubscriptionPatch(BaseModel):
    status: str = Field(pattern="^(pending|active|past_due|canceled)$")
    plan_code: str | None = None


@router.patch("/subscriptions/{sub_id}")
def patch_subscription(sub_id: int, body: SubscriptionPatch, admin: AdminUser, db: DB, request: Request):
    s = get_or_404(db, Subscription, sub_id)
    s.status = body.status
    if body.plan_code:
        s.plan_code = body.plan_code
    _audit(db, admin, request, "admin.subscription_update", "subscription", s.id, body.model_dump())
    db.commit()
    return {"ok": True}


@router.get("/payments")
def payments(admin: AdminUser, db: DB):
    rows = db.scalars(select(Payment).order_by(Payment.id.desc()).limit(300)).all()
    return [_row(p, ["id", "user_id", "provider", "external_id", "amount", "currency", "status", "created_at"]) for p in rows]


# ---------------------------------------------------------------- plans


class PlanIn(BaseModel):
    code: str = Field(max_length=30)
    name: str = Field(max_length=80)
    prices: dict[str, float]
    limits: dict[str, int]
    features: list[str] = []
    is_active: bool = True
    sort: int = 0


@router.get("/plans")
def list_plans(admin: AdminUser, db: DB):
    return [_row(p, ["id", "code", "name", "prices", "limits", "features", "is_active", "sort"]) for p in db.scalars(select(Plan).order_by(Plan.sort))]


@router.put("/plans")
def upsert_plan(body: PlanIn, admin: AdminUser, db: DB, request: Request):
    p = db.scalar(select(Plan).where(Plan.code == body.code)) or Plan(code=body.code)
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    db.add(p)
    _audit(db, admin, request, "admin.plan_upsert", "plan", body.code, body.model_dump())
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- prompts (versioned)


@router.get("/prompts")
def prompts(admin: AdminUser, db: DB):
    rows = db.scalars(select(Prompt).order_by(Prompt.key, Prompt.version.desc())).all()
    return {"keys": list(DEFAULT_PROMPTS), "versions": [_row(p, ["id", "key", "version", "is_active", "system", "user_template", "notes", "created_at"]) for p in rows]}


class PromptIn(BaseModel):
    key: str
    system: str = Field(min_length=10)
    user_template: str = Field(min_length=3)
    notes: str | None = None
    activate: bool = False


@router.post("/prompts")
def create_prompt_version(body: PromptIn, admin: AdminUser, db: DB, request: Request):
    if body.key not in DEFAULT_PROMPTS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown prompt key")
    latest = db.scalar(select(func.max(Prompt.version)).where(Prompt.key == body.key)) or 0
    p = Prompt(key=body.key, version=latest + 1, system=body.system, user_template=body.user_template, notes=body.notes, is_active=False)
    db.add(p)
    db.flush()
    if body.activate:
        _activate(db, p)
    _audit(db, admin, request, "admin.prompt_version", "prompt", f"{p.key}@{p.version}")
    db.commit()
    return {"id": p.id, "version": p.version}


def _activate(db, p: Prompt) -> None:
    db.execute(update(Prompt).where(Prompt.key == p.key).values(is_active=False))
    p.is_active = True


@router.post("/prompts/{prompt_id}/activate")
def activate_prompt(prompt_id: int, admin: AdminUser, db: DB, request: Request):
    p = get_or_404(db, Prompt, prompt_id)
    _activate(db, p)
    _audit(db, admin, request, "admin.prompt_activate", "prompt", f"{p.key}@{p.version}")
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- content: questions, companies, roles, skills


class QuestionIn(BaseModel):
    category: str
    topic: str = Field(max_length=120)
    role_family: str = "any"
    difficulty: int = Field(default=3, ge=1, le=5)
    text: str = Field(min_length=10)
    ideal_points: list[str] = []
    language: str = "en"
    is_active: bool = True


@router.get("/questions")
def list_questions(admin: AdminUser, db: DB, category: str | None = None, q: str | None = None):
    stmt = select(Question)
    if category:
        stmt = stmt.where(Question.category == category)
    if q:
        stmt = stmt.where(or_(Question.topic.ilike(f"%{q}%"), Question.text.ilike(f"%{q}%")))
    cols = ["id", "category", "topic", "role_family", "difficulty", "text", "ideal_points", "language", "is_active"]
    return [_row(x, cols) for x in db.scalars(stmt.order_by(Question.category, Question.topic).limit(500))]


@router.post("/questions")
def create_question(body: QuestionIn, admin: AdminUser, db: DB, request: Request):
    qn = Question(**body.model_dump())
    db.add(qn)
    db.flush()
    _audit(db, admin, request, "admin.question_create", "question", qn.id)
    db.commit()
    return {"id": qn.id}


@router.put("/questions/{qid}")
def update_question(qid: int, body: QuestionIn, admin: AdminUser, db: DB, request: Request):
    qn = get_or_404(db, Question, qid)
    for k, v in body.model_dump().items():
        setattr(qn, k, v)
    _audit(db, admin, request, "admin.question_update", "question", qid)
    db.commit()
    return {"ok": True}


class CompanyIn(BaseModel):
    name: str = Field(max_length=200)
    country: str | None = Field(default=None, max_length=2)
    website: str | None = None
    industry: str | None = None
    public_interview_notes: str | None = None
    source_url: str | None = Field(default=None, description="Required when interview notes are provided")


@router.get("/companies")
def companies(admin: AdminUser, db: DB):
    cols = ["id", "name", "country", "website", "industry", "public_interview_notes", "source_url"]
    return [_row(c, cols) for c in db.scalars(select(Company).order_by(Company.name))]


@router.post("/companies")
def upsert_company(body: CompanyIn, admin: AdminUser, db: DB, request: Request):
    if body.public_interview_notes and not body.source_url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Interview notes must cite a public source_url")
    c = db.scalar(select(Company).where(Company.name == body.name)) or Company(name=body.name)
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    db.add(c)
    _audit(db, admin, request, "admin.company_upsert", "company", body.name)
    db.commit()
    return {"ok": True}


@router.get("/roles")
def roles(admin: AdminUser, db: DB):
    return [_row(r, ["id", "slug", "name", "family", "blueprint"]) for r in db.scalars(select(RoleCatalog).order_by(RoleCatalog.name))]


class RolePatch(BaseModel):
    name: str | None = None
    blueprint: dict | None = None


@router.patch("/roles/{role_id}")
def patch_role(role_id: int, body: RolePatch, admin: AdminUser, db: DB, request: Request):
    r = get_or_404(db, RoleCatalog, role_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    _audit(db, admin, request, "admin.role_update", "role", role_id)
    db.commit()
    return {"ok": True}


@router.get("/skills")
def skills(admin: AdminUser, db: DB):
    return [_row(s, ["id", "slug", "name", "category", "aliases"]) for s in db.scalars(select(Skill).order_by(Skill.name))]


class SkillIn(BaseModel):
    slug: str
    name: str
    category: str
    aliases: list[str] = []


@router.post("/skills")
def create_skill(body: SkillIn, admin: AdminUser, db: DB, request: Request):
    if db.scalar(select(Skill).where(Skill.slug == body.slug)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Skill exists")
    db.add(Skill(**body.model_dump()))
    _audit(db, admin, request, "admin.skill_create", "skill", body.slug)
    db.commit()
    return {"ok": True}


@router.get("/audit")
def audit(admin: AdminUser, db: DB, limit: int = 200):
    cols = ["id", "actor_id", "action", "entity", "entity_id", "meta", "ip", "created_at"]
    return [_row(a, cols) for a in db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 1000)))]
