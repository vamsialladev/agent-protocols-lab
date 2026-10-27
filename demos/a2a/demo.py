"""Demo 3: A2A (official a2a-sdk). Two flows, both over real A2A JSON-RPC with bearer auth, in-process:

1. Delegation: the concierge agent hands a guest email it can't handle to the guest-email agent, reads that agent's
   card first (skills, auth), and gets a task that goes working -> completed with one data artifact.
2. Collaboration: a reader agent turns a source document into facts; an ideas agent turns the facts into ideas.
   The concierge only passes artifacts between them.

The agents here are small rule-based stand-ins so the demo needs no API key. The real stage 2 Guest Request Agent
runs the same protocol with Claude (guest-request-agent, src/a2a_server.py).

    python -m demos.a2a.demo
"""

import asyncio
import re
import secrets
import sys
from pathlib import Path

from protolab.a2a_kit import agent_app, send
from protolab.audit import Audit

ROOT = Path(__file__).resolve().parents[2]
URLS = {"email": "http://guest-email.test", "reader": "http://reader.test", "ideas": "http://ideas.test"}
KINDS = {
    "room_change": r"\b(?:noisy|noise|quieter|move (?:us|rooms?)|room change)\b",
    "late_checkout": r"\blate check-?out\b",
    "billing": r"\b(?:charged|charge|bill|refund|invoice)\b",
}


def guest_email_agent(data: dict) -> dict:
    body = str(data.get("body", ""))
    if not body.strip():
        raise ValueError("no email body")
    found = [k for k, pattern in KINDS.items() if re.search(pattern, body, re.I)]
    return {
        "requests": found or ["other"],
        "staff_tasks": [f"front_desk: {k.replace('_', ' ')}" for k in found],
        "draft": "Thank you for your message. Our team will look into this and reply today.",
        "note": "Draft for staff review; nothing was sent to the guest.",
    }


def reader_agent(data: dict) -> dict:
    """Facts from a source document: one per bullet, with any time and price."""
    facts = []
    for line in str(data.get("document", "")).splitlines():
        if not line.startswith("- "):
            continue
        item = line[2:].split(",")[0].split(":")[0].strip()
        times = re.findall(r"\d{2}:\d{2}-\d{2}:\d{2}", line)
        price = re.findall(r"\$\d+", line)
        facts.append({"item": item, "time": times[0] if times else "", "price": price[0] if price else "free"})
    return {"facts": facts}


def ideas_agent(data: dict) -> dict:
    """Ideas from facts: pair a morning and an evening item into a day plan, and flag the free ones."""
    facts = data.get("facts", [])
    morning = [f for f in facts if f["time"][:2] and int(f["time"][:2]) < 12]
    evening = [f for f in facts if f["time"][:2] and int(f["time"][:2]) >= 17]
    ideas = [f"Day plan: {m['item']} then {e['item']}" for m in morning[:1] for e in evening[:1]]
    ideas += [f"Free for families: {f['item']}" for f in facts if f["price"] == "free"]
    return {"ideas": ideas, "from_facts": len(facts)}


def apps(token: str) -> dict:
    return {
        "email": agent_app("Guest email agent", "handle_guest_email", "Drafts replies and staff tasks for review.",
                           guest_email_agent, token, URLS["email"]),
        "reader": agent_app("Reader agent", "extract_facts", "Turns a document into facts.",
                            reader_agent, token, URLS["reader"]),
        "ideas": agent_app("Ideas agent", "propose_ideas", "Turns facts into ideas.",
                           ideas_agent, token, URLS["ideas"]),
    }  # fmt: skip


async def main_async(token: str | None = None) -> dict:
    token = token or secrets.token_urlsafe(24)  # per run; the agents share it like a service credential
    audit, agents = Audit(), apps(token)
    email = {"body": "Our room is really noisy at night. Can you move us? Also I was charged twice for parking."}
    delegated = await send(agents["email"], email, token, URLS["email"])
    audit.record("concierge", "delegated", to=delegated["card"]["name"], state=delegated["state"])
    document = (ROOT / "data" / "brochures" / "beach-resort-activities.md").read_text(encoding="utf-8")
    facts = await send(agents["reader"], {"document": document}, token, URLS["reader"])
    audit.record("concierge", "facts", count=len(facts["artifact"]["facts"]))
    ideas = await send(agents["ideas"], facts["artifact"], token, URLS["ideas"])
    audit.record("concierge", "ideas", count=len(ideas["artifact"]["ideas"]))
    return {"delegated": delegated, "facts": facts, "ideas": ideas, "audit": audit.events}


def main() -> int:
    out = asyncio.run(main_async())
    d = out["delegated"]
    print(
        f"card: {d['card']['name']} · skill {d['card']['skills'][0]['id']} · auth {list(d['card']['securitySchemes'])}"
    )
    print(f"task: {' -> '.join(t for t in d['history'] if t)} -> {d['state']}")
    print("artifact:", d["artifact"]["requests"], d["artifact"]["staff_tasks"])
    print("facts:", [f["item"] for f in out["facts"]["artifact"]["facts"]])
    print("ideas:", out["ideas"]["artifact"]["ideas"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
