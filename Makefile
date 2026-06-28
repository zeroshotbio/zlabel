.DEFAULT_GOAL := help
.PHONY: help setup setup-core setup-upgrade format lint lint-docstrings type test verify audit eval gate eval-zscape gate-zscape eval-zebrahub gate-zebrahub gate-all hooks notebook

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
	uv run pytest -vv

verify: lint lint-docstrings type test  ## The PR gate: lint + docstrings + types + tests

audit:  ## Curation gate: audit panels.yaml markers vs ZFIN data (needs data/ontologies; not in CI)
	uv run python scripts/audit_panels.py

eval:  ## Regenerate the Daniocell baseline report (needs data/ontologies)
	uv run python -m zlabel.evaluate benchmarks/daniocell_eval.csv

gate:  ## Regression wall: fail on baseline drift / overcall-audit regression (needs data/ontologies)
	uv run python scripts/check_baseline.py

eval-zscape:  ## Regenerate the held-out ZSCAPE 2nd-atlas report (needs data/ontologies)
	uv run python scripts/atlas_eval.py run --atlas zscape

gate-zscape:  ## Held-out wall: ZSCAPE report drift, with a directional read (needs data/ontologies)
	uv run python scripts/atlas_eval.py check --atlas zscape

eval-zebrahub:  ## Regenerate the held-out Zebrahub 3rd-atlas report (needs data/ontologies)
	uv run python scripts/atlas_eval.py run --atlas zebrahub

gate-zebrahub:  ## Held-out wall: Zebrahub report drift, with a directional read (needs data/ontologies)
	uv run python scripts/atlas_eval.py check --atlas zebrahub

gate-all: gate gate-zscape gate-zebrahub  ## All regression walls: Daniocell (hard) + ZSCAPE + Zebrahub (held-out)

##@ Development
hooks:  ## Install the git pre-commit hook (runs make gate-all on engine/panel/benchmark changes)
	install -m 0755 scripts/hooks/pre-commit .git/hooks/pre-commit
	@echo "installed .git/hooks/pre-commit"

notebook:  ## Start JupyterLab on port 8888 (no token; run make setup first)
	uv run jupyter lab --no-browser --port=8888 --ServerApp.token='' --ServerApp.password=''
