"""Demo 10: UCP (Universal Commerce Protocol), a mock checkout: discover, cart, quote, guest confirms, complete.

Follows the UCP specification at tag v2026-08-25 (github.com/Universal-Commerce-Protocol/ucp): discovery at
`/.well-known/ucp`, the checkout capability's REST binding (`POST /checkout-sessions`, `GET` / `PUT
/checkout-sessions/{id}`, `POST .../complete`, `POST .../cancel`), the status lifecycle (`incomplete` ->
`ready_for_complete` -> `completed`, or `canceled`), amounts in minor units, and the `UCP-Agent` header.

**Built from the spec, not the SDK:** the official `ucp-sdk` (Universal-Commerce-Protocol/python-sdk) isn't on PyPI,
and installing it from GitHub was blocked in this environment, so the request and response shapes here are written
from the spec's own examples. The merchant is a mock (the resort gift shop), and payment is a sandbox token: **no
payment network, no real money.**

Guardrails: the price comes from the merchant's catalog (a price in the request is ignored), complete needs the
session to be `ready_for_complete` and an `Idempotency-Key` (the same key returns the same order, never a second
one), the agent completes only after the guest confirms the quoted total, and every call carries `UCP-Agent`.

    python -m demos.ucp.demo
"""

import asyncio
import sys
import uuid

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from protolab.audit import Audit

VERSION = "2026-08-25"
BASE = "http://giftshop.test"
ENDPOINT = f"{BASE}/ucp/v1"
CATALOG = {"robe-beach-resort": ("Beach Resort bathrobe", 6500), "candle-sea-salt": ("Sea salt candle", 2400)}
SESSIONS: dict[str, dict] = {}
ORDERS_BY_KEY: dict[str, dict] = {}


def _envelope(status="success") -> dict:
    return {"version": VERSION, "status": status, "payment_handlers": {"sandbox_token": [{"id": "sandbox"}]}}


def _error(code: str, message: str, http: int = 400) -> JSONResponse:
    return JSONResponse({"ucp": _envelope("error"), "messages": [{"type": "error", "code": code,
                                                                  "content": message}]}, http)  # fmt: skip


def _price(session: dict, line_items: list) -> str | None:
    lines, subtotal = [], 0
    for i, li in enumerate(line_items):
        item_id = (li.get("item") or {}).get("id")
        if item_id not in CATALOG:
            return f"unknown item {item_id!r}"
        title, price = CATALOG[item_id]  # any price the agent sent is ignored
        qty = int(li.get("quantity", 1))
        if not 1 <= qty <= 5:
            return "quantity must be 1 to 5"
        amount = price * qty
        subtotal += amount
        totals = [{"type": "subtotal", "amount": amount}, {"type": "total", "amount": amount}]
        lines.append({"id": f"li_{i}", "item": {"id": item_id, "title": title, "price": price}, "quantity": qty,
                      "totals": totals})  # fmt: skip
    session["line_items"] = lines
    session["totals"] = [{"type": "subtotal", "amount": subtotal}, {"type": "total", "amount": subtotal}]
    return None


def _status(session: dict) -> None:
    if session["status"] in ("completed", "canceled"):
        return
    session["status"] = "ready_for_complete" if session.get("buyer", {}).get("email") else "incomplete"


def _public(session: dict) -> dict:
    return {"ucp": _envelope(), **{k: v for k, v in session.items() if not k.startswith("_")}}


def _agent_ok(request: Request) -> bool:
    return request.headers.get("ucp-agent", "").startswith("profile=")


async def profile(request: Request):
    return JSONResponse({"ucp": {"version": VERSION,
                                 "services": {"dev.ucp.shopping": [{"version": VERSION, "transport": "rest",
                                                                    "endpoint": ENDPOINT}]},
                                 "capabilities": {"dev.ucp.shopping.checkout": [{"version": VERSION}]},
                                 "payment_handlers": {"sandbox_token": [{"id": "sandbox"}]}}})  # fmt: skip


async def create(request: Request):
    if not _agent_ok(request):
        return _error("missing_agent", "UCP-Agent header required", 401)
    body = await request.json()
    session = {"id": f"chk_{uuid.uuid4().hex[:10]}", "status": "incomplete", "currency": "USD",
               "links": [{"type": "terms_of_service", "url": f"{BASE}/terms"}]}  # fmt: skip
    if problem := _price(session, body.get("line_items", [])):
        return _error("invalid_line_items", problem)
    if body.get("buyer"):
        session["buyer"] = {"email": str(body["buyer"].get("email", ""))}
    _status(session)
    SESSIONS[session["id"]] = session
    return JSONResponse(_public(session), 201)


async def read(request: Request):
    session = SESSIONS.get(request.path_params["sid"])
    return JSONResponse(_public(session)) if session else _error("not_found", "no such checkout", 404)


async def update(request: Request):
    session = SESSIONS.get(request.path_params["sid"])
    if session is None:
        return _error("not_found", "no such checkout", 404)
    if session["status"] in ("completed", "canceled"):
        return _error("not_modifiable", f"checkout is {session['status']}", 409)
    body = await request.json()
    if "line_items" in body and (problem := _price(session, body["line_items"])):
        return _error("invalid_line_items", problem)
    if body.get("buyer"):
        session["buyer"] = {"email": str(body["buyer"].get("email", ""))}
    _status(session)
    return JSONResponse(_public(session))


