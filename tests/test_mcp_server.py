"""Demo 1: the real hotel-tools-mcp server as a separate stdio process, two roles."""

import asyncio

from demos.mcp_server import demo


def test_each_role_sees_only_its_tools_and_gets_policy_passages():
    out = asyncio.run(demo.main_async())
    assert out["guest"]["tools"] == ["create_booking_request", "list_activities", "lookup_booking", "search_policy"]
    assert "issue_credit_request" in out["front_desk"]["tools"]
    for role in ("guest", "front_desk"):
        passages = out[role]["policy"]["passages"]
        assert any("Pets" in p["section"] and "40 lbs" in p["text"] for p in passages)
    assert "Unknown tool" in str(out["guest"]["denied"])  # not listed, and refused when called anyway
    events = [(e["actor"], e["event"]) for e in out["audit"]]
    assert ("guest", "unlisted_tool_refused") in events and len({e["trace_id"] for e in out["audit"]}) == 1
