"""Demo 9: AP2 (Agent Payments Protocol), sandbox only. A payment mandate with limits and an explicit human approval.

Uses the official AP2 SDK from its GitHub tag v0.2.0 (commit b4587ac): the mandate models (`IntentMandate`,
`CartMandate`, `PaymentMandate`, W3C `PaymentRequest`) and its JWT helper for signatures. The PyPI package named
`ap2` is someone else's, so the lab installs from the tag. The SDK pins exact versions (pydantic 2.12.5,
cryptography 46.0.5, pytest at runtime); the lab installs it without those pins and its models and JWT helper run
fine on newer versions (tests below).

1. The guest's intent: what, from which merchant, until when (IntentMandate).
2. The spa desk (merchant agent) builds the cart from its own price list and signs it (CartMandate,
   merchant_authorization = ES256 JWT over the cart).
3. The concierge (shopping agent) checks the merchant is in the intent, the cart signature, the expiry, and the
   limits: $200 per payment, $300 a day. It can't approve anything itself.
4. The guest approves explicitly; their device key signs the PaymentMandate (user_authorization).
5. A mock processor verifies both signatures, the totals and that the mandate ID is new, and returns a sandbox
   receipt. **No payment network, no card, no real money; keys are generated per run and never leave memory.**

    python -m demos.ap2.demo
"""

import hashlib
import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ap2.models.mandate import CartContents, CartMandate, IntentMandate, PaymentMandate, PaymentMandateContents
from ap2.models.payment_request import (
    PaymentCurrencyAmount,
    PaymentDetailsInit,
    PaymentItem,
    PaymentMethodData,
    PaymentRequest,
    PaymentResponse,
)
from ap2.sdk.jwt_helper import create_jwt, verify_jwt
from jwcrypto.jwk import JWK

from protolab.audit import Audit

MERCHANT = "Beach Resort Spa (sandbox)"
PRICES = {
    "spa-aromatherapy-60": ("Aromatherapy massage, 60 min", 120.0),
    "spa-hot-stone-60": ("Hot stone, 60 min", 130.0),
}
PER_PAYMENT_LIMIT, DAILY_LIMIT = 200.0, 300.0
CART_MINUTES = 15


