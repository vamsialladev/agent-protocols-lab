"""One audit log for every demo: each event gets the run's trace ID, a timestamp and the actor, and secrets are masked
before anything is kept. Demos print it at the end, and tests read it to check what happened, in order."""

import json
import re
import time
import uuid
from dataclasses import dataclass, field

SECRET = re.compile(r"(?:sk-ant-|hmcp_|Bearer\s+)[A-Za-z0-9_\-\.]{6,}")


def new_trace_id() -> str:
    return uuid.uuid4().hex


def mask(value):
    if isinstance(value, str):
        return SECRET.sub("[secret]", value)
    if isinstance(value, dict):
        return {k: mask(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [mask(v) for v in value]
    return value


@dataclass
class Audit:
    trace_id: str = field(default_factory=new_trace_id)
    events: list = field(default_factory=list)

    def record(self, actor: str, event: str, **detail) -> dict:
        row = {"trace_id": self.trace_id, "ts": round(time.time(), 3), "actor": actor, "event": event,
               **mask(detail)}  # fmt: skip
        self.events.append(row)
        return row

    def names(self) -> list[str]:
        return [e["event"] for e in self.events]

    def dump(self) -> str:
        return "\n".join(json.dumps(e, ensure_ascii=False, default=str) for e in self.events)
