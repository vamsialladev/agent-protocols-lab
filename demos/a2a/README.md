# 3. A2A: delegation and two agents working together

Simulated hotel group, synthetic data.

<!-- DEMO-VIDEO -->

## What it shows

(1) The concierge reads the guest-email agent's card (skill, bearer auth), sends one guest email, and gets a task that goes working → completed with a data artifact (requests, staff tasks, a draft for review). (2) A reader agent turns a brochure into facts; an ideas agent turns the facts into ideas; the concierge only passes artifacts between them.

## Status and sources

A2A is Google's protocol, now under the Linux Foundation ([a2aproject/A2A](https://github.com/a2aproject/A2A)). SDK: `a2a-sdk` 1.2.3 (official). The real stage 2 agent serves the same protocol with Claude (guest-request-agent, `src/a2a_server.py`).

## Guardrails

Bearer token on everything but the public card, compared in constant time; a failed task returns a safe message, never a stack trace. The agents here are rule-based stand-ins so it runs free.

## Run it

`PYTHONPATH=src python -m demos.a2a.demo` (Windows: `$env:PYTHONPATH="src"` first).

Tests: [`tests/test_a2a.py`](../../tests/test_a2a.py)
