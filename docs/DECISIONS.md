# Decisions

Each one: context, decision, trade-off, result.

## 1. One demo per protocol, official SDK where it's usable (2026-10-26)
- **Context:** the plan asks for a small, working, tested demo per protocol, checked against the current spec, with
  no faking where a protocol has merged or has no SDK.
- **Decision:** use the official SDK when it installs and runs (MCP, A2A, ACP, ANP, Agora, AG-UI, A2UI, AP2, x402);
  otherwise write from the spec and say so (UCP).
- **Trade-off:** eleven dependency trees in one environment; some SDKs fight (decision 3).
- **Result:** ten of eleven use the official package; UCP is written from its spec at a pinned tag.

## 2. Rule-based agents by default, one live model run (2026-10-26)
- **Context:** the demos are about protocols. A model in every demo would make CI need a key and make results vary.
- **Decision:** small rule-based agents everywhere; demo 6 (Agora), where negotiation in natural language is the
  point, has a `--live` mode with Claude Haiku 5.5.
- **Trade-off:** the stand-ins don't show model behaviour; the hotel apps do (the concierge, the guest request agent).
- **Result:** the suite runs in about 20 seconds with no key. One live Agora run is saved (about $0.0005).

## 3. AP2's SDK without its exact pins (2026-10-27)
- **Context:** AP2 v0.2.0 pins `pydantic==2.12.5`, `cryptography==46.0.5` and `pytest==9.0.2` as runtime
  dependencies. The other SDKs need newer pydantic. The PyPI name `ap2` belongs to an unrelated project.
- **Decision:** install AP2 from its tag's commit archive with `--no-deps` (`requirements-nodeps.txt`), and its
  signing dependencies at its own versions.
- **Trade-off:** `pip check` reports the pin mismatch; an AP2 release could rely on something only the pinned
  versions have.
- **Result:** its models and JWT helper run on the newer versions; tests/test_ap2.py covers every path used.

## 4. ACP kept, with its workarounds visible (2026-10-27)
- **Context:** ACP merged into A2A and its repo is archived. The last SDK needs uvicorn 0.35, its client omits a
  Content-Type header current FastAPI requires, and it sets up its executor in a lifespan.
- **Decision:** keep the demo, side by side with A2A, with each workaround commented in the code.
- **Trade-off:** an old uvicorn pin for the whole lab.
- **Result:** the same delegation gives the same result over both; the README says plainly not to start new work on
  ACP.

## 5. Agora without generated code (2026-10-27)
- **Context:** the Agora library's programmer writes Python routines and runs them with RestrictedPython.
- **Decision:** use the library for protocol documents, hashes and wire fields; write the negotiation loop myself;
  never run generated code; validate structured bodies against the agreed schema.
- **Trade-off:** no "routine" speed-up after agreement; this demo shows the negotiation and the switch, not
  Agora's code generation.
- **Result:** the first live run found my bug (the accepted document isn't always in the last message); fixed with
  a test.

## 6. x402 on a mock network (2026-10-27)
- **Context:** x402's real schemes sign token transfers on a blockchain. The rules for this portfolio: no real money,
  no mainnet, no real wallets or keys.
- **Decision:** the official package's schemas and headers, with a mock scheme and network and a mock facilitator
  holding play money.
- **Trade-off:** it doesn't show EIP-3009 signing or settlement.
- **Result:** the agent skips a Base mainnet option when it's offered, and every spending rule is tested.

## 7. Demo 2's live run behind an opt-in (2026-10-27)
- **Context:** demo 2 starts npm-hosted MCP servers with npx and drives Chrome. The environment I built this in
  blocked that run.
- **Decision:** unit-test the gateway with fake sessions; keep the live test behind `LAB_NPX=1`; say it hasn't run
  here.
- **Trade-off:** the three-server run is unverified until someone runs it.
- **Result (updated 2026-10-27):** run live with the owner's approval and conditions: exact pinned versions with
  npm provenance checked, the filesystem server rooted in a fresh folder inside the lab with copies of synthetic
  files, Playwright headless with a fresh profile on a local page only. Every check passed
  (demos/mcp_consumer/README.md). The live test stays opt-in because CI has no Chrome.

## 8. Agora's core copied, the package dropped (2026-10-27)
- **Context:** the first CI run's pip-audit failed. `import agora` loads its LangChain, LangGraph and RestrictedPython
  integrations, and the versions agora-protocol 0.2.0 pins had 18 known vulnerabilities between them.
- **Decision:** copy the parts the demo uses (`Protocol`, `compute_hash`, `extract_metadata`; MIT License) into
  `src/protolab/agora_core.py` and remove the package. A test pins `compute_hash("hello")` to the package's output.
- **Trade-off:** a later Agora change to its hashing wouldn't reach the lab by itself.
- **Result:** the vulnerable tree is gone; the demo and its tests are unchanged.

## 9. jwcrypto above AP2's pin; one advisory ignored with a reason (2026-10-27)
- **Context:** the same audit flagged jwcrypto 1.5.6 (AP2's pin; PYSEC-2026-70, fixed in 1.5.7) and python-ecdsa
  0.19.2 (PYSEC-2026-1325 / CVE-2024-23342, a Minerva timing attack on P-256 signing that upstream won't fix).
- **Decision:** jwcrypto 1.6.1 (AP2 is installed without its pins anyway, decision 3). Ignore only
  PYSEC-2026-1325 in CI and the Makefile, with the reason next to it: ecdsa arrives through anp, and nothing here signs
  with it (ANP signs with Ed25519, AP2 with ES256, both through cryptography).
- **Trade-off:** an ignore can outlive its reason; it's written next to the command so it gets re-read.
- **Result:** pip-audit passes with that one ignore; AP2's tests pass on jwcrypto 1.6.1.

I should have run pip-audit before the first push. The first CI run on main was red for these reasons.

## 10. UCP checked against the official SDK, both runs kept (2026-10-27)
- **Context:** demo 10 was first written from the spec's examples because installing `ucp-sdk` was blocked. The
  owner then approved installing it from the official organisation, pinned, inside the lab's virtual environment.
- **Decision:** install `ucp-sdk` 0.5.0 from its tag v2026-08-25 (commit b6f9b91c), run pip-audit, and validate every
  request and response of the demo's flow with the SDK's models during the run.
- **Trade-off:** the demo now depends on an SDK that isn't on PyPI and is generated from schemas that change with
  each dated spec release.
- **Result:** pip-audit: nothing new. The spec-only version failed 6 of 9 checks: payment handler keys must be
  reverse-domain names with a version, an order needs a `permalink_url`, and an update must carry the line items.
  Fixed; 9 of 9 conform. Both runs are saved and labelled (docs/ucp-spec-only-run.md, docs/ucp-sdk-run.md), and a
  test keeps the old shapes to show the SDK rejects them. Writing from examples got the flow right and the
  details wrong.
