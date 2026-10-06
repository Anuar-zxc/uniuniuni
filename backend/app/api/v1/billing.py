from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import DB, CurrentUser
from app.models import Plan, Subscription
from app.schemas.api import CheckoutIn, PlanOut, SandboxConfirmIn
from app.services.billing import service as billing
from app.services.billing.providers import PROVIDERS, PaymentEvent, PaymentProviderError, get_provider
from app.services.usage import active_subscription, current_plan

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
def plans(db: DB):
    return db.scalars(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort)).all()


@router.get("/providers")
def providers():
    return [{"name": p.name, "currencies": list(p.currencies), "available": p.configured} for p in PROVIDERS.values()]


@router.get("/subscription")
def subscription(user: CurrentUser, db: DB):
    sub = active_subscription(db, user)
    plan = current_plan(db, user)
    return {"plan": PlanOut.model_validate(plan) if plan.id else {"code": "free"},
            "subscription": {"id": sub.id, "status": sub.status, "provider": sub.provider, "currency": sub.currency,
                             "current_period_end": sub.current_period_end} if sub else None}


@router.post("/checkout")
def checkout(body: CheckoutIn, user: CurrentUser, db: DB):
    try:
        out = billing.checkout(db, user, body.plan_code, body.currency, body.provider)
    except PaymentProviderError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    db.commit()
    return out


@router.post("/sandbox/confirm")
def sandbox_confirm(body: SandboxConfirmIn, user: CurrentUser, db: DB):
    if not get_settings().payments_sandbox:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    sub = db.scalar(select(Subscription).where(Subscription.external_id == body.external_id, Subscription.user_id == user.id))
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Checkout not found")
    billing.apply_event(db, "sandbox", PaymentEvent(body.external_id, "succeeded", 0, sub.currency, {"sandbox": True}))
    db.commit()
    return {"ok": True, "plan": sub.plan_code}


@router.post("/cancel")
def cancel(user: CurrentUser, db: DB):
    billing.cancel(db, user)
    db.commit()
    return {"ok": True}


@router.post("/webhooks/{provider_name}")
async def webhook(provider_name: str, request: Request, db: DB):
    if provider_name == "sandbox":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    body = await request.body()
    try:
        provider = get_provider(provider_name)
        event = provider.parse_webhook(body, {k.lower(): v for k, v in request.headers.items()})
    except PaymentProviderError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    if event.status != "ignored":
        billing.apply_event(db, provider.name, event)
        db.commit()
    return {"received": True}
