"""Demo 5: ANP (Agent Network Protocol, official `anp` 1.0.7). Two agents with locally generated did:wba identities
authenticate and exchange signed messages, with no central server or registry.

- Each agent makes its own DID document and Ed25519 key (`create_did_wba_document`). The DID ends in a fingerprint of
  the key (the "e1" profile), so a document with someone else's key under that DID fails the binding check.
- The concierge calls the partner tour operator with a DIDWba auth header (`generate_auth_header`) made for that
  operator's domain; the operator resolves the DID, checks the binding and verifies the header for its own domain.
- The message body is signed too, with a nonce and timestamp: the operator rejects a changed body, a reused nonce
  and anything older than 5 minutes. The reply comes back signed the same way.

**Local and test only:** did:wba resolves a DID by fetching `https://<domain>/.../did.json` from the agent's own
domain. Here that fetch is a local dictionary (`DIRECTORY`), and the domains end in .test.

    python -m demos.anp.demo
"""

import base64
import json
import secrets
import sys
import time
from dataclasses import dataclass, field

from anp.authentication.did_wba import (
    create_did_wba_document,
    extract_auth_header_parts,
    generate_auth_header,
    validate_did_document_binding,
    verify_auth_header_signature,
)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from protolab.audit import Audit

MAX_AGE_S = 300
DIRECTORY: dict[str, dict] = {}  # stands in for each domain's own https://.../did.json


class Rejected(PermissionError):
    pass


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def public_key(doc: dict) -> Ed25519PublicKey:
    """The Ed25519 key the DID document lists for authentication (Multikey, multibase base58btc 'z...')."""
    import base58  # anp depends on it

    auth_id = doc["authentication"][0]
    vm = next(v for v in doc["verificationMethod"] if v["id"] == auth_id)
    raw = base58.b58decode(vm["publicKeyMultibase"][1:])
    return Ed25519PublicKey.from_public_bytes(raw[2:])  # strip the multicodec prefix 0xed01


@dataclass
class Agent:
    name: str
    domain: str
    audit: Audit
    doc: dict = field(init=False)
    keys: dict = field(init=False)
    seen_nonces: set = field(default_factory=set)

    def __post_init__(self):
        self.doc, self.keys = create_did_wba_document(self.domain, path_segments=["agents", self.name])
        DIRECTORY[self.doc["id"]] = self.doc  # "publish" on its own domain
        self.audit.record(self.name, "did_created", did=self.doc["id"])

    @property
    def did(self) -> str:
        return self.doc["id"]

    def _sign(self, content: bytes, fragment: str = "key-1") -> bytes:
        return load_pem_private_key(self.keys[fragment.split("#")[-1]][0], password=None).sign(content)

    def envelope(self, to: "Agent", body: dict) -> tuple[str, dict]:
        header = generate_auth_header(self.doc, to.domain, self._sign)
        msg = {"from": self.did, "to": to.did, "nonce": secrets.token_hex(16), "ts": time.time(), "body": body}
        signed = {**msg, "sig": base64.urlsafe_b64encode(self._sign(canonical(msg))).decode().rstrip("=")}
        self.audit.record(self.name, "sent", to=to.name, nonce=msg["nonce"])
        return header, signed

    def verify(self, header: str, signed: dict, now: float | None = None) -> dict:
        did = extract_auth_header_parts(header)[0]
        doc = DIRECTORY.get(did)
        if doc is None:
            raise Rejected("unknown DID")
        if not validate_did_document_binding(doc):
            raise Rejected("DID document isn't bound to the DID's key")
        ok, why = verify_auth_header_signature(header, doc, self.domain)
        if not ok:
            raise Rejected(f"auth header: {why}")
        msg = {k: v for k, v in signed.items() if k != "sig"}
        if msg["from"] != did or msg["to"] != self.did:
            raise Rejected("message isn't from the authenticated DID to me")
        try:
            public_key(doc).verify(_b64url_decode(signed["sig"]), canonical(msg))
        except Exception as exc:  # noqa: BLE001 - any verification failure is a rejection
            raise Rejected("message signature doesn't match") from exc
        if (now or time.time()) - msg["ts"] > MAX_AGE_S:
            raise Rejected("message too old")
        if msg["nonce"] in self.seen_nonces:
            raise Rejected("replayed nonce")
        self.seen_nonces.add(msg["nonce"])
        self.audit.record(self.name, "verified", sender=did, nonce=msg["nonce"])
        return msg["body"]


def tour_operator_reply(body: dict) -> dict:
    places = {"reef-snorkel-2026-11-03": 6}
    return {"tour": body["tour"], "places_left": places.get(body["tour"], 0), "hold": "none (staff confirm)"}


def run() -> dict:
    DIRECTORY.clear()
    audit = Audit()
    concierge = Agent("concierge", "concierge.hotel.test", audit)
    tours = Agent("tours", "tours.partner.test", audit)
    header, signed = concierge.envelope(tours, {"ask": "availability", "tour": "reef-snorkel-2026-11-03"})
    body = tours.verify(header, signed)
    rh, reply = tours.envelope(concierge, tour_operator_reply(body))
    answer = concierge.verify(rh, reply)
    rejected = {}
    try:
        tours.verify(header, signed)
    except Rejected as exc:
        rejected["replay"] = str(exc)
    h2, s2 = concierge.envelope(tours, {"ask": "availability", "tour": "reef-snorkel-2026-11-03"})
    try:
        tours.verify(h2, {**s2, "body": {"ask": "book", "tour": "reef-snorkel-2026-11-03", "party": 20}})
    except Rejected as exc:
        rejected["tampered"] = str(exc)
    return {"concierge": concierge.did, "tours": tours.did, "answer": answer, "rejected": rejected,
            "audit": audit.events}  # fmt: skip


def main() -> int:
    out = run()
    print("concierge:", out["concierge"][:60] + "...")
    print("tours:    ", out["tours"][:60] + "...")
    print("reply (verified):", out["answer"])
    for k, v in out["rejected"].items():
        print(f"rejected {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
