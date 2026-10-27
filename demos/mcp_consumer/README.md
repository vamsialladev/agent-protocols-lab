# 2. MCP consumer: three servers behind one gateway

Simulated hotel group, synthetic data.

<!-- DEMO-VIDEO -->

## What it shows

One agent uses three MCP servers at once: hotel-tools-mcp (guest role), the official filesystem server rooted at a folder of brochures, and Microsoft's Playwright server, headless and isolated, allowed to open only a local test page. It prepares tomorrow's activity brief from all three.

## Status and sources

Servers pinned: `@modelcontextprotocol/server-filesystem@1.0.0` (2026-10-11) and `@playwright/mcp@0.0.83` (2026-09-28), both older than two weeks when chosen.

## Guardrails

Two fences. Each server's own settings (the filesystem root, Playwright's `--allowed-origins`), and a gateway that exposes only allowlisted tools (no `write_file`, no `browser_run_code_unsafe` or `browser_evaluate`), checks every URL against an origin allowlist, and audits every call, allowed or refused.

**Not run live in this environment** (the permission check blocked starting the npm servers). The gateway is tested with fake sessions; `LAB_NPX=1 pytest tests/test_mcp_consumer.py` runs it live.

## What I found

The Playwright server offers `browser_run_code_unsafe` and `browser_evaluate`: a reason the allowlist is on the client, not just the server's flags.

## Run it

`PYTHONPATH=src python -m demos.mcp_consumer.demo` (Windows: `$env:PYTHONPATH="src"` first).

Tests: [`tests/test_mcp_consumer.py`](../../tests/test_mcp_consumer.py)
