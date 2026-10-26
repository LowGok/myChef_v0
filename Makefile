PYTHON ?= python3

.PHONY: run test test-live

run:
	$(PYTHON) -m streamlit run mychefApp/main.py

test:
	$(PYTHON) -m pytest -m 'not live'

test-live:
	MYCHEF_RUN_LIVE_E2E=1 $(PYTHON) -m pytest tests/e2e/test_live_menu.py -q -s
