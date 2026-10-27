"""Demo 5: ANP did:wba identities, auth headers and signed messages, locally."""

import time

import pytest

from demos.anp import demo
from protolab.audit import Audit


def test_two_agents_authenticate_and_exchange_signed_messages():
    out = demo.run()
    assert out["concierge"].startswith("did:wba:concierge.hotel.test:") and ":e1_" in out["concierge"]
    assert out["answer"]["places_left"] == 6
    assert out["rejected"] == {"replay": "replayed nonce", "tampered": "message signature doesn't match"}


@pytest.fixture
def pair():
    demo.DIRECTORY.clear()
    audit = Audit()
    return demo.Agent("concierge", "concierge.hotel.test", audit), demo.Agent("tours", "tours.partner.test", audit)


def test_a_header_made_for_another_domain_is_refused(pair):
    concierge, tours = pair
    other = demo.Agent("spa", "spa.partner.test", concierge.audit)
    header, signed = concierge.envelope(other, {"ask": "x"})
    with pytest.raises(demo.Rejected, match="auth header"):
        tours.verify(header, {**signed, "to": tours.did})


def test_unknown_did_and_a_forged_document_are_refused(pair):
    concierge, tours = pair
    header, signed = concierge.envelope(tours, {"ask": "x"})
    real = demo.DIRECTORY.pop(concierge.did)
    with pytest.raises(demo.Rejected, match="unknown DID"):
        tours.verify(header, signed)
    forged, _ = demo.create_did_wba_document("concierge.hotel.test", path_segments=["agents", "concierge"])
    demo.DIRECTORY[concierge.did] = {**forged, "id": real["id"]}  # someone else's key under the concierge's DID
    with pytest.raises(demo.Rejected, match="isn't bound"):
        tours.verify(header, signed)


def test_a_stale_message_is_refused(pair):
    concierge, tours = pair
    header, signed = concierge.envelope(tours, {"ask": "x"})
    with pytest.raises(demo.Rejected, match="too old"):
        tours.verify(header, signed, now=time.time() + demo.MAX_AGE_S + 1)
