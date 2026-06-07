.DEFAULT_GOAL := help
.PHONY: help setup setup-core setup-upgrade format lint lint-docstrings type test verify notebook

help:  ## Show this help
	@awk 'BEGIN {FS = ":.*## "; print "Usage: make <target>\n"} /^##@/ {printf "\n%s\n", substr($$0, 5)} /^[a-zA-Z0-9_.-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

##@ Environment
setup:  ## Sync the full dev environment (all groups + extras)
	uv sync --all-groups --all-extras

setup-core:  ## Sync only the core runtime deps (no dev tools)
	uv sync --no-default-groups

setup-upgrade:  ## Sync the full dev environment, upgrading locked versions
	uv sync --all-groups --all-extras --upgrade

##@ Quality
format:  ## ruff format + safe autofixes
	uv run ruff format .
	uv run ruff check --fix .

lint:  ## ruff check (no fixes) — the gate verify depends on
	uv run ruff check .

lint-docstrings:  ## Fail on backticks or Sphinx roles in Python prose (plain text only)
	@if grep -rEn --include='*.py' '`|:(param|type|returns|rtype|raises|class|func|meth|mod|obj|attr|data|ref):' src tests; then \
		echo "FAIL: backtick or reST role in Python source — keep docstrings/comments plain text (backticks belong in .md)"; exit 1; \
	else echo "docstrings clean (plain text, no backticks or reST)"; fi

type:  ## pyright (basic)
	uv run pyright

test:  ## pytest
	uv run pytest

verify: lint lint-docstrings type test  ## The PR gate: lint + docstrings + types + tests

##@ Development
notebook:  ## Start JupyterLab on port 8888 (no token; run make setup first)
	uv run jupyter lab --no-browser --port=8888 --ServerApp.token='' --ServerApp.password=''
