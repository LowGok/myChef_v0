UV ?= uv

.PHONY: sync run test test-live lock lock-check audit

sync:
	$(UV) sync --locked

run:
	$(UV) run --locked streamlit run mychefApp/main.py

test:
	$(UV) run --locked pytest -m 'not live'

test-live:
	MYCHEF_RUN_LIVE_E2E=1 $(UV) run --locked pytest tests/e2e/test_live_menu.py -q -s

lock:
	$(UV) lock

lock-check:
	$(UV) lock --check

audit:
	$(UV) run --locked python scripts/audit_dependencies.py
