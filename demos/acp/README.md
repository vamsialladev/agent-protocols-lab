# 4. ACP: the same delegation over REST, next to A2A

Simulated hotel group, synthetic data.

<!-- DEMO-VIDEO -->

## What it shows

The guest-email delegation from demo 3 over ACP's REST messaging (`GET /agents`, `POST /runs`, a run that ends completed), with the same result as A2A; and an outline → draft → edit chain of three ACP agents.

## Status and sources

**ACP merged into A2A in August 2025** ([announcement](https://github.com/orgs/i-am-bee/discussions/5)); the [repo](https://github.com/i-am-bee/acp) is archived. SDK: `acp-sdk` 1.0.3 (official, last release). I'd use this only to maintain an existing ACP system.

## Guardrails

Bearer auth as a FastAPI dependency on every route.

## What I found

The archived SDK needs uvicorn 0.35 (0.36 removed a type it imports), its client posts JSON without a Content-Type header that current FastAPI requires, and its app sets up its executor in a lifespan that in-process test clients don't run. All three are worked around in `demo.py`, with comments.

## Run it

`PYTHONPATH=src python -m demos.acp.demo` (Windows: `$env:PYTHONPATH="src"` first).

Tests: [`tests/test_acp.py`](../../tests/test_acp.py)
