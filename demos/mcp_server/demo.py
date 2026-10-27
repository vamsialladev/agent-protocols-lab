"""Demo 1: an MCP client calling the stage 7 hotel-tools-mcp server over stdio, as two roles.

The server is a separate process, started by the client the way Claude Desktop or any MCP host starts it. One process
serves one API key, so the role is fixed for the session: the server registers only that role's tools. Keys are made
fresh for each run in a temporary folder (only their SHA-256 hashes are stored), so nothing here is a real secret.

    python -m demos.mcp_server.demo
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from protolab.audit import Audit

ROLES = {"guest": ("hg-demo", "elena.ruiz@mail.test"), "front_desk": ("hg-demo", "staff-fd-01")}


def make_keys(runtime: Path) -> dict[str, str]:
    """One random key per role; the keys file holds only hashes."""
    from hotel_tools.auth import add_key

    keys, shown = {}, {}
    for role, (tenant, subject) in ROLES.items():
        shown[role] = add_key(keys, role, tenant, subject)
    (runtime / "keys.json").write_text(json.dumps(keys), encoding="utf-8")
    return shown


def server_params(key: str, runtime: Path) -> StdioServerParameters:
    env = {**os.environ, "HOTEL_MCP_API_KEY": key, "HOTEL_MCP_RUNTIME_DIR": str(runtime),
           "HOTEL_MCP_KEYS_FILE": str(runtime / "keys.json")}  # fmt: skip
    return StdioServerParameters(command=sys.executable, args=["-m", "hotel_tools.server"], env=env)


def _payload(result) -> dict:
    if getattr(result, "structured_content", None):
        return result.structured_content
    text = "".join(getattr(c, "text", "") for c in result.content)
    try:
        return json.loads(text)
    except ValueError:
        return {"text": text}


async def as_role(role: str, key: str, runtime: Path, audit: Audit) -> dict:
    async with stdio_client(server_params(key, runtime)) as (read, write), ClientSession(read, write) as session:
        info = await session.initialize()
        tools = sorted(t.name for t in (await session.list_tools()).tools)
        audit.record(role, "tools_listed", server=info.server_info.name, tools=tools)
        result = await session.call_tool(
            "search_policy", {"question": "Can I bring my dog?", "property": "beach-resort"}
        )
        found = _payload(result)
        audit.record(role, "search_policy", passages=len(found.get("passages", [])))
        denied = None
        if "issue_credit_request" not in tools:  # not even listed for this role; calling it anyway is refused
            denied = _payload(
                await session.call_tool(
                    "issue_credit_request", {"booking_id": "BR-1001", "amount_usd": 20, "reason": "x"}
                )
            )
            audit.record(role, "unlisted_tool_refused", result=str(denied)[:120])
        return {"tools": tools, "policy": found, "denied": denied}


async def main_async() -> dict:
    audit = Audit()
    with tempfile.TemporaryDirectory(prefix="mcp-demo-") as tmp:
        runtime = Path(tmp)
        keys = make_keys(runtime)
        out = {role: await as_role(role, key, runtime, audit) for role, key in keys.items()}
    out["audit"] = audit.events
    return out


def main() -> int:
    out = asyncio.run(main_async())
    for role in ROLES:
        r = out[role]
        first = (r["policy"].get("passages") or [{}])[0]
        print(f"{role}: {len(r['tools'])} tools {r['tools']}")
        print(f"  search_policy -> {first.get('section')}: {first.get('text', '')[:80]}")
        if r["denied"] is not None:
            print(f"  issue_credit_request (not listed) -> {str(r['denied'])[:90]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
