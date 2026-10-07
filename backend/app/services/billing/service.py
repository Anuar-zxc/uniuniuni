from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Payment, Plan, Subscription, User
from app.services.billing.providers import PaymentEvent, PaymentProviderError, get_provider
from app.services.usage import track


def checkout(db: Session, user: User, plan_code: str, currency: str, provider_name: str | None) -> dict:
    plan = db.scalar(select(Plan).where(Plan.code == plan_code, Plan.is_active.is_(True)))
    if plan is None or plan.code == "free":
        raise PaymentProviderError("Unknown or free plan")
    currency = currency.upper()
    if currency not in plan.prices:
        raise PaymentProviderError(f"Plan is not available in {currency}")
    provider = get_provider(provider_name or get_settings().payment_provider_default)
    if not provider.configured:
        raise PaymentProviderError(f"Payment provider '{provider.name}' is not available")
    if currency not in provider.currencies:
        raise PaymentProviderError(f"{provider.name} does not support {currency}")
    amount = float(plan.prices[currency])
    fe = get_settings().frontend_url
    cs = provider.create_checkout(user_id=user.id, plan_code=plan.code, amount=amount, currency=currency,
                                  success_url=f"{fe}/billing/success", cancel_url=f"{fe}/pricing")
    sub = Subscription(user_id=user.id, plan_code=plan.code, status="pending", provider=provider.name,
                       external_id=cs.external_id, currency=currency)
    db.add(sub)
    db.flush()
    db.add(Payment(user_id=user.id, subscription_id=sub.id, provider=provider.name, external_id=cs.external_id,
                   amount=amount, currency=currency, status="pending"))
    track(db, user.id, "checkout_started", plan=plan.code, provider=provider.name, currency=currency)
    return {"redirect_url": cs.redirect_url, "external_id": cs.external_id, "provider": provider.name}


def apply_event(db: Session, provider_name: str, event: PaymentEvent) -> Subscription | None:
    """Idempotent: re-delivered webhooks do not double-activate or double-record."""
    sub = db.scalar(select(Subscription).where(Subscription.external_id == event.external_id, Subscription.provider == provider_name))
    if sub is None:
        return None
    payment = db.scalar(select(Payment).where(Payment.external_id == event.external_id, Payment.provider == provider_name))
    if event.status == "succeeded":
        if sub.status != "active":
            db.execute(update(Subscription).where(Subscription.user_id == sub.user_id, Subscription.status == "active",
                                                  Subscription.id != sub.id).values(status="canceled"))
            sub.status = "active"
            sub.current_period_end = datetime.now(UTC) + timedelta(days=31)
            track(db, sub.user_id, "subscription_activated", plan=sub.plan_code, provider=provider_name)
        if payment and payment.status != "succeeded":
            payment.status = "succeeded"
            payment.raw = event.raw
    elif event.status == "failed":
        sub.status = "past_due" if sub.status == "active" else "pending"
        if payment:
            payment.status = "failed"
    elif event.status == "canceled":
        sub.status = "canceled"
    elif event.status == "refunded" and payment:
        payment.status = "refunded"
    db.flush()
    return sub


def cancel(db: Session, user: User) -> None:
    for sub in db.scalars(select(Subscription).where(Subscription.user_id == user.id, Subscription.status == "active")):
        sub.status = "canceled"
    track(db, user.id, "subscription_canceled")
