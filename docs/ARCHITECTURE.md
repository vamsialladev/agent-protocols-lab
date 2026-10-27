# Architecture

## Layers

```mermaid
flowchart LR
  subgraph UI
    AGUI[AG-UI 7]
    A2UI[A2UI 8]
  end
  subgraph Agents[Agent to agent]
    A2A[A2A 3]
    ACP[ACP 4]
    AGORA[Agora 6]
  end
  subgraph Net[Network and identity]
    ANP[ANP 5]
  end
  subgraph Tools[Tools and data]
    MCP1[MCP server 1]
    MCP2[MCP consumer 2]
  end
  subgraph Pay[Payments and commerce]
    AP2[AP2 9]
    UCP[UCP 10]
    X402[x402 11]
  end
  UI --> Agents --> Tools
  Agents --> Pay
  Agents -.-> Net
```

## Components

| Component | What it does |
|---|---|
| `src/protolab/audit.py` | One audit log per run: trace ID, actor, event, secrets masked |
| `src/protolab/a2a_kit.py` | A function becomes an A2A agent (card, bearer auth, task lifecycle, one artifact); used by demos 3 and 4 |
| `demos/<name>/demo.py` | One demo: `main()` prints what happened; a function the tests call returns it |
| `demos/<name>/README.md` | Status, sources, guardrails, what I found |
| `tests/test_<name>.py` | The normal path, each refusal, and a control case |
| `data/` | Synthetic brochure and events page |

## How a demo runs

Everything is in-process unless the protocol is about processes: demo 1 starts hotel-tools-mcp as a real stdio
subprocess, demo 2 starts npm servers. HTTP protocols (A2A, ACP, AG-UI, UCP, x402) run their real server apps over
httpx's ASGI transport, so requests go through the same routing, middleware and serialisation as on a network.

## Scaling path (Roadmap)

Move tasks, approvals, nonces and vouchers from memory to Redis or Postgres with TTLs; run A2A agents behind a load
balancer; replace shared bearer tokens with per-tenant credentials (OAuth client credentials); resolve did:wba over
HTTPS; send the audit log to the shared ops tables the hotel apps use.
