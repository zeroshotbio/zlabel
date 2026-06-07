.PHONY: setup format lint type test verify

setup:  ## install deps into the uv-managed venv
	uv sync

format:  ## ruff format + safe autofixes
	uv run ruff format .
	uv run ruff check --fix .

lint:  ## ruff check (no fixes) — the gate verify depends on
	uv run ruff check .

type:  ## pyright (basic)
	uv run pyright

test:  ## pytest
	uv run pytest

verify: lint type test  ## the PR gate: lint + types + tests