async def complete(request: Request):
    key = request.headers.get("idempotency-key", "")
    if not key:
        return _error("missing_idempotency_key", "Idempotency-Key header required")
    if key in ORDERS_BY_KEY:  # a retry: the same order again, never a second one
        return JSONResponse(ORDERS_BY_KEY[key])
    session = SESSIONS.get(request.path_params["sid"])
    if session is None:
        return _error("not_found", "no such checkout", 404)
    if session["status"] != "ready_for_complete":
        return _error("not_ready", f"checkout is {session['status']}", 409)
    instruments = ((await request.json()).get("payment") or {}).get("instruments") or []
    token = ((instruments[0] if instruments else {}).get("credential") or {}).get("token", "")
    if not token.startswith("tok_sandbox_"):
        return _error("payment_declined", "only sandbox tokens are accepted here", 402)
    session["status"] = "completed"
    session["order"] = {"id": f"ord_{uuid.uuid4().hex[:8]}", "note": "Sandbox order: nothing ships, no money moved."}
    ORDERS_BY_KEY[key] = _public(session)
    return JSONResponse(ORDERS_BY_KEY[key])


async def cancel(request: Request):
    session = SESSIONS.get(request.path_params["sid"])
    if session is None:
        return _error("not_found", "no such checkout", 404)
    if session["status"] == "completed":
        return _error("not_modifiable", "checkout is completed", 409)
    session["status"] = "canceled"
    return JSONResponse(_public(session))


merchant = Starlette(routes=[
    Route("/.well-known/ucp", profile),
    Route("/ucp/v1/checkout-sessions", create, methods=["POST"]),
    Route("/ucp/v1/checkout-sessions/{sid}", read, methods=["GET"]),
    Route("/ucp/v1/checkout-sessions/{sid}", update, methods=["PUT"]),
    Route("/ucp/v1/checkout-sessions/{sid}/complete", complete, methods=["POST"]),
    Route("/ucp/v1/checkout-sessions/{sid}/cancel", cancel, methods=["POST"]),
])  # fmt: skip


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=merchant), base_url=BASE,
                             headers={"UCP-Agent": 'profile="https://concierge.hotel.test/profile"'})  # fmt: skip


async def shop(guest_confirms, audit: Audit) -> dict:
    async with client() as http:
        prof = (await http.get("/.well-known/ucp")).json()["ucp"]
        endpoint = prof["services"]["dev.ucp.shopping"][0]["endpoint"].removeprefix(BASE)
        audit.record("concierge", "discovered", endpoint=endpoint, capabilities=list(prof["capabilities"]))
        cart = {
            "line_items": [{"item": {"id": "robe-beach-resort", "price": 1}, "quantity": 1}]
        }  # the price is ignored
        s = (await http.post(f"{endpoint}/checkout-sessions", json=cart)).json()
        audit.record("concierge", "created", id=s["id"], status=s["status"])
        s = (await http.put(f"{endpoint}/checkout-sessions/{s['id']}",
                            json={"buyer": {"email": "guest@mail.test"}})).json()  # fmt: skip
        total = next(t["amount"] for t in s["totals"] if t["type"] == "total")
        audit.record("concierge", "quoted", status=s["status"], total_minor=total)
        if not guest_confirms(f"{s['line_items'][0]['item']['title']}: ${total / 100:.2f}"):
            done = (await http.post(f"{endpoint}/checkout-sessions/{s['id']}/cancel")).json()
            audit.record("guest", "declined", status=done["status"])
            return {"session": done, "retry": None}
        audit.record("guest", "confirmed", total_minor=total)
        instrument = {"id": "instr_1", "handler_id": "sandbox", "type": "token",
                      "credential": {"type": "token", "token": "tok_sandbox_1"}}  # fmt: skip
        key, pay = uuid.uuid4().hex, {"payment": {"instruments": [instrument]}}
        done = (await http.post(f"{endpoint}/checkout-sessions/{s['id']}/complete", json=pay,
                                headers={"Idempotency-Key": key})).json()  # fmt: skip
        retry = (await http.post(f"{endpoint}/checkout-sessions/{s['id']}/complete", json=pay,
                                 headers={"Idempotency-Key": key})).json()  # fmt: skip
        audit.record("concierge", "completed", status=done["status"], order=done["order"]["id"])
        return {"session": done, "retry": retry}


def run(guest_confirms=lambda summary: True) -> dict:
    audit = Audit()
    out = asyncio.run(shop(guest_confirms, audit))
    return {**out, "audit": audit.events}


def main() -> int:
    out = run()
    s = out["session"]
    print(f"{s['line_items'][0]['item']['title']} x {s['line_items'][0]['quantity']}: "
          f"${s['totals'][-1]['amount'] / 100:.2f} (the agent sent price 1; the catalog price was used)")  # fmt: skip
    print("status:", s["status"], "| order:", s["order"])
    print("retry with the same Idempotency-Key -> same order:", out["retry"]["order"]["id"] == s["order"]["id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
