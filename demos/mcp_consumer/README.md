# 2. MCP consumer: three servers behind one gateway

Simulated hotel group, synthetic data.

<!-- DEMO-VIDEO -->

## What it shows

One agent uses three MCP servers at once: hotel-tools-mcp (guest role), the official filesystem server, and
Microsoft's Playwright server. It prepares tomorrow's activity brief from all three.

## Status and sources

| Server | Package (exact version) | Provenance (checked 2026-10-27) |
|---|---|---|
| Filesystem | `@modelcontextprotocol/server-filesystem@1.0.0`, published 2026-10-11 | npm provenance: built by GitHub Actions from [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers), `release.yml`, tag `v1.0.0` |
| Playwright | `@playwright/mcp@0.0.83`, published 2026-09-28 | npm provenance: built by GitHub Actions from [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), `publish.yml` |
| Hotel tools | hotel-tools-mcp, commit 53ea634 | this portfolio's stage 7 server |

Both npm versions were older than two weeks when chosen; `npx -y <package>@<version>` runs exactly that version
(npm resolves its own dependencies at run time).

## Guardrails

Two fences.

1. **Each server's own settings.** The filesystem server's only root is a fresh folder inside the lab,
   `.mcp-sandbox/run-<id>/` (git-ignored), holding copies of the synthetic brochure; it's deleted after the run.
   Playwright runs `--headless --isolated` (a fresh in-memory profile: no saved logins or cookies) with
   `--allowed-origins` set to a synthetic page served on 127.0.0.1.
2. **The gateway.** It exposes only allowlisted tools (`list_allowed_directories`, `list_directory`,
   `read_text_file`; `browser_navigate`, `browser_snapshot`; no `write_file`, no `browser_run_code_unsafe` or
   `browser_evaluate`), checks every URL against an origin allowlist, and audits every call, allowed or refused.

## Live run (2026-10-27, Windows 11, Node 24.22.1, npx 11.19.1, Python 3.12.10)

Command: `PYTHONPATH=src python -m demos.mcp_consumer.demo`. Full output: [docs/mcp-consumer-live-run.txt](../../docs/mcp-consumer-live-run.txt).

| Check | Result |
|---|---|
| Tools exposed through the gateway | hotel 2, files 3, browser 2 (all others hidden) |
| Filesystem server's own answer to `list_allowed_directories` | only `...\agent-protocols-lab\.mcp-sandbox\run-e05f2c0b` |
| Read of the lab's README (outside the root), an allowed tool | refused by the server: "Access denied - path outside allowed directories" |
| Brochure read from the sandbox | the synthetic kids club line |
| Playwright on the local page | page loaded and read; the local server logged one request, `GET /events.html` |
| `write_file`, `browser_run_code_unsafe`, `https://example.com` | refused by the gateway; never reached a server |
| Sandbox afterwards | still only the copied brochure (nothing written), then removed |
| Playwright's own snapshots (`.playwright-mcp/`, git-ignored) | two files, one per run, each only the synthetic events page |

The live test (`LAB_NPX=1 pytest tests/test_mcp_consumer.py`) checks the same points and passed on the same day.
CI runs the gateway tests with fake sessions (no Node, no browser there).

## What I found

The Playwright server offers `browser_run_code_unsafe` and `browser_evaluate`: a reason the allowlist is on the
client, not just the server's flags. The filesystem server refused the out-of-root read on its own, so the two
fences really are independent.

## Run it

`PYTHONPATH=src python -m demos.mcp_consumer.demo` (Windows: `$env:PYTHONPATH="src"` first). Needs Node.js and Chrome.

Tests: [`tests/test_mcp_consumer.py`](../../tests/test_mcp_consumer.py)
