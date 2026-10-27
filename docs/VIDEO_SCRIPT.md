# Video script: Agent Protocols Lab (about 75 seconds)

Natural, first person, like explaining it on a call. AI narration is allowed only if it sounds natural, and the video
is labelled "AI-narrated". My own voice replaces it when I record one. Each demo also gets a 30–45 second clip
(below), made from the same terminal runs.

## Main video

| Time | On screen | Say |
|---|---|---|
| 0:00 | README, protocol table | "Agent protocols are arriving faster than anyone can read the specs. So I built one small demo for each, in the same hotel scenario." |
| 0:10 | `pytest` running, 44 passed | "Eleven demos, forty-four tests, and they run in about twenty seconds with no API key." |
| 0:18 | `python -m demos.mcp_server.demo` | "MCP first. A guest and the front desk connect to the same hotel tool server. The guest sees four tools, front desk sees five." |
| 0:28 | `python -m demos.a2a.demo` | "A2A: the concierge reads another agent's card and hands it a guest email. The task comes back completed, with an artifact." |
| 0:38 | `python -m demos.anp.demo` | "ANP: two agents make their own identities and sign their messages. A replayed or changed message is refused." |
| 0:48 | AG-UI page in a browser, click Approve | "AG-UI streams the run to a page, and nothing gets sent until a person approves it." |
| 0:58 | `python -m demos.ap2.demo` | "And payments. AP2 needs the guest's signature and has limits. Over two hundred dollars? Refused. All sandbox, no real money." |
| 1:08 | README, "Other protocols" table | "Each demo says what the protocol is for, when I wouldn't use it, and what I found. ACP has merged into A2A, and it shows." |

Tested inputs: the commands above, exactly as written, with `PYTHONPATH=src`.

## Per-demo clips (30–45 s each)

For each demo: 5 s on its README's "What it shows", 20–30 s on its `python -m demos.<name>.demo` run, 5–10 s on the
one refusal its test checks (wrong token, replay, tampered cart, unknown component, real network skipped).
