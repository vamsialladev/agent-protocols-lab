# 9. AP2: a payment mandate with limits and an explicit approval

Simulated hotel group, synthetic data.

<!-- DEMO-VIDEO -->

## What it shows

The guest's intent, the merchant's signed cart and the guest's signed payment mandate, checked by the concierge and verified by a mock processor. Sandbox only.

## Status and sources

[AP2](https://github.com/google-agentic-commerce/AP2), Google, v0.2.0. The SDK is installed from that tag (commit b4587ac). **The PyPI package named `ap2` belongs to someone else.**

## Guardrails

Prices come from the merchant; the concierge checks the merchant is in the intent, the signature, the expiry, $200 per payment and $300 a day, and holds no key that can authorise. The guest signs. The processor refuses a reused mandate, another key's signature and a payment the approval doesn't cover. Keys are made per run and never leave memory; no money moves.

## What I found

The SDK pins pydantic 2.12.5, cryptography 46.0.5 and pytest at runtime, so it's installed with `--no-deps` (`requirements-nodeps.txt`); its models and JWT helper run on the newer versions.

## Run it

`PYTHONPATH=src python -m demos.ap2.demo` (Windows: `$env:PYTHONPATH="src"` first).

Tests: [`tests/test_ap2.py`](../../tests/test_ap2.py)
