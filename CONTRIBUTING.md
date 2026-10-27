# Contributing

This is a portfolio lab, but issues and pull requests are welcome.

- Commits follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`).
- Before a pull request: `make lint test`. CI also runs every demo, pip-audit, a link check and gitleaks.
- Never commit a key. Secrets live only in `.env`, which is git-ignored.

## Adding a protocol

1. Check the official spec and SDK first: version, creator, whether it has merged or been renamed. Put what you found
   and the links in the demo's README.
2. Add `demos/<name>/demo.py` with a function the tests can call and a `main()`, plus `demos/<name>/README.md`.
3. Add `tests/test_<name>.py`: the normal path, each refusal that matters, and a control case.
4. Add a row to the README's protocol table and its `What it does` table.
5. Payments stay sandboxed or mocked. No real money, no mainnet, no real wallets or keys.
