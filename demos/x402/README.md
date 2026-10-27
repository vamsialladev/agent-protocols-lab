# 11. x402: pay for an API call with HTTP 402

Simulated hotel group, synthetic data.

<!-- DEMO-VIDEO -->

## What it shows

A mock events API answers 402 with `PAYMENT-REQUIRED`; the agent checks the terms, pays, retries with `PAYMENT-SIGNATURE`, and gets the data with a `PAYMENT-RESPONSE` receipt.

## Status and sources

[x402](https://github.com/x402-foundation/x402), x402 Foundation. SDK: `x402` 2.25.0 (official), used for the schemas and header encoding.

## Guardrails

**Fully mocked:** a mock scheme on a mock network, play money, an HMAC voucher. No chain, no testnet, no wallet, no private key. The agent pays only on the mock network (it skips Base mainnet when offered), only allowlisted payees, at most $0.05 a call and $0.20 a session; a voucher works once.

## Run it

`PYTHONPATH=src python -m demos.x402.demo` (Windows: `$env:PYTHONPATH="src"` first).

Tests: [`tests/test_x402.py`](../../tests/test_x402.py)
