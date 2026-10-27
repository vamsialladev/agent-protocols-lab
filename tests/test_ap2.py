"""Demo 9: AP2 sandbox mandates (official SDK models + JWT helper), limits, explicit approval, replay protection."""

from datetime import timedelta

import pytest

from demos.ap2 import demo
from protolab.audit import Audit


def test_limits_and_replay_in_one_session():
    out = demo.run()
    assert out["receipt"]["status"] == "SANDBOX_SETTLED" and out["receipt"]["amount_usd"] == 120.0
    assert out["refusals"]["over the per-payment limit ($260)"].startswith("$260.00 is over")
    assert out["refusals"]["second payment ($130, $250 today)"] == "settled"
    assert out["refusals"]["third payment ($120 more)"] == "over the $300 daily limit"
    assert out["refusals"]["replay"].startswith("payment mandate already used")
    assert out["spent"] == 250.0


def buy(**kw):
    guest, merchant, concierge, processor = demo.setup(kw.pop("approves", True))
    return demo.purchase("spa-aromatherapy-60", 1, guest, merchant, concierge, processor, Audit(), **kw)


def test_the_guest_must_approve():
    with pytest.raises(demo.Refused, match="declined"):
        buy(approves=False)


def test_a_cart_changed_after_signing_is_refused():
    def cheaper(cart):
        cart.contents.payment_request.details.total.amount.value = 1.0

    with pytest.raises(demo.Refused, match="changed after the merchant signed"):
        buy(tamper=cheaper)


def test_a_merchant_outside_the_intent_is_refused():
    def other(cart):
        cart.contents.merchant_name = "Friend's Surf Shop"

    with pytest.raises(demo.Refused, match="merchant isn't one the guest asked for"):
        buy(tamper=other)


def test_an_expired_cart_is_refused():
    guest, merchant, concierge, processor = demo.setup()
    old = demo._now() - timedelta(minutes=demo.CART_MINUTES + 1)
    cart = merchant.cart("spa-aromatherapy-60", 1, old)
    expiry = (old + timedelta(hours=1)).isoformat()
    intent = demo.IntentMandate(user_cart_confirmation_required=True, merchants=[demo.MERCHANT],
                                natural_language_description="x", intent_expiry=expiry)  # fmt: skip
    with pytest.raises(demo.Refused, match="expired"):
        concierge.check_cart(intent, cart, demo._now())


def test_a_signature_from_another_key_or_for_another_payment_is_refused():
    guest, merchant, concierge, processor = demo.setup()
    first = demo.purchase("spa-aromatherapy-60", 1, guest, merchant, concierge, processor, Audit())
    impostor = demo.Guest()  # someone else's device key
    mandate = first["mandate"].model_copy(deep=True)
    mandate.payment_mandate_contents.payment_mandate_id = "pm-new"
    mandate.user_authorization = impostor.approve("x", mandate.payment_mandate_contents, first["cart"])
    with pytest.raises(demo.Refused, match="signature"):
        processor.settle(first["cart"], mandate)
    reused = first["mandate"].model_copy(deep=True)
    reused.payment_mandate_contents.payment_mandate_id = "pm-other"  # guest's signature covers the old ID
    with pytest.raises(demo.Refused, match="doesn't cover"):
        processor.settle(first["cart"], reused)
