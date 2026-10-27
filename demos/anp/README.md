# 5. ANP: decentralised identity and signed messages

Simulated hotel group, synthetic data.

<!-- DEMO-VIDEO -->

## What it shows

Two agents (the concierge and a partner tour operator) each make a did:wba identity and an Ed25519 key locally, authenticate with DIDWba headers made for the other's domain, and exchange signed messages with no central server.

## Status and sources

[ANP](https://github.com/agent-network-protocol/AgentNetworkProtocol), community project, active. SDK: `anp` 1.0.7 (official).

## Guardrails

The DID ends in a fingerprint of its key, so a document with another key under that DID fails the binding check. Headers are bound to the receiver's domain. Bodies are signed with a nonce and a timestamp: a changed body, a reused nonce and anything older than 5 minutes are refused.

**Local and test only.** did:wba resolves a DID by fetching a document from the agent's own HTTPS domain; here that fetch is a local dictionary and the domains end in .test.

## Run it

`PYTHONPATH=src python -m demos.anp.demo` (Windows: `$env:PYTHONPATH="src"` first).

Tests: [`tests/test_anp.py`](../../tests/test_anp.py)
