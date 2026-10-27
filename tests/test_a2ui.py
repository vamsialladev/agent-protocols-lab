"""Demo 8: A2UI rendering from an allowlist, on top of the official a2ui-core catalog validation."""

import copy

import pytest
from a2ui.core.exceptions import A2uiValidationError

from demos.a2ui import demo

ACTIVITY = {"id": "BR-20261103-kids", "name": "Kids club", "when": "09:30", "price": "Free"}


def messages():
    return copy.deepcopy(demo.booking_card(ACTIVITY))


def with_components(*extra, replace=None):
    m = messages()
    comps = m[1]["updateComponents"]["components"]
    if replace:
        comps[:] = [replace.get(c["id"], c) for c in comps]
    comps.extend(extra)
    return m


def test_the_card_renders_and_a_click_sends_only_the_event():
    out = demo.run()
    assert "<h3>Kids club: sandcastle morning</h3>" in out["html"] and out["html"].count("<button") == 2
    expected = {"name": "request_booking", "surfaceId": "booking_card", "sourceComponentId": "book",
                "context": {"activity_id": "BR-20261103-kids"}}  # fmt: skip
    assert out["click"]["action"] == expected


def test_agent_text_is_escaped():
    m = messages()
    m[2]["updateDataModel"]["value"]["name"] = '<img src=x onerror="alert(1)">'
    html_out = demo.run(m)["html"]
    assert "<img" not in html_out and "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html_out


@pytest.mark.parametrize(
    "bad,why",
    [
        ({"id": "x", "component": "Script", "code": "alert(1)"}, "allowlist"),
        ({"id": "x", "component": "Image", "url": "https://tracker.example/p.png"}, "allowlist"),  # in the catalog
        (
            {
                "id": "x",
                "component": "Button",
                "child": "book_label",
                "action": {"event": {"name": "charge_card", "context": {}}},
            },
            "event",
        ),  # fmt: skip
    ],
)
def test_components_and_events_outside_the_allowlist_are_refused(bad, why):
    with pytest.raises(demo.Refused, match=why):
        demo.run(with_components(bad))


def test_the_official_validator_rejects_a_malformed_allowed_component():
    with pytest.raises(A2uiValidationError):
        demo.run(with_components({"id": "x", "component": "Text", "text": 42, "onclick": "steal()"}))


def test_tree_problems_and_protocol_problems_are_refused():
    cycle = {"body": {"id": "body", "component": "Column", "children": ["title", "body"]}}
    with pytest.raises(demo.Refused, match="cycle"):
        demo.run(with_components(replace=cycle))
    missing = {"actions": {"id": "actions", "component": "Row", "children": ["book", "ghost"]}}
    with pytest.raises(demo.Refused, match="missing component 'ghost'"):
        demo.run(with_components(replace=missing))
    m = messages()
    m[0]["createSurface"]["catalogId"] = "https://evil.example/catalog.json"
    with pytest.raises(demo.Refused, match="unknown catalog"):
        demo.run(m)
    m = messages()
    m[1]["deleteSurface"] = {"surfaceId": "booking_card"}
    with pytest.raises(demo.Refused, match="exactly one"):
        demo.run(m)
