"""Demo 11: x402. A mock API answers HTTP 402 with payment terms; the agent pays a fully mocked payment and retries.

Uses the official `x402` 2.25.0 package for the wire format: the `PaymentRequired` / `PaymentRequirements` /
`PaymentPayload` / `SettleResponse` schemas and its header helpers (`PAYMENT-REQUIRED`, `PAYMENT-SIGNATURE`,
`PAYMENT-RESPONSE`, base64 JSON). The payment itself is a **mock scheme on a mock network** (`mock` /
`mock:sandbox`): a mock facilitator holds play-money balances and signs vouchers with an HMAC key made per run.
**No blockchain, no mainnet, no testnet, no wallet, no private key, no real funds.** x402's real schemes (e.g.
`exact` with an EIP-3009 signature on an EVM network) are not used here.

The agent's rules, each tested: it pays only on the mock network, only allowlisted payees, at most $0.05 a request
and $0.20 a session; a voucher works once (the facilitator refuses a replay); and the API serves the data only
after the facilitator settles.

    python -m demos.x402.demo
"""

import asyncio
import hashlib
import hmac
import json
import secrets
import sys
import uuid
from dataclasses import dataclass, field

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from x402.http.constants import PAYMENT_REQUIRED_HEADER, PAYMENT_RESPONSE_HEADER, PAYMENT_SIGNATURE_HEADER
from x402.http.utils import (
    decode_payment_required_header,
    decode_payment_response_header,
    decode_payment_signature_header,
    encode_payment_required_header,
    encode_payment_response_header,
    encode_payment_signature_header,
)
from x402.schemas.payments import PaymentPayload, PaymentRequired, PaymentRequirements, ResourceInfo
from x402.schemas.responses import SettleResponse

from protolab.audit import Audit

NETWORK, SCHEME, ASSET = "mock:sandbox", "mock", "MOCK-USD"  # play money, in micro-units (1 USD = 1,000,000)
PRICE = "10000"  # $0.01 per call
PAY_TO = "mock:events-feed.partner.test"
MICRO = 1_000_000


class Refused(PermissionError):
    pass


@dataclass
class MockFacilitator:
    """Holds play-money balances; issues and settles one-time vouchers. Nothing here touches a real network."""

    balances: dict = field(default_factory=lambda: {"mock:concierge": 500_000})  # $0.50 of play money
    key: bytes = field(default_factory=lambda: secrets.token_bytes(32))
    settled: set = field(default_factory=set)

    def _sig(self, v: dict) -> str:
        return hmac.new(self.key, json.dumps(v, sort_keys=True).encode(), hashlib.sha256).hexdigest()

    def authorize(self, payer: str, req: PaymentRequirements) -> dict:
        if self.balances.get(payer, 0) < int(req.amount):
            raise Refused("insufficient play-money balance")
        voucher = {"id": uuid.uuid4().hex, "payer": payer, "pay_to": req.pay_to, "amount": req.amount,
                   "asset": req.asset, "network": req.network}  # fmt: skip
        return {**voucher, "sig": self._sig(voucher)}

    def settle(self, payload: PaymentPayload) -> SettleResponse:
        v = dict(payload.payload)
        sig = v.pop("sig", "")
        ok = hmac.compare_digest(sig, self._sig(v))
        reason = None
        if not ok:
            reason = "invalid_signature"
        elif v["id"] in self.settled:
            reason = "voucher_already_used"
        elif (v["pay_to"], v["amount"], v["network"]) != (payload.accepted.pay_to, payload.accepted.amount, NETWORK):
            reason = "voucher_does_not_match_requirements"
        if reason:
            return SettleResponse(success=False, error_reason=reason, transaction="", network=NETWORK)
        self.settled.add(v["id"])
        self.balances[v["payer"]] -= int(v["amount"])
        return SettleResponse(success=True, transaction=f"mock-tx-{v['id'][:12]}", network=NETWORK,
                              payer=v["payer"], amount=v["amount"])  # fmt: skip