class Refused(PermissionError):
    pass


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _digest(model) -> str:
    return hashlib.sha256(json.dumps(model.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()


def _key() -> JWK:
    return JWK.generate(kty="EC", crv="P-256")


@dataclass
class Merchant:
    key: JWK = field(default_factory=_key)

    def cart(self, sku: str, quantity: int, now: datetime) -> CartMandate:
        label, price = PRICES[sku]  # the price comes from the merchant's list, never from the conversation
        total = PaymentItem(label="Total", amount=PaymentCurrencyAmount(currency="USD", value=price * quantity))
        request = PaymentRequest(
            method_data=[PaymentMethodData(supported_methods="sandbox-room-charge")],
            details=PaymentDetailsInit(id=f"order-{uuid.uuid4().hex[:8]}", total=total, display_items=[
                PaymentItem(label=f"{label} x {quantity}", amount=total.amount)]),
        )  # fmt: skip
        contents = CartContents(id=f"cart-{uuid.uuid4().hex[:8]}", user_cart_confirmation_required=True,
                                payment_request=request, merchant_name=MERCHANT,
                                cart_expiry=(now + timedelta(minutes=CART_MINUTES)).isoformat())  # fmt: skip
        jwt = create_jwt({"alg": "ES256", "typ": "JWT"}, {"cart_hash": _digest(contents), "iss": MERCHANT}, self.key)
        return CartMandate(contents=contents, merchant_authorization=jwt)


@dataclass
class Guest:
    approves: bool = True
    key: JWK = field(default_factory=_key)

    def approve(self, summary: str, payment: PaymentMandateContents, cart: CartMandate) -> str | None:
        """The explicit human step. Signs the payment and the cart it pays for, or returns None."""
        if not self.approves:
            return None
        claims = {"payment_hash": _digest(payment), "cart_hash": _digest(cart.contents), "approved": summary}
        return create_jwt({"alg": "ES256", "typ": "JWT"}, claims, self.key)


@dataclass
class Concierge:
    """The shopping agent: it prepares and checks, the guest authorises. It holds no key that can authorise."""

    merchant_key: JWK
    spent_today: float = 0.0

    def check_cart(self, intent: IntentMandate, cart: CartMandate, now: datetime) -> float:
        c = cart.contents
        if c.merchant_name not in (intent.merchants or []):
            raise Refused("merchant isn't one the guest asked for")
        if datetime.fromisoformat(intent.intent_expiry) < now or datetime.fromisoformat(c.cart_expiry) < now:
            raise Refused("intent or cart expired")
        try:
            claims = verify_jwt(cart.merchant_authorization or "", self.merchant_key)
        except Exception as exc:  # noqa: BLE001 - any signature problem is a refusal
            raise Refused("merchant signature doesn't verify") from exc
        if claims.get("cart_hash") != _digest(c):
            raise Refused("cart changed after the merchant signed it")
        total = c.payment_request.details.total.amount.value
        if total > PER_PAYMENT_LIMIT:
            raise Refused(f"${total:.2f} is over the ${PER_PAYMENT_LIMIT:.0f} per-payment limit")
        if self.spent_today + total > DAILY_LIMIT:
            raise Refused(f"over the ${DAILY_LIMIT:.0f} daily limit")
        return total

    def payment(self, cart: CartMandate, now: datetime) -> PaymentMandateContents:
        d = cart.contents.payment_request.details
        return PaymentMandateContents(
            payment_mandate_id=f"pm-{uuid.uuid4().hex[:10]}", payment_details_id=d.id, payment_details_total=d.total,
            payment_response=PaymentResponse(request_id=d.id, method_name="sandbox-room-charge"),
            merchant_agent=MERCHANT, timestamp=now.isoformat(),
        )  # fmt: skip


@dataclass
class MockProcessor:
    merchant_key: JWK
    guest_key: JWK
    used: set = field(default_factory=set)

    def settle(self, cart: CartMandate, mandate: PaymentMandate) -> dict:
        p = mandate.payment_mandate_contents
        if p.payment_mandate_id in self.used:
            raise Refused("payment mandate already used (replay)")
        try:
            user = verify_jwt(mandate.user_authorization or "", self.guest_key)
            merchant = verify_jwt(cart.merchant_authorization or "", self.merchant_key)
        except Exception as exc:  # noqa: BLE001
            raise Refused("a signature doesn't verify") from exc
        if user["payment_hash"] != _digest(p) or user["cart_hash"] != merchant["cart_hash"]:
            raise Refused("the approval doesn't cover this payment and cart")
        if p.payment_details_total.amount.value != cart.contents.payment_request.details.total.amount.value:
            raise Refused("payment total doesn't match the cart")
        self.used.add(p.payment_mandate_id)
        return {"status": "SANDBOX_SETTLED", "mandate": p.payment_mandate_id,
                "amount_usd": p.payment_details_total.amount.value, "note": "Sandbox: no money moved."}  # fmt: skip


def purchase(sku: str, quantity: int, guest: Guest, merchant: Merchant, concierge: Concierge,
             processor: MockProcessor, audit: Audit, now: datetime | None = None, tamper=None) -> dict:  # fmt: skip
    now = now or _now()
    intent = IntentMandate(user_cart_confirmation_required=True, merchants=[MERCHANT], skus=[sku],
                           natural_language_description=f"Book {quantity} x {sku} for tomorrow afternoon",
                           intent_expiry=(now + timedelta(hours=1)).isoformat(),
                           requires_refundability=True)  # fmt: skip
    cart = merchant.cart(sku, quantity, now)
    if tamper:
        tamper(cart)
    total = concierge.check_cart(intent, cart, now)
    audit.record("concierge", "cart_checked", total=total, merchant=cart.contents.merchant_name)
    contents = concierge.payment(cart, now)
    signature = guest.approve(f"${total:.2f} to {MERCHANT}", contents, cart)
    if signature is None:
        audit.record("guest", "declined")
        raise Refused("the guest declined")
    audit.record("guest", "approved", total=total)
    mandate = PaymentMandate(payment_mandate_contents=contents, user_authorization=signature)
    receipt = processor.settle(cart, mandate)
    concierge.spent_today += total
    audit.record("processor", "settled", **receipt)
    return {"intent": intent, "cart": cart, "mandate": mandate, "receipt": receipt}


def setup(approves: bool = True):
    merchant, guest = Merchant(), Guest(approves)
    return guest, merchant, Concierge(merchant.key), MockProcessor(merchant.key, guest.key)


def run() -> dict:
    audit = Audit()
    guest, merchant, concierge, processor = setup()
    first = purchase("spa-aromatherapy-60", 1, guest, merchant, concierge, processor, audit)
    refusals = {}
    for name, args in (("over the per-payment limit ($260)", ("spa-hot-stone-60", 2)),
                       ("second payment ($130, $250 today)", ("spa-hot-stone-60", 1)),
                       ("third payment ($120 more)", ("spa-aromatherapy-60", 1))):  # fmt: skip
        try:
            purchase(*args, guest, merchant, concierge, processor, audit)
            refusals[name] = "settled"
        except Refused as exc:
            refusals[name] = str(exc)
    try:
        processor.settle(first["cart"], first["mandate"])
    except Refused as exc:
        refusals["replay"] = str(exc)
    return {"receipt": first["receipt"], "refusals": refusals, "spent": concierge.spent_today, "audit": audit.events}


def main() -> int:
    out = run()
    print("first payment:", out["receipt"])
    for k, v in out["refusals"].items():
        print(f"{k}: {v}")
    print(f"authorised today: ${out['spent']:.2f} (sandbox)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
