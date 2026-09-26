UV ?= $(shell command -v uv 2>/dev/null || printf '%s' '$(CURDIR)/.uv-tools/bootstrap/bin/uv')
UV_CACHE_DIR ?= $(CURDIR)/.uv-cache
UV_PYTHON_INSTALL_DIR ?= $(CURDIR)/.uv-tools/python
export UV_CACHE_DIR
export UV_PYTHON_INSTALL_DIR

.PHONY: setup run test clean

setup:
	python3 scripts/bootstrap.py
	$(UV) sync --locked

run:
	$(UV) run --locked ion

test:
	$(UV) run --locked python -m pytest -q

clean:
	python3 scripts/clean.py
