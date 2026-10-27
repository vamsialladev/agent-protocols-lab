# Security

## Reporting a vulnerability

Email vamsialla.dev@gmail.com with the details. Please don't open a public issue for a security problem. This is a
demo lab with synthetic data and no hosted service, so I'll reply within a few days.

## Scope

Everything runs locally. There are no secrets in the repo; the only optional secret is `ANTHROPIC_API_KEY` for
demo 6's live mode, read from a git-ignored `.env`. Payments are sandboxes or mocks: no payment network, no card, no
real money, no blockchain, no wallet. Keys used for signatures (ANP, AP2) are generated per run and never written to
disk.

## Threat model

| Asset | Threat | Mitigation | Demo |
|---|---|---|---|
| Tools an agent can call | An agent (or text it read) calls a tool it shouldn't | One role per MCP session; client allowlist per server; read-only scopes; origin allowlist for the browser | 1, 2 |
| Delegated tasks | An unknown caller sends work to an agent | Bearer token on everything but the public card / manifest (constant-time compare) | 3, 4 |
| Agent identity | Impersonating another agent; replaying its messages | did:wba with key binding, headers bound to the receiver's domain, signed bodies, nonces, 5-minute window | 5 |
| The agent's own process | Running code an agent generated | Never run Agora routines; validate bodies against the agreed schema | 6 |
| The user's screen | Injected markup, tracking pixels, fake buttons | AG-UI text via textContent; A2UI official validator + narrower allowlist, escaping, named events only | 7, 8 |
| Money | Unapproved, altered, repeated or oversized payments | Signed carts and approvals, per-payment and daily limits, single-use mandate IDs and vouchers, catalog prices, Idempotency-Key, mock networks only | 9, 10, 11 |
| Secrets | A key ends up in a log or the repo | Audit log masks key shapes; `.env` git-ignored; gitleaks in pre-commit and CI | all |

## OWASP Top 10 for LLM applications (2025)

| ID | Risk | Here |
|---|---|---|
| LLM01 | Prompt injection | Agent messages are data: Agora's negotiator prompt says so and its output only counts if it's a valid document; structured phases validate against schemas; MCP results go through a gateway that can't widen what a tool may do |
| LLM02 | Sensitive information disclosure | Synthetic data; the A2A hand-off sends no guest name or room; the audit log masks secrets |
| LLM03 | Supply chain | SDKs pinned (exact where an SDK is fragile); npm servers pinned to releases older than two weeks; AP2 installed from its official tag, not the unrelated PyPI `ap2`; pip-audit and Dependabot |
| LLM04 | Data and model poisoning | No training; documents are the repo's own synthetic files |
| LLM05 | Improper output handling | A2UI and AG-UI output is escaped and allowlisted; no agent output is executed |
| LLM06 | Excessive agency | Allowlisted tools and events; payments need the guest's signature or confirmation; the concierge holds no key that can authorise a payment |
| LLM07 | System prompt leakage | The only prompt (demo 6) holds no secrets |
| LLM08 | Vector and embedding weaknesses | Not applicable: no vector store here (the stage 7 server's policy search is BM25) |
| LLM09 | Misinformation | Structured checks (schemas, catalog prices, signatures) instead of trusting an agent's claims |
| LLM10 | Unbounded consumption | Spending caps (AP2, x402), quantity limits (UCP), a 4-round cap on Agora negotiation, `max_tokens` on the live model call |

## Before any real deployment

These demos stop at sandboxes on purpose. A real version needs per-tenant credentials instead of shared bearer
tokens, keys in a key management service, real DID resolution over HTTPS, a payment provider's test mode before any
live keys, and a spending limit set in the Anthropic Console for any public model use.
