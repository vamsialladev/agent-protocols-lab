PY ?= python
export PYTHONPATH := src

.PHONY: install test lint audit demos

install:
	$(PY) -m pip install -r requirements-dev.txt
	$(PY) -m pip install --no-deps -r requirements-nodeps.txt

test:
	$(PY) -m pytest --cov=demos --cov=protolab --cov-report=term-missing --cov-fail-under=80

lint:
	ruff check .
	ruff format --check .

audit:
	pip-audit --skip-editable --ignore-vuln PYSEC-2026-1325  # see docs/DECISIONS.md, decision 9

demos:
	for d in mcp_server a2a acp anp agora a2ui ap2 ucp x402; do $(PY) -m demos.$$d.demo; done
