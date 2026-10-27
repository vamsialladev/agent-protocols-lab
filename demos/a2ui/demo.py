"""Demo 8: A2UI (v0.9.1, the current production spec). The agent returns a declarative UI, an activity booking card,
as A2UI messages; the client renders it from an allowlist and runs no code from the agent.

Two fences on the client:
1. The official `a2ui-core` 0.3.0 validator checks every component against the v0.9 basic catalog (an unknown
   component like "Script" is rejected there).
2. This renderer's own allowlist is narrower than the catalog: Column, Row, Card, Text, Divider, Button. No Image,
   Video, Modal or text inputs, so the agent can't load a URL or ask for typed data. Every string is HTML-escaped,
   a Button can only fire an event named in ALLOWED_EVENTS, and the component tree is checked (one root, no
   missing children, no cycles, at most 8 levels deep).

    python -m demos.a2ui.demo        writes demos/a2ui/card.html and prints the event a button would send
"""

import html
import json
import sys
from pathlib import Path

from a2ui.core.basic_catalog import BasicCatalog
from a2ui.core.validation.payload_validator import STRICT_VALIDATION, PayloadValidator

from protolab.audit import Audit

VERSION = "v0.9.1"
CATALOG_ID = "https://a2ui.org/specification/v0_9_1/catalogs/basic/catalog.json"
ALLOWED_COMPONENTS = {"Column", "Row", "Card", "Text", "Divider", "Button"}
ALLOWED_EVENTS = {"request_booking", "show_other_times"}
MAX_DEPTH = 8
HERE = Path(__file__).resolve().parent


class Refused(ValueError):
    pass


def booking_card(activity: dict) -> list[dict]:
    """What the agent sends: create the surface, its components (an adjacency list), then the data they bind to."""
    sid = "booking_card"
    components = [
        {"id": "root", "component": "Card", "child": "body"},
        {"id": "body", "component": "Column", "children": ["title", "when", "price", "rule", "actions"]},
        {"id": "title", "component": "Text", "text": {"path": "/activity/name"}, "variant": "h3"},
        {"id": "when", "component": "Text", "text": {"path": "/activity/when"}},
        {"id": "price", "component": "Text", "text": {"path": "/activity/price"}},
        {"id": "rule", "component": "Divider"},
        {"id": "actions", "component": "Row", "children": ["book", "other"]},
        {"id": "book", "component": "Button", "child": "book_label", "variant": "primary",
         "action": {"event": {"name": "request_booking", "context": {"activity_id": activity["id"]}}}},
        {"id": "book_label", "component": "Text", "text": "Request booking"},
        {"id": "other", "component": "Button", "child": "other_label",
         "action": {"event": {"name": "show_other_times", "context": {"activity_id": activity["id"]}}}},
        {"id": "other_label", "component": "Text", "text": "Other times"},
    ]  # fmt: skip
    return [
        {"version": VERSION, "createSurface": {"surfaceId": sid, "catalogId": CATALOG_ID}},
        {"version": VERSION, "updateComponents": {"surfaceId": sid, "components": components}},
        {"version": VERSION, "updateDataModel": {"surfaceId": sid, "path": "/activity", "value": {
            "name": activity["name"], "when": activity["when"], "price": activity["price"]}}},
    ]  # fmt: skip


