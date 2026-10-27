# 7. AG-UI: an agent run streamed to a web page

Simulated hotel group, synthetic data.

<!-- DEMO-VIDEO -->

## What it shows

A Starlette backend streams AG-UI events over SSE to a small page: text, a tool call with its result, a state snapshot, and a pause for a human approval. Approve or Decline starts a second run that updates the state with a JSON Patch.

## Status and sources

[AG-UI](https://github.com/ag-ui-protocol/ag-ui), active. SDK: `ag-ui-protocol` 1.0 (official), including its `EventEncoder`.

## Guardrails

The page builds the DOM with `textContent` only; an approval ID can be decided once.

## What I found

Checked in a browser: 48 events, the approval card, the state after Approve, no console errors.

## Run it

`PYTHONPATH=src python -m demos.ag_ui.demo`, then open http://127.0.0.1:8007 (`PORT` changes it).

Tests: [`tests/test_ag_ui.py`](../../tests/test_ag_ui.py)
