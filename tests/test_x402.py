"""Demo 11: x402 wire format (official package), fully mocked payment, the agent's spending rules."""

import asyncio

import pytest
from x402.schemas.payments import PaymentRequired, PaymentRequirements

from demos.x402 import demo
from protolab.audit import Audit


def test_402_then_pay_then_data_and_a_replay_is_refused():
    out = asyncio.run(demo.main_async())
    assert [e["what"] for e in out["first"]["events"]] == ["Harbour lantern walk", "Farmers market"]
    assert out["first"]["receipt"]["network"] == "mock:sandbox" and out["first"]["receipt"]["success"]
    assert out["replay_status"] == 402 and out["replay_error"] == "voucher_already_used"
    assert out["spent"] == 10_000 and out["balance"] == 490_000
    assert [e["event"] for e in out["audit"]] == ["paying", "paid"]


def req(**kw):
    base = {"scheme": "mock", "network": "mock:sandbox", "asset": "MOCK-USD", "amount": "10000",
            "pay_to": demo.PAY_TO, "max_timeout_seconds": 60}  # fmt: skip
    return PaymentRequirements(**{**base, **kw})


def agent():
    return demo.Agent(demo.MockFacilitator(), Audit())


def test_real_networks_are_never_used_even_when_offered():
    a = agent()
    offered = PaymentRequired(x402_version=2, accepts=[req(scheme="exact", network="eip155:8453"), req()])
    assert a.choose(offered).network == "mock:sandbox"  # Base mainnet skipped, the mock option taken
    assert a.audit.events[0]["why"] == "only the mock network"
    with pytest.raises(demo.Refused, match="no payment option on the mock network"):
        a.choose(PaymentRequired(x402_version=2, accepts=[req(scheme="exact", network="eip155:84532")]))


@pytest.mark.parametrize(
    "kw,why",
    [({"pay_to": "mock:someone-else"}, "allowlisted"), ({"amount": "60000"}, "over the \\$0.05 limit")],
)
def test_payee_and_amount_rules(kw, why):
    with pytest.raises(demo.Refused, match=why):
        agent().choose(PaymentRequired(x402_version=2, accepts=[req(**kw)]))


def test_the_session_budget_holds():
    a = agent()
    a.spent = 195_000
    with pytest.raises(demo.Refused, match="session budget"):
        a.choose(PaymentRequired(x402_version=2, accepts=[req()]))


def test_a_forged_or_mismatched_voucher_does_not_settle():
    f = demo.MockFacilitator()
    payload = demo.PaymentPayload(x402_version=2, accepted=req(), payload=f.authorize("mock:concierge", req()))
    forged = payload.model_copy(deep=True)
    forged.payload["amount"] = "1"
    assert f.settle(forged).error_reason == "invalid_signature"
    cheaper = demo.PaymentPayload(x402_version=2, accepted=req(amount="1"), payload=payload.payload)
    assert f.settle(cheaper).error_reason == "voucher_does_not_match_requirements"
    assert f.settle(payload).success and f.balances["mock:concierge"] == 490_000
