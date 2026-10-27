"""A function becomes an A2A agent (official a2a-sdk 1.2): agent card, bearer auth, task lifecycle, one data artifact.

    app = agent_app("Guest email agent", "handle_guest_email", "...", handler, token="...")
    out = await send(app, {"body": "..."}, token="...")       # in-process, over httpx's ASGI transport

The same app runs as a real server with uvicorn. The handler gets the message's data part (a dict) and returns a
dict; an exception fails the task with a safe message, never a stack trace.
"""

import asyncio
import hmac
import json

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_data_parts, new_data_message, new_task_from_user_message, new_text_message
from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    HTTPAuthSecurityScheme,
    Part,
    Role,
    SecurityRequirement,
    SecurityScheme,
    SendMessageRequest,
    StringList,
    TaskState,
)
from google.protobuf import struct_pb2
from google.protobuf.json_format import MessageToDict
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

CARD_PATH = "/.well-known/agent-card.json"


def card(name: str, skill_id: str, description: str, url: str) -> AgentCard:
    return AgentCard(
        name=name,
        description=description + " Simulated hotel group, synthetic data.",
        version="0.1.0",
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        capabilities=AgentCapabilities(streaming=False),
        supported_interfaces=[AgentInterface(protocol_binding="JSONRPC", url=url, protocol_version="1.0")],
        skills=[AgentSkill(id=skill_id, name=skill_id.replace("_", " "), description=description, tags=["hotel"])],
        security_schemes={"bearer": SecurityScheme(http_auth_security_scheme=HTTPAuthSecurityScheme(scheme="bearer"))},
        security_requirements=[SecurityRequirement(schemes={"bearer": StringList()})],
    )


class FunctionExecutor(AgentExecutor):
    def __init__(self, handler):
        self.handler = handler

    async def execute(self, context, event_queue) -> None:
        task = context.current_task or new_task_from_user_message(context.message)
        if not context.current_task:
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue=event_queue, task_id=task.id, context_id=task.context_id)
        await updater.update_status(state=TaskState.TASK_STATE_WORKING, message=new_text_message("Working"))
        data = next(iter(get_data_parts(context.message.parts)), None)
        try:
            result = await asyncio.to_thread(self.handler, data if isinstance(data, dict) else {})
        except Exception:  # noqa: BLE001 - another agent gets a safe message, never a stack trace
            await updater.update_status(state=TaskState.TASK_STATE_FAILED, message=new_text_message("Failed."))
            return
        payload = struct_pb2.Struct()
        payload.update(json.loads(json.dumps(result, default=str)))
        await updater.add_artifact(parts=[Part(data=struct_pb2.Value(struct_value=payload))], name="result")
        await updater.update_status(state=TaskState.TASK_STATE_COMPLETED, message=new_text_message("Done."))

    async def cancel(self, context, event_queue) -> None:  # pragma: no cover - tasks take milliseconds
        raise NotImplementedError


class BearerAuth(BaseHTTPMiddleware):
    def __init__(self, app, token: str):
        super().__init__(app)
        self.token = token

    async def dispatch(self, request, call_next):
        if request.url.path == CARD_PATH:  # the card is public: it says how to authenticate
            return await call_next(request)
        given = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        if not self.token or not hmac.compare_digest(given.encode(), self.token.encode()):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def agent_app(name: str, skill_id: str, description: str, handler, token: str, url: str) -> Starlette:
    c = card(name, skill_id, description, url)
    rh = DefaultRequestHandler(agent_executor=FunctionExecutor(handler), task_store=InMemoryTaskStore(), agent_card=c)
    app = Starlette(routes=[*create_agent_card_routes(c), *create_jsonrpc_routes(rh, "/")])
    app.add_middleware(BearerAuth, token=token)
    return app


async def send(app, data: dict, token: str, url: str) -> dict:
    """One message to an in-process agent. Returns {"card", "states", "state", "artifact"}."""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=url, headers=headers) as http:
        agent_card = await A2ACardResolver(httpx_client=http, base_url=url).get_agent_card()
        client = await create_client(agent=agent_card, client_config=ClientConfig(streaming=False, httpx_client=http))
        try:
            request = SendMessageRequest(message=new_data_message(data, role=Role.ROLE_USER))
            events = [MessageToDict(e[0] if isinstance(e, tuple) else e) async for e in client.send_message(request)]
        finally:
            await client.close()
    task = next((e["task"] for e in reversed(events) if "task" in e), {})
    artifact = next((p["data"] for a in task.get("artifacts", []) for p in a.get("parts", []) if "data" in p), None)
    return {"card": MessageToDict(agent_card), "state": task.get("status", {}).get("state"), "artifact": artifact,
            "history": [m.get("parts", [{}])[0].get("text") for m in task.get("history", [])]}  # fmt: skip
