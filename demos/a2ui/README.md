# 8. A2UI: a declarative booking card, rendered from an allowlist

Simulated hotel group, synthetic data.

<!-- DEMO-VIDEO -->

## What it shows

The agent sends A2UI v0.9.1 messages (`createSurface`, `updateComponents` as an adjacency list, `updateDataModel`) for an activity booking card; the client renders HTML and sends back only the event a button names.

## Status and sources

A2UI v0.9.1 is the current production spec; v1.0 is a draft ([a2ui-project/a2ui](https://github.com/a2ui-project/a2ui)). SDK: `a2ui-core` 0.3.0 (official, released from that repo; pinned to a version older than two weeks). When I first checked, there was no Python package; there is now.

## Guardrails

The official validator checks every component against the basic catalog; then a narrower allowlist (Column, Row, Card, Text, Divider, Button: no Image, Video or inputs), HTML escaping, named events only, and tree checks (one root, no missing children, no cycles, 8 levels at most).

## Run it

`PYTHONPATH=src python -m demos.a2ui.demo` (Windows: `$env:PYTHONPATH="src"` first).

Tests: [`tests/test_a2ui.py`](../../tests/test_a2ui.py)
