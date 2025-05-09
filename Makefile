.PHONY: help test run

help:
	@echo "Usage: make [target] ..."
	@echo ""
	@echo "Available targets:"
	@echo "  help     Show this help message"
	@echo "  test     Run all tests"
	@echo "  run      Run development server"


test:
	poetry run pytest -v $(TESTS)

run:
	poetry run python oldap-api-app.py
