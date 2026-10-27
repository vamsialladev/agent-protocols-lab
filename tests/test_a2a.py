"""Demo 3: A2A delegation and two-agent collaboration over the official SDK, in-process."""

import asyncio

import pytest

from demos.a2a import demo
from protolab.a2a_kit import send

TOKEN = "test-token-not-a-secret"


def test_delegation_completes_with_an_artifact_and_collaboration_turns_a_document_into_ideas():
    out = asyncio.run(demo.main_async(TOKEN))
    d = out["delegated"]
    assert d["card"]["skills"][0]["id"] == "handle_guest_email" and "bearer" in d["card"]["securitySchemes"]
    assert d["state"] == "TASK_STATE_COMPLETED" and d["artifact"]["requests"] == ["room_change", "billing"]
    assert "nothing was sent" in d["artifact"]["note"]
    assert [f["item"] for f in out["facts"]["artifact"]["facts"]] == ["Kids club", "Reef snorkel tour", "Sunset cruise"]
    assert "Day plan: Kids club then Sunset cruise" in out["ideas"]["artifact"]["ideas"]
    assert [e["event"] for e in out["audit"]] == ["delegated", "facts", "ideas"]


def test_a_wrong_token_is_refused():
    app = demo.apps(TOKEN)["email"]
    with pytest.raises(Exception, match="401|nauthorized"):  # noqa: B017 - the SDK's error type varies by transport
        asyncio.run(send(app, {"body": "hi"}, "wrong-token", demo.URLS["email"]))


def test_a_bad_request_fails_the_task_cleanly():
    out = asyncio.run(send(demo.apps(TOKEN)["email"], {"body": " "}, TOKEN, demo.URLS["email"]))
    assert out["state"] == "TASK_STATE_FAILED" and out["artifact"] is None