def paid_api(facilitator: MockFacilitator) -> Starlette:
    requirements = PaymentRequirements(scheme=SCHEME, network=NETWORK, asset=ASSET, amount=PRICE, pay_to=PAY_TO,
                                       max_timeout_seconds=60)  # fmt: skip
    resource = ResourceInfo(url="http://events-feed.test/events", description="Local events this week (synthetic)")

    def payment_required(required: PaymentRequired) -> JSONResponse:
        header = {PAYMENT_REQUIRED_HEADER: encode_payment_required_header(required)}
        return JSONResponse({"error": required.error or "payment required"}, 402, headers=header)

    async def events(request: Request):
        header = request.headers.get(PAYMENT_SIGNATURE_HEADER)
        if not header:
            return payment_required(PaymentRequired(x402_version=2, accepts=[requirements], resource=resource))
        payload = decode_payment_signature_header(header)
        result = facilitator.settle(payload)
        if not result.success:
            return payment_required(PaymentRequired(x402_version=2, accepts=[requirements], error=result.error_reason))
        data = {"events": [{"day": "Tuesday", "what": "Harbour lantern walk", "time": "19:00"},
                           {"day": "Friday", "what": "Farmers market", "time": "08:00"}]}  # fmt: skip
        return JSONResponse(data, headers={PAYMENT_RESPONSE_HEADER: encode_payment_response_header(result)})

    return Starlette(routes=[Route("/events", events)])


@dataclass
class Agent:
    facilitator: MockFacilitator
    audit: Audit
    payer: str = "mock:concierge"
    per_request_max: int = 50_000  # $0.05
    session_max: int = 200_000  # $0.20
    allowed_payees: frozenset = frozenset({PAY_TO})
    spent: int = 0
    last_payload: PaymentPayload | None = None

    def choose(self, required: PaymentRequired) -> PaymentRequirements:
        for req in required.accepts:
            if req.network != NETWORK or req.scheme != SCHEME:
                self.audit.record("agent", "skipped_option", network=req.network, why="only the mock network")
                continue
            if req.pay_to not in self.allowed_payees:
                raise Refused(f"payee {req.pay_to} isn't allowlisted")
            if int(req.amount) > self.per_request_max:
                raise Refused(f"${int(req.amount) / MICRO:.2f} is over the ${self.per_request_max / MICRO:.2f} limit")
            if self.spent + int(req.amount) > self.session_max:
                raise Refused("over the session budget")
            return req
        raise Refused("no payment option on the mock network")

    async def get(self, http: httpx.AsyncClient, url: str) -> dict:
        r = await http.get(url)
        if r.status_code != 402:
            return r.json()
        required = decode_payment_required_header(r.headers[PAYMENT_REQUIRED_HEADER])
        req = self.choose(required)
        self.audit.record("agent", "paying", amount=req.amount, pay_to=req.pay_to, network=req.network)
        payload = PaymentPayload(x402_version=2, accepted=req, payload=self.facilitator.authorize(self.payer, req))
        self.last_payload = payload
        r = await http.get(url, headers={PAYMENT_SIGNATURE_HEADER: encode_payment_signature_header(payload)})
        if r.status_code != 200:
            raise Refused(f"payment failed: {r.json().get('error')}")
        receipt = decode_payment_response_header(r.headers[PAYMENT_RESPONSE_HEADER])
        self.spent += int(receipt.amount or 0)
        self.audit.record("agent", "paid", transaction=receipt.transaction, spent=self.spent)
        return {**r.json(), "receipt": receipt.model_dump()}


def client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://events-feed.test")


async def main_async() -> dict:
    audit, facilitator = Audit(), MockFacilitator()
    agent, app = Agent(facilitator, audit), paid_api(facilitator)
    async with client(app) as http:
        first = await agent.get(http, "/events")
        replay = await http.get("/events", headers={PAYMENT_SIGNATURE_HEADER:
                                                    encode_payment_signature_header(agent.last_payload)})  # fmt: skip
    return {"first": first, "replay_status": replay.status_code, "replay_error": replay.json()["error"],
            "spent": agent.spent, "balance": facilitator.balances["mock:concierge"], "audit": audit.events}  # fmt: skip


def main() -> int:
    out = asyncio.run(main_async())
    print("events:", [e["what"] for e in out["first"]["events"]])
    print("receipt:", out["first"]["receipt"]["transaction"], out["first"]["receipt"]["network"])
    print(f"replayed voucher -> HTTP {out['replay_status']} {out['replay_error']}")
    print(f"spent ${out['spent'] / MICRO:.2f} of play money; balance ${out['balance'] / MICRO:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
