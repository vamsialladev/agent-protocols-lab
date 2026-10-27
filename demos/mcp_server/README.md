# 1. MCP server: a client calling hotel-tools-mcp

Simulated hotel group, synthetic data.

<!-- DEMO-VIDEO -->

## What it shows

A Python MCP client starts the stage 7 [hotel-tools-mcp](https://github.com/vamsialladev/hotel-tools-mcp) server as a separate stdio process, the way any MCP host does, once as a guest and once as front desk. Each role sees only its tools (4 vs 5); calling a tool the guest doesn't have is refused.

## Status and sources

MCP is the most widely used of these protocols. SDK: `mcp` 2.3 (official). Spec: [modelcontextprotocol.io](https://modelcontextprotocol.io).

## Guardrails

One process serves one API key, so the role can't change mid-session. Keys are made fresh per run in a temporary folder; only their SHA-256 hashes are stored.

## What I found

Starting the server from a fresh install, its first search printed a progress line to stdout, which over stdio is the protocol stream. Fixed in hotel-tools-mcp (decision 14).

## Run it

`PYTHONPATH=src python -m demos.mcp_server.demo` (Windows: `$env:PYTHONPATH="src"` first).

Tests: [`tests/test_mcp_server.py`](../../tests/test_mcp_server.py)
