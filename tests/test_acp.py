"""Demo 4: ACP REST runs (acp-sdk, archived; merged into A2A), side by side with A2A, plus a three-agent chain."""

import asyncio

import pytest
from acp_sdk.models import Message, MessagePart

from demos.acp import demo

TOKEN = "test-token-not-a-secret"


def test_delegation_matches_a2a_and_the_writing_chain_completes():
    out = asyncio.run(demo.main_async(TOKEN))
    assert out["manifests"] == ["guest_email_agent", "outline_agent", "draft_agent", "edit_agent"]
    assert out["run_status"].endswith("COMPLETED") and out["same_as_a2a"]
    assert [c["agent"] for c in out["chain"]] == ["outline_agent", "draft_agent", "edit_agent"]
    assert all(c["status"].endswith("COMPLETED") for c in out["chain"])
    assert "most mornings" in out["final"] and out["final"].endswith("(Simulated hotel group, synthetic data.)")


def test_a_wrong_token_is_refused():
    async def go():
        asgi = demo.app(TOKEN)
        async with asgi.router.lifespan_context(asgi), demo.client(asgi, "wrong-token") as acp:
            await acp.run_sync(Message(parts=[MessagePart(content="hi")]), agent="outline_agent")

    with pytest.raises(Exception, match="401|nauthorized"):  # noqa: B017 - acp-sdk raises its own error types
        asyncio.run(go())
