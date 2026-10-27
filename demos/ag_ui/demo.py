"""Demo 7: AG-UI. A backend agent streams AG-UI events (official ag-ui-protocol 1.0, its EventEncoder, SSE) to a
minimal web page: text, a tool call with its result, a state snapshot, and a pause for human approval.

    POST /agent            {"threadId", "runId", "messages": [...]}  -> one run as Server-Sent Events
    POST /approval/<id>    {"approve": true|false}                     -> a second run that finishes the booking request
    GET  /                 the page (vanilla JS, reads the stream, shows an Approve / Decline card)

The "agent" is scripted (it books the kids club for two), so the demo needs no API key; what matters is the event
stream. Approval decisions are kept per approval ID; an ID can be decided once.

    python -m demos.ag_ui.demo        then open http://127.0.0.1:8007
"""

import json
import sys
import uuid
from pathlib import Path

from ag_ui.core import (
    CustomEvent,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateDeltaEvent,
    StateSnapshotEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from ag_ui.encoder import EventEncoder
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.routing import Route

HERE = Path(__file__).resolve().parent
PENDING: dict[str, dict] = {}  # approval id -> what waits for a person
SESSION = {"activity": "Kids club: sandcastle morning", "date": "2026-11-03", "start": "09:30", "party": 2}


def _text(message_id: str, text: str):
    yield TextMessageStartEvent(message_id=message_id, role="assistant")
    for word in text.split(" "):
        yield TextMessageContentEvent(message_id=message_id, delta=word + " ")
    yield TextMessageEndEvent(message_id=message_id)


def booking_run(thread_id: str, run_id: str, message: str):
    """The guest asked to book: look up the session (a tool call), then stop for a person to approve."""
    yield RunStartedEvent(thread_id=thread_id, run_id=run_id)
    yield from _text(uuid.uuid4().hex[:8], "Let me check tomorrow's kids club.")
    call = uuid.uuid4().hex[:8]
    yield ToolCallStartEvent(tool_call_id=call, tool_call_name="check_availability")
    yield ToolCallArgsEvent(tool_call_id=call, delta=json.dumps({"activity_id": "BR-20261103-kids", "party_size": 2}))
    yield ToolCallEndEvent(tool_call_id=call)
    result = {"available": True, "places_left": 12, "price_total_usd": 0}
    yield ToolCallResultEvent(
        message_id=uuid.uuid4().hex[:8], tool_call_id=call, role="tool", content=json.dumps(result)
    )
    yield StateSnapshotEvent(snapshot={"request": {**SESSION, "status": "AWAITING_APPROVAL"}})
    approval = uuid.uuid4().hex[:12]
    PENDING[approval] = {"thread_id": thread_id, "request": dict(SESSION)}
    yield CustomEvent(name="human_approval_requested",
                      value={"approval_id": approval, "summary": f"{SESSION['activity']}, {SESSION['date']} "
                             f"{SESSION['start']}, party of {SESSION['party']}"})  # fmt: skip
    yield from _text(uuid.uuid4().hex[:8], "It has places. Approve the request below and I'll send it to the desk.")
    yield RunFinishedEvent(thread_id=thread_id, run_id=run_id, result={"awaiting": approval})


def approval_run(approval: str, approve: bool):
    item = PENDING.pop(approval, None)
    run_id = uuid.uuid4().hex[:8]
    if item is None:
        yield RunErrorEvent(message="unknown or already decided approval")
        return
    yield RunStartedEvent(thread_id=item["thread_id"], run_id=run_id)
    yield CustomEvent(name="human_approval_granted" if approve else "human_approval_declined",
                      value={"approval_id": approval})  # fmt: skip
    status = "PENDING_STAFF" if approve else "CANCELLED"
    yield StateDeltaEvent(delta=[{"op": "replace", "path": "/request/status", "value": status}])
    text = ("Sent to the activities desk: PENDING until staff confirm it." if approve
            else "OK, I haven't sent anything.")  # fmt: skip
    yield from _text(uuid.uuid4().hex[:8], text)
    yield RunFinishedEvent(thread_id=item["thread_id"], run_id=run_id, result={"status": status})


def stream(events, request: Request) -> StreamingResponse:
    encoder = EventEncoder(accept=request.headers.get("accept"))
    return StreamingResponse((encoder.encode(e) for e in events), media_type=encoder.get_content_type())


async def agent(request: Request):
    body = await request.json()
    message = (body.get("messages") or [{}])[-1].get("content", "")
    return stream(booking_run(body.get("threadId") or uuid.uuid4().hex[:8], body.get("runId") or uuid.uuid4().hex[:8],
                              message), request)  # fmt: skip


async def approval(request: Request):
    body = await request.json()
    return stream(approval_run(request.path_params["approval_id"], bool(body.get("approve"))), request)


async def page(request: Request):
    return FileResponse(HERE / "index.html")


async def health(request: Request):
    return JSONResponse({"ok": True})


app = Starlette(routes=[Route("/", page), Route("/health", health), Route("/agent", agent, methods=["POST"]),
                        Route("/approval/{approval_id}", approval, methods=["POST"])])  # fmt: skip


def main() -> int:  # pragma: no cover - a server process
    import os

    import uvicorn

    port = int(os.getenv("PORT", "8007"))
    print(f"AG-UI demo on http://127.0.0.1:{port} (Ctrl+C to stop)")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
