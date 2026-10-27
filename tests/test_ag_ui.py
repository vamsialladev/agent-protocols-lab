"""Demo 7: the AG-UI event stream over SSE, validated against the official types, and the approval round trip."""

import json

import httpx
import pytest
from ag_ui.core import Event
from pydantic import TypeAdapter

from demos.ag_ui import demo

EVENT = TypeAdapter(Event)


async def _events(client, url, body):
    out = []
    async with client.stream("POST", url, json=body, headers={"Accept": "text/event-stream"}) as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        async for line in r.aiter_lines():
            if line.startswith("data:"):
                out.append(json.loads(line[5:]))
    return out


@pytest.fixture
def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=demo.app), base_url="http://ag-ui.test")


async def _flow(client, approve):
    ask_body = {"threadId": "t1", "runId": "r1", "messages": [{"role": "user", "content": "Book the kids club"}]}
    first = await _events(client, "/agent", ask_body)
    ask = next(e for e in first if e["type"] == "CUSTOM")
    second = await _events(client, f"/approval/{ask['value']['approval_id']}", {"approve": approve})
    again = await _events(client, f"/approval/{ask['value']['approval_id']}", {"approve": approve})
    return first, second, again


def test_a_run_streams_valid_events_in_order_and_pauses_for_approval(client):
    import asyncio

    first, second, again = asyncio.run(_flow(client, True))
    kinds = [e["type"] for e in first]
    assert kinds[0] == "RUN_STARTED" and kinds[-1] == "RUN_FINISHED"
    assert kinds.index("TOOL_CALL_START") < kinds.index("TOOL_CALL_RESULT") < kinds.index("CUSTOM")
    assert first[-1]["result"]["awaiting"]
    for e in first + second:
        EVENT.validate_python(e)
    assert [e["type"] for e in second][1:3] == ["CUSTOM", "STATE_DELTA"]
    assert second[2]["delta"][0]["value"] == "PENDING_STAFF" and second[-1]["result"] == {"status": "PENDING_STAFF"}
    assert [e["type"] for e in again] == ["RUN_ERROR"]  # an approval can be decided once


def test_declining_sends_nothing(client):
    import asyncio

    _, second, _ = asyncio.run(_flow(client, False))
    assert second[1]["name"] == "human_approval_declined" and second[-1]["result"] == {"status": "CANCELLED"}


def test_the_page_builds_the_dom_without_innerhtml(client):
    import asyncio

    page = asyncio.run(client.get("/")).text
    assert "AG-UI" in page and "textContent" in page and "innerHTML" not in page
