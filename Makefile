.PHONY: help test

help:
	@echo "Usage: make [target] ..."
	@echo ""
	@echo "Available targets:"
	@echo "  help     Show this help message"
	@echo "  test     Run all tests"


test:
	poetry run pytest -v