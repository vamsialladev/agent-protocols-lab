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
- **Result:** listed under Limitations in the README.
