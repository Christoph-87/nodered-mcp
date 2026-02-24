.PHONY: all check test lint format fix

all: format lint test

check: lint test

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

fix:
	uv run ruff check --fix --unsafe-fixes src/ tests/
