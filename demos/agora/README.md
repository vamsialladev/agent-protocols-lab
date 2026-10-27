# 6. Agora: negotiate a format, then switch to it

Simulated hotel group, synthetic data.

<!-- DEMO-VIDEO -->

## What it shows

Two agents start in plain language, negotiate a protocol document (front matter plus request and response schemas), then send only `{protocolHash, body}` messages that are checked against the agreed schema.

## Status and sources

[Agora](https://arxiv.org/abs/2410.11905) (Marro et al., 2024), research library `agora-protocol` 0.2.0. Used for what it standardises: `Protocol`, `compute_hash` and the wire fields.

## Guardrails

The package's own negotiator and programmer are LangChain conversations, and the programmer writes Python routines that it runs with RestrictedPython. **This demo never runs generated code**; the negotiation is a small loop of my own, and bodies are validated against the agreed schema.

## What I found

Run live once with Claude Haiku 5.5 (`--live`): the model concierge proposed a `boolean` field the format doesn't allow, the model operator fixed it, and the concierge accepted. About $0.0005 ([log](../../docs/agora-live-run.txt)). My first version assumed the accepted document was in the concierge's last message; the live run proved it wrong, so the document is now the latest complete one in the conversation.

## Run it

`PYTHONPATH=src python -m demos.agora.demo` (Windows: `$env:PYTHONPATH="src"` first).

Tests: [`tests/test_agora.py`](../../tests/test_agora.py)
