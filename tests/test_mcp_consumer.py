"""Demo 2: the gateway's allowlist, URL check and audit, with fake MCP sessions (no Node, no browser).

The live run (real filesystem and Playwright servers through npx) is `python -m demos.mcp_consumer.demo`, or this
file with LAB_NPX=1.
"""

import asyncio
import os
from types import SimpleNamespace

import pytest

from demos.mcp_consumer import demo
from protolab.audit import Audit

ORIGIN = "http://127.0.0.1:8123"


class FakeSession:
    def __init__(self, tools):
        self.tools, self.calls = tools, []

    async def list_tools(self):
        return SimpleNamespace(tools=[SimpleNamespace(name=t) for t in self.tools])

    async def call_tool(self, name, args):
        self.calls.append((name, args))
        return SimpleNamespace(content=[SimpleNamespace(text=f"{name} ok")], is_error=False)


def gateway():
    sessions = {
        "files": FakeSession(["read_text_file", "list_directory", "write_file", "move_file"]),
        "browser": FakeSession(["browser_navigate", "browser_snapshot", "browser_run_code_unsafe", "browser_evaluate"]),
    }
    return demo.Gateway(sessions, demo.ALLOWLIST, {ORIGIN}, Audit()), sessions


def test_only_allowlisted_tools_are_exposed():
    gw, _ = gateway()
    offered = asyncio.run(gw.discover())
    assert offered == {
        "files": ["list_directory", "read_text_file"],
        "browser": ["browser_navigate", "browser_snapshot"],
    }
    hidden = {e["server"]: e["hidden"] for e in gw.audit.events if e["event"] == "tools_discovered"}
    assert hidden["browser"] == ["browser_evaluate", "browser_run_code_unsafe"]


@pytest.mark.parametrize(
    "server,tool,args",
    [
        ("files", "write_file", {"path": "x", "content": "y"}),
        ("browser", "browser_run_code_unsafe", {"code": "1"}),
        ("browser", "browser_navigate", {"url": "https://example.com/"}),
        ("browser", "browser_navigate", {"url": "http://127.0.0.1:9999/"}),  # same host, other port
    ],
)
def test_refused_calls_never_reach_the_server_and_are_audited(server, tool, args):
    gw, sessions = gateway()
    with pytest.raises(demo.Refused):
        asyncio.run(gw.call(server, tool, args))
    assert sessions[server].calls == [] and gw.audit.events[-1]["event"] == "refused"


def test_allowed_calls_go_through_with_one_trace_id():
    gw, sessions = gateway()
    asyncio.run(gw.call("browser", "browser_navigate", {"url": f"{ORIGIN}/events.html"}))
    asyncio.run(gw.call("files", "read_text_file", {"path": "a.md"}))
    assert sessions["browser"].calls[0][0] == "browser_navigate"
    assert [e["event"] for e in gw.audit.events] == ["called", "called"]
    assert len({e["trace_id"] for e in gw.audit.events}) == 1


@pytest.mark.skipif(os.getenv("LAB_NPX") != "1", reason="live servers through npx: set LAB_NPX=1")
def test_live_three_servers():  # pragma: no cover - needs Node.js, network for npx, and Chrome
    out = asyncio.run(demo.main_async())
    assert "Kids club" in out["brief"]["brochure"] and "turtle talk" in out["brief"]["events_page"].lower()
    assert len(out["refused"]) == 3
