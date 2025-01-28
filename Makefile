.PHONY: help test run

help:
	@echo "Usage: make [target] ..."
	@echo ""
	@echo "Available targets:"
	@echo "  help     Show this help message"
	@echo "  test     Run all tests"
	@echo "  run      Run development server"


test:
	poetry run pytest -v

run:
	poetry run python oladp-api-app.py
	