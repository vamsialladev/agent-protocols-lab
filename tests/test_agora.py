"""Demo 6: Agora negotiation (scripted), protocol hash, and the structured phase checked against the agreed schema."""

from agora.utils import compute_hash

from demos.agora import demo


def test_prose_then_negotiation_then_structured_messages():
    out = demo.run()
    proto = out["protocol"]
    assert "6 places left" in out["prose"]
    assert proto.metadata["name"] == "tour-availability" and "price_usd" in proto.protocol_document
    assert proto.hash == compute_hash(proto.protocol_document)
    assert out["ok"] == {"status": "success", "body": {"tour_id": "reef-snorkel", "date": "2026-11-03",
                                                        "places_left": 6, "price_usd": 55.0}}  # fmt: skip
    assert out["bad"]["status"] == "error" and "missing party_size" in out["bad"]["body"]
    assert out["unknown"]["body"].startswith("unknown protocol hash")
    turns = [e["side"] for e in out["audit"] if e["event"] == "negotiation_turn"]
    assert turns == ["concierge", "operator", "concierge", "operator"]


def test_the_latest_complete_document_wins_and_either_side_can_accept():
    revised = demo.DRAFT.replace("v1", "v2")
    transcript = [{"from": "concierge", "text": "Here:\n\n" + demo.DRAFT},
                  {"from": "operator", "text": "Changed one thing:\n\n```markdown\n" + revised + "```"},
                  {"from": "concierge", "text": "ACCEPT"}]  # fmt: skip
    assert "v2" in demo.latest_document(transcript)
    assert demo.latest_document([{"from": "operator", "text": "ACCEPT"}]) is None  # nothing to accept


def test_fill_follows_whatever_names_were_agreed():
    schema = {"session_id": "string", "preferred_date": "string", "guests": "integer"}
    assert demo.fill(schema, demo.REQUEST_FACTS) == {"session_id": "reef-snorkel", "preferred_date": "2026-11-03",
                                                     "guests": 2}  # fmt: skip
    assert demo.conforms({"guests": "two"}, schema) == ["missing session_id", "missing preferred_date",
                                                        "guests should be integer"]  # fmt: skip