class Surface:
    def __init__(self, validator: PayloadValidator):
        self.validator, self.components, self.data, self.catalog = validator, {}, {}, None

    def apply(self, message: dict) -> None:
        kinds = [k for k in ("createSurface", "updateComponents", "updateDataModel", "deleteSurface") if k in message]
        if len(kinds) != 1 or message.get("version") != VERSION:
            raise Refused("a message must have the version and exactly one A2UI message type")
        body = message[kinds[0]]
        if kinds[0] == "createSurface":
            if body.get("catalogId") != CATALOG_ID:
                raise Refused("unknown catalog")
            self.catalog = body["catalogId"]
        elif self.catalog is None:
            raise Refused("surface not created")
        elif kinds[0] == "updateComponents":
            for comp in body["components"]:
                if comp.get("component") not in ALLOWED_COMPONENTS:
                    raise Refused(f"component {comp.get('component')!r} isn't on this renderer's allowlist")
                self.validator.validate_component(comp)  # the official catalog check (raises A2uiValidationError)
                event = (comp.get("action") or {}).get("event", {}).get("name")
                if comp["component"] == "Button" and event not in ALLOWED_EVENTS:
                    raise Refused(f"button event {event!r} isn't allowed")
                self.components[comp["id"]] = comp
        elif kinds[0] == "updateDataModel":
            keys = [k for k in body.get("path", "/").split("/") if k]
            target = self.data
            for k in keys[:-1]:
                target = target.setdefault(k, {})
            if keys:
                target[keys[-1]] = body.get("value")
            else:
                self.data = body.get("value") or {}
        else:
            self.components, self.data, self.catalog = {}, {}, None

    def _value(self, v) -> str:
        if isinstance(v, dict) and "path" in v:
            node = self.data
            for k in [k for k in v["path"].split("/") if k]:
                node = node.get(k, "") if isinstance(node, dict) else ""
            return str(node)
        return str(v)

    def render(self) -> str:
        if "root" not in self.components:
            raise Refused("no root component")
        return self._render("root", set(), 0)

    def _render(self, cid: str, seen: set, depth: int) -> str:
        if depth > MAX_DEPTH or cid in seen:
            raise Refused("component tree too deep or has a cycle")
        comp = self.components.get(cid)
        if comp is None:
            raise Refused(f"missing component {cid!r}")
        seen = seen | {cid}
        kind = comp["component"]
        kids = comp.get("children") or ([comp["child"]] if comp.get("child") else [])
        inner = "".join(self._render(k, seen, depth + 1) for k in kids)
        if kind == "Text":
            tag = "h3" if comp.get("variant") in ("h1", "h2", "h3") else "p"
            return f"<{tag}>{html.escape(self._value(comp.get('text', '')))}</{tag}>"
        if kind == "Divider":
            return "<hr>"
        if kind == "Button":
            ev = comp["action"]["event"]
            payload = html.escape(json.dumps({"name": ev["name"], "context": ev.get("context", {})}), quote=True)
            cls = "primary" if comp.get("variant") == "primary" else "secondary"
            return f'<button type="button" class="{cls}" data-a2ui-event="{payload}">{inner}</button>'
        css = {"Card": "a2ui-card", "Column": "a2ui-column", "Row": "a2ui-row"}[kind]
        return f'<div class="{css}">{inner}</div>'

    def event(self, button_id: str) -> dict:
        """What a click sends back to the agent: the event name and context, nothing else (client-to-server)."""
        ev = self.components[button_id]["action"]["event"]
        action = {"name": ev["name"], "surfaceId": "booking_card", "sourceComponentId": button_id,
                  "context": ev.get("context", {})}  # fmt: skip
        return {"version": VERSION, "action": action}


def run(messages=None) -> dict:
    audit = Audit()
    activity = {"id": "BR-20261103-kids", "name": "Kids club: sandcastle morning",
                "when": "Tuesday 3 November, 09:30-11:30, ages 4-11", "price": "Free for resident guests"}  # fmt: skip
    surface = Surface(PayloadValidator(BasicCatalog("v0.9"), STRICT_VALIDATION))
    for m in messages or booking_card(activity):
        surface.apply(m)
        audit.record("client", "applied", type=next(k for k in m if k != "version"))
    page = surface.render()
    audit.record("client", "rendered", chars=len(page))
    return {"html": page, "click": surface.event("book"), "surface": surface, "audit": audit.events}


def main() -> int:
    out = run()
    doc = ("<!doctype html><meta charset='utf-8'><title>A2UI card</title><style>body{font:16px system-ui;padding:16px}"
           ".a2ui-card{border:1px solid #e3ddd2;border-radius:12px;padding:12px;max-width:420px}"
           ".a2ui-row{display:flex;gap:8px}button{border-radius:8px;padding:6px 12px}</style>"
           + out["html"])  # fmt: skip
    (HERE / "card.html").write_text(doc, encoding="utf-8")
    print(out["html"])
    print("Request booking sends:", json.dumps(out["click"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
