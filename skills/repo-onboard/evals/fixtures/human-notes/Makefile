.PHONY: check lint unit

check: lint unit

lint:
	uv run ruff check src tests

unit:
	uv run pytest -q
