# 10. UCP: a mock checkout

Simulated hotel group, synthetic data.

<!-- DEMO-VIDEO -->

## What it shows

The concierge discovers a mock gift shop at `/.well-known/ucp`, creates a checkout session, adds the buyer, reads the
quote, asks the guest, and completes with a sandbox token.

## Status and sources

[UCP](https://ucp.dev), Google and Shopify, dated spec releases. The spec at tag v2026-08-25 (REST binding, status
lifecycle, minor units), and the official SDK, `ucp-sdk` 0.5.0, from
[Universal-Commerce-Protocol/python-sdk](https://github.com/Universal-Commerce-Protocol/python-sdk) at tag
v2026-08-25 (commit b6f9b91c). The SDK isn't on PyPI, so it's installed from that commit's archive. ucp.dev links to
the same GitHub organisation. pip-audit after installing it: nothing new (no advisories for it or its dependencies).

## Two runs, labelled

| Version | What it is | Result |
|---|---|---|
| **Spec-only** (first version) | Request and response shapes written from the spec's examples, before the SDK could be installed | The demo's own flow and tests passed. Validated afterwards against the SDK's models: **6 of 9 checks failed** (3 passed: the create and complete requests) ([run](../../docs/ucp-spec-only-run.md)) |
| **SDK-validated** (now) | Same flow; every request and response validated with the SDK's models during the run, and the run fails if one doesn't conform | **9 of 9 conform** ([run](../../docs/ucp-sdk-run.md)) |

What the SDK caught in the spec-only version, all three fixed:

1. Payment handler keys must be reverse-domain names (`test.hotel-lab.sandbox_token`, not `sandbox_token`), and each
   handler needs a `version`.
2. A completed checkout's `order` needs a `permalink_url`.
3. An update (`PUT`) replaces the session's fields, so it must carry `line_items` again; mine sent only the buyer.

A test keeps the spec-only shapes and checks the SDK still rejects each one.

## Guardrails

Catalog prices only (the agent's `price: 1` is ignored), complete only when `ready_for_complete` and with an
Idempotency-Key (a retry returns the same order), `UCP-Agent` required, only sandbox tokens, the guest confirms the
total first.

## Run it

`PYTHONPATH=src python -m demos.ucp.demo` (Windows: `$env:PYTHONPATH="src"` first).

Tests: [`tests/test_ucp.py`](../../tests/test_ucp.py)
