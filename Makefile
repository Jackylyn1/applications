# The validation workflow from CODING_RULES.md, as one command.
#
# `make check` is the contract: if it is green, the code is shippable. CI runs
# exactly these targets, so a green local run and a green pipeline mean the same
# thing. Tool settings live in pyproject.toml, never as flags here.

PY      ?= python3
VENV    ?= .venv
BIN      = $(VENV)/bin
SOURCES  = career-kb/tools job-watch tests

.DEFAULT_GOAL := check
.PHONY: check lint format typecheck security complexity deadcode test audit fix venv clean

$(BIN)/ruff: requirements-dev.txt
	$(PY) -m venv $(VENV) 2>/dev/null || $(PY) -m venv --without-pip $(VENV)
	$(BIN)/pip install -q -U pip
	$(BIN)/pip install -q -r requirements-dev.txt -r requirements.txt
	@touch $(BIN)/ruff

venv: $(BIN)/ruff  ## create the dev virtualenv

## run the whole validation workflow
check: lint format typecheck security complexity deadcode test audit
	@echo "\nAll checks passed."

lint: venv           ## Ruff
	$(BIN)/ruff check .

format: venv         ## Ruff Formatter (check only; `make fix` rewrites)
	$(BIN)/ruff format --check .

typecheck: venv      ## mypy
	$(BIN)/mypy

security: venv       ## Bandit — only medium severity and above fails the build
	$(BIN)/bandit -q -ll -c pyproject.toml -r $(SOURCES)

complexity: venv     ## Radon/Xenon — no block worse than C, no module worse than B
	$(BIN)/xenon -b C -m B -a A $(SOURCES)

deadcode: venv       ## Vulture (paths and exclusions come from pyproject.toml)
	$(BIN)/vulture

test: venv           ## pytest + coverage.py
	$(BIN)/coverage run -m pytest
	$(BIN)/coverage report

audit: venv          ## pip-audit — advisory only, see README
	-$(BIN)/pip-audit -r requirements.txt

fix: venv            ## apply every safe autofix
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

clean:
	rm -rf $(VENV) .ruff_cache .mypy_cache .pytest_cache .coverage
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
