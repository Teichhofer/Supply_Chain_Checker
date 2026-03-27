.PHONY: format format-check lint type test check

format:
	python -m black src tests
	python -m ruff check --fix src tests

format-check:
	python -m black --check src tests
	python -m ruff format --check src tests

lint:
	python -m ruff check src tests

type:
	python -m mypy src

test:
	python -m pytest

check: format-check lint type test
