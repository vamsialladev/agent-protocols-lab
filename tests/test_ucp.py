"""Demo 10: UCP checkout against a mock merchant, per the spec's REST binding and status lifecycle."""

import asyncio

import httpx

from demos.ucp import demo

AGENT = {"UCP-Agent": 'profile="https://concierge.hotel.test/profile"'}


def call(method, path, json=None, headers=None):
    """A bare client: only the headers each call passes (demo.client() always sends UCP-Agent)."""

    async def go():
        transport = httpx.ASGITransport(app=demo.merchant)
        async with httpx.AsyncClient(transport=transport, base_url=demo.BASE) as http:
            return await http.request(method, path, json=json, headers=headers)

    return asyncio.run(go())


def test_discover_quote_confirm_complete_and_an_idempotent_retry():
    out = demo.run()
    s = out["session"]
    assert s["status"] == "completed" and s["order"]["id"].startswith("ord_")
    assert s["line_items"][0]["item"]["price"] == 6500 and s["totals"][-1] == {"type": "total", "amount": 6500}
    assert out["retry"]["order"]["id"] == s["order"]["id"]  # same key, same order
    assert [e["event"] for e in out["audit"]] == ["discovered", "created", "quoted", "confirmed", "completed"]


def test_the_guest_declining_cancels_the_session():
    out = demo.run(guest_confirms=lambda summary: False)
    assert out["session"]["status"] == "canceled" and out["retry"] is None


def test_protocol_rules_hold():
    path = "/ucp/v1/checkout-sessions"
    assert call("POST", path, {"line_items": []}).status_code == 401  # no UCP-Agent
    r = call("POST", path, {"line_items": [{"item": {"id": "jet-ski"}, "quantity": 1}]}, AGENT)
    assert r.status_code == 400 and r.json()["messages"][0]["code"] == "invalid_line_items"
    s = call("POST", path, {"line_items": [{"item": {"id": "candle-sea-salt"}, "quantity": 2}]}, AGENT).json()
    assert s["status"] == "incomplete" and s["totals"][-1]["amount"] == 4800
    pay = {"payment": {"instruments": [{"credential": {"token": "tok_sandbox_x"}}]}}
    early = call("POST", f"{path}/{s['id']}/complete", pay, {**AGENT, "Idempotency-Key": "k1"})
    assert early.status_code == 409 and early.json()["messages"][0]["code"] == "not_ready"
    call("PUT", f"{path}/{s['id']}", {"buyer": {"email": "guest@mail.test"}}, AGENT)
    assert call("POST", f"{path}/{s['id']}/complete", pay, AGENT).status_code == 400  # no Idempotency-Key
    real_card = {"payment": {"instruments": [{"credential": {"token": "tok_live_4242"}}]}}
    declined = call("POST", f"{path}/{s['id']}/complete", real_card, {**AGENT, "Idempotency-Key": "k2"})
    assert declined.status_code == 402  # only sandbox tokens
    done = call("POST", f"{path}/{s['id']}/complete", pay, {**AGENT, "Idempotency-Key": "k3"}).json()
    assert done["status"] == "completed"
    assert call("PUT", f"{path}/{s['id']}", {"buyer": {"email": "x@mail.test"}}, AGENT).status_code == 409
    assert call("POST", f"{path}/{s['id']}/cancel", None, AGENT).status_code == 409
