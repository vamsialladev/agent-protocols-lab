"""Demo 4: ACP (IBM's Agent Communication Protocol, official acp-sdk 1.0.3), side by side with A2A.

**Status:** ACP merged into A2A under the Linux Foundation in August 2025; the acp-sdk repository is read-only. I
run it here to show the difference, not as something I'd start a new project on. It also needs uvicorn 0.35 or
older (newer uvicorn removed a type acp-sdk imports), and its client must send a Content-Type header that current
FastAPI requires: this is what an unmaintained SDK looks like in practice.

1. The same guest-email delegation as demo 3, over ACP's REST messaging: GET /agents (manifests), POST /runs, a run
   that ends "completed" with output messages. Bearer auth as a FastAPI dependency.
2. A small multi-agent writing flow: outline -> draft -> edit, each an ACP agent, the output of one the input of
   the next.

    python -m demos.acp.demo
"""

import asyncio
import hmac
import json
import secrets
import sys

import httpx
from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart
from acp_sdk.server import agent, create_app
from fastapi import Depends, HTTPException, Request

from demos.a2a.demo import URLS, guest_email_agent
from demos.a2a.demo import main_async as a2a_main
from protolab.audit import Audit

URL = "http://acp-agents.test"


def _json_part(obj: dict) -> MessagePart:
    return MessagePart(content_type="application/json", content=json.dumps(obj))


def _read(input: list[Message]) -> dict:
    part = input[-1].parts[-1]
    return json.loads(part.content) if part.content_type == "application/json" else {"text": part.content}


@agent(name="guest_email_agent", description="Drafts replies and staff tasks for review (synthetic data).")
async def email_agent(input: list[Message], context):
    yield _json_part(guest_email_agent(_read(input)))


@agent(name="outline_agent", description="Turns a topic into an outline.")
async def outline_agent(input: list[Message], context):
    topic = _read(input)["text"]
    yield _json_part({"topic": topic, "outline": ["What it is", "Who it's for", "How to book"]})


@agent(name="draft_agent", description="Writes one sentence per outline point.")
async def draft_agent(input: list[Message], context):
    o = _read(input)
    lines = {"What it is": f"{o['topic']} runs every morning at the beach pavilion.",
             "Who it's for": "It's for children aged 4 to 11 staying at the resort.",
             "How to book": "Ask the concierge; staff confirm every request."}  # fmt: skip
    yield _json_part({"topic": o["topic"], "draft": [lines[p] for p in o["outline"]]})


@agent(name="edit_agent", description="Tightens a draft and adds the synthetic-data note.")
async def edit_agent(input: list[Message], context):
    d = _read(input)
    text = " ".join(s.replace(" every morning", " most mornings") for s in d["draft"])
    yield MessagePart(content=f"{text} (Simulated hotel group, synthetic data.)")


def app(token: str):
    async def bearer(request: Request):
        given = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        if not hmac.compare_digest(given.encode(), token.encode()):
            raise HTTPException(status_code=401, detail="unauthorized")

    return create_app(email_agent, outline_agent, draft_agent, edit_agent, dependencies=[Depends(bearer)])


def client(asgi, token: str) -> Client:
    # acp-sdk's client posts JSON without a Content-Type header, and current FastAPI won't parse such a body: set it.
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=asgi), base_url=URL, headers=headers)
    return Client(client=http)


async def main_async(token: str | None = None) -> dict:
    token = token or secrets.token_urlsafe(24)
    audit, asgi = Audit(), app(token)
    email = {"body": "Our room is really noisy at night. Can you move us? Also I was charged twice for parking."}
    # acp-sdk creates its run executor in the app's lifespan; httpx's ASGI transport doesn't run lifespans.
    async with asgi.router.lifespan_context(asgi), client(asgi, token) as acp:
        manifests = [a.name async for a in acp.agents()]
        run = await acp.run_sync(Message(parts=[_json_part(email)]), agent="guest_email_agent")
        audit.record("concierge", "acp_run", agent=run.agent_name, status=str(run.status))
        delegated = json.loads(run.output[-1].parts[-1].content)
        step = Message(parts=[MessagePart(content="Kids club: sandcastle morning")])
        chain = []
        for name in ("outline_agent", "draft_agent", "edit_agent"):
            r = await acp.run_sync(step, agent=name)
            chain.append({"agent": name, "status": str(r.status)})
            step = Message(parts=r.output[-1].parts)
        final = step.parts[-1].content
    a2a = await a2a_main(token)
    same = a2a["delegated"]["artifact"] == delegated
    audit.record("concierge", "compared", same_result=same)
    return {"manifests": manifests, "run_status": str(run.status), "delegated": delegated, "chain": chain,
            "final": final, "same_as_a2a": same, "a2a_url": URLS["email"], "audit": audit.events}  # fmt: skip


def main() -> int:
    out = asyncio.run(main_async())
    print("ACP agents:", out["manifests"])
    print(
        "delegation run:", out["run_status"], out["delegated"]["requests"], "| same result as A2A:", out["same_as_a2a"]
    )
    print("writing chain:", " -> ".join(f"{c['agent']} ({c['status']})" for c in out["chain"]))
    print("final:", out["final"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
