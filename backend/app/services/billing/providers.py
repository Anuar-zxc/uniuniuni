"""Payment provider abstraction. Core billing logic never depends on a concrete provider."""

import hashlib
import hmac
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.core.config import get_settings


class PaymentProviderError(RuntimeError):
    pass


@dataclass
class CheckoutSession:
    provider: str
    external_id: str
    redirect_url: str


@dataclass
class PaymentEvent:
    """Provider-agnostic normalized webhook event."""

    external_id: str  # checkout/subscription id we stored on Subscription.external_id
    status: str  # succeeded | failed | canceled | refunded
    amount: float
    currency: str
    raw: dict


class PaymentProvider(ABC):
    name: str
    currencies: tuple[str, ...]

    @abstractmethod
    def create_checkout(self, *, user_id: int, plan_code: str, amount: float, currency: str, success_url: str,
                        cancel_url: str) -> CheckoutSession: ...

    @abstractmethod
    def parse_webhook(self, body: bytes, headers: dict[str, str]) -> PaymentEvent: ...

    @property
    def configured(self) -> bool:
        return True


class SandboxProvider(PaymentProvider):
    """Development provider: checkout redirects to our own confirm page; no money moves."""

    name = "sandbox"
    currencies = ("KZT", "USD")

    def create_checkout(self, *, user_id, plan_code, amount, currency, success_url, cancel_url):
        ext = f"sbx_{uuid.uuid4().hex[:16]}"
        return CheckoutSession(self.name, ext, f"{get_settings().frontend_url}/billing/sandbox?session={ext}")

    def parse_webhook(self, body, headers):
        data = json.loads(body or b"{}")
        return PaymentEvent(data["external_id"], data.get("status", "succeeded"), float(data.get("amount", 0)),
                            data.get("currency", "KZT"), data)

    @property
    def configured(self) -> bool:
        return bool(get_settings().payments_sandbox)


class StripeProvider(PaymentProvider):
    name = "stripe"
    currencies = ("USD", "KZT")

    @property
    def configured(self) -> bool:
        return bool(get_settings().stripe_secret_key)

    def create_checkout(self, *, user_id, plan_code, amount, currency, success_url, cancel_url):
        s = get_settings()
        if not s.stripe_secret_key:
            raise PaymentProviderError("Stripe is not configured")
        form = {
            "mode": "subscription",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": str(user_id),
            "metadata[plan_code]": plan_code,
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": currency.lower(),
            "line_items[0][price_data][unit_amount]": str(int(round(amount * 100))),
            "line_items[0][price_data][recurring][interval]": "month",
            "line_items[0][price_data][product_data][name]": f"OfferReady {plan_code.title()}",
        }
        r = httpx.post("https://api.stripe.com/v1/checkout/sessions", data=form, auth=(s.stripe_secret_key, ""), timeout=30)
        if r.status_code >= 400:
            raise PaymentProviderError(f"Stripe error: {r.text[:300]}")
        data = r.json()
        return CheckoutSession(self.name, data["id"], data["url"])

    def parse_webhook(self, body, headers):
        s = get_settings()
        sig = headers.get("stripe-signature", "")
        if s.stripe_webhook_secret:
            parts = dict(p.split("=", 1) for p in sig.split(",") if "=" in p)
            ts, v1 = parts.get("t", ""), parts.get("v1", "")
            expected = hmac.new(s.stripe_webhook_secret.encode(), f"{ts}.{body.decode()}".encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, v1) or abs(time.time() - int(ts or 0)) > 300:
                raise PaymentProviderError("Invalid Stripe signature")
        event = json.loads(body)
        obj = event.get("data", {}).get("object", {})
        status = {"checkout.session.completed": "succeeded", "invoice.payment_failed": "failed",
                  "customer.subscription.deleted": "canceled", "charge.refunded": "refunded"}.get(event.get("type"), "ignored")
        return PaymentEvent(obj.get("id", ""), status, (obj.get("amount_total") or 0) / 100,
                            (obj.get("currency") or "usd").upper(), event)


class _NotYetIntegrated(PaymentProvider):
    """Local providers share the interface; integration needs merchant credentials and their API contract."""

    name = "base"
    currencies = ("KZT",)

    @property
    def configured(self) -> bool:
        return False

    def create_checkout(self, **kwargs):
        raise PaymentProviderError(f"{self.name} is not configured for this deployment")

    def parse_webhook(self, body, headers):
        raise PaymentProviderError(f"{self.name} is not configured for this deployment")


class KaspiProvider(_NotYetIntegrated):
    name = "kaspi"


class FreedomPayProvider(_NotYetIntegrated):
    name = "freedompay"


class HalykProvider(_NotYetIntegrated):
    name = "halyk"


class PaddleProvider(_NotYetIntegrated):
    name = "paddle"
    currencies = ("USD",)


PROVIDERS: dict[str, PaymentProvider] = {
    p.name: p for p in (SandboxProvider(), StripeProvider(), KaspiProvider(), FreedomPayProvider(), HalykProvider(), PaddleProvider())
}


def get_provider(name: str) -> PaymentProvider:
    p = PROVIDERS.get(name)
    if p is None:
        raise PaymentProviderError(f"Unknown payment provider {name}")
    return p
