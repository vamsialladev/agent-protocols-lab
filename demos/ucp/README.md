# 10. UCP: a mock checkout

Simulated hotel group, synthetic data.

<!-- DEMO-VIDEO -->

## What it shows

The concierge discovers a mock gift shop at `/.well-known/ucp`, creates a checkout session, adds the buyer, reads the quote, asks the guest, and completes with a sandbox token.

## Status and sources

[UCP](https://ucp.dev), Google and Shopify, dated spec releases. Written from the spec at tag v2026-08-25 (REST binding, status lifecycle, minor units). **Not the SDK:** `ucp-sdk` isn't on PyPI and installing it from GitHub was blocked in this environment.

## Guardrails

Catalog prices only (the agent's `price: 1` is ignored), complete only when `ready_for_complete` and with an Idempotency-Key (a retry returns the same order), `UCP-Agent` required, only sandbox tokens, the guest confirms the total first.

## Run it

`PYTHONPATH=src python -m demos.ucp.demo` (Windows: `$env:PYTHONPATH="src"` first).

Tests: [`tests/test_ucp.py`](../../tests/test_ucp.py)
