# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-27
### Added
- Eleven demos: MCP server, MCP consumer, A2A, ACP, ANP, Agora, AG-UI, A2UI, AP2, UCP, x402, each with a README and
  tests; shared audit log and A2A helper.
- Agora's protocol core copied (MIT) instead of installing agora-protocol and its vulnerable LangChain stack;
  jwcrypto 1.6.1; one documented pip-audit ignore (decisions 8-9).
- CI: ruff, pytest with an 80% coverage gate, demo smoke runs, pip-audit, lychee, gitleaks.
