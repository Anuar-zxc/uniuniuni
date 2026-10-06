"""Plan limits, usage metering and analytics events."""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event, Plan, Subscription, Usage, User


def current_period() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def active_subscription(db: Session, user: User) -> Subscription | None:
    stmt = select(Subscription).where(Subscription.status == "active")
    if user.organization_id:
        stmt = stmt.where((Subscription.user_id == user.id) | (Subscription.organization_id == user.organization_id))
    else:
        stmt = stmt.where(Subscription.user_id == user.id)
    subs = db.scalars(stmt.order_by(Subscription.id.desc())).all()
    now = datetime.now(UTC)
    for sub in subs:
        end = sub.current_period_end
        if end is None or (end.replace(tzinfo=UTC) if end.tzinfo is None else end) > now:
            return sub
    return None


def current_plan(db: Session, user: User) -> Plan:
    sub = active_subscription(db, user)
    code = sub.plan_code if sub else "free"
    plan = db.scalar(select(Plan).where(Plan.code == code))
    if plan is None:
        plan = db.scalar(select(Plan).where(Plan.code == "free"))
    if plan is None:  # unseeded DB: permissive defaults
        plan = Plan(code="free", name="Free", prices={}, limits={}, features=[])
    return plan


def get_usage(db: Session, user_id: int, metric: str) -> int:
    row = db.scalar(select(Usage).where(Usage.user_id == user_id, Usage.period == current_period(), Usage.metric == metric))
    return row.count if row else 0


def check_quota(db: Session, user: User, metric: str) -> None:
    if user.role == "admin":
        return
    limit = current_plan(db, user).limits.get(metric, -1)
    if limit != -1 and get_usage(db, user.id, metric) >= limit:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "quota_exceeded", "metric": metric, "limit": limit, "message": "Upgrade your plan to continue"},
        )


def increment(db: Session, user_id: int, metric: str, amount: int = 1) -> None:
    row = db.scalar(select(Usage).where(Usage.user_id == user_id, Usage.period == current_period(), Usage.metric == metric))
    if row is None:
        row = Usage(user_id=user_id, period=current_period(), metric=metric, count=0)
        db.add(row)
    row.count += amount
    db.flush()


def track(db: Session, user_id: int | None, name: str, **props) -> None:
    db.add(Event(user_id=user_id, name=name, props=props, occurred_at=datetime.now(UTC)))
    db.flush()
