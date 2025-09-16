.PHONY: help test run

help:
	@echo "Usage: make [target] ..."
	@echo ""
	@echo "Available targets:"
	@echo "  help     Show this help message"
	@echo "  test     Run all tests"
	@echo "  run      Run development server"


test:
	OLDAP_TS_SERVER=http://localhost:7200 \
	OLDAP_TS_REPO=oldap \
	poetry run pytest -v $(TESTS)

run:
	OLDAP_TS_SERVER=http://localhost:7200 \
	OLDAP_TS_REPO=oldap \
	poetry run python oldap-api-app.py
