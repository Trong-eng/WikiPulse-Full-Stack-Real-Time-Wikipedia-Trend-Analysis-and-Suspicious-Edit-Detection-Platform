PYTHON ?= .venv/bin/python
COMPOSE ?= docker compose

.PHONY: help install up down logs init replay smoke test test-spark lint config build
help:
	@echo 'install | up | init | replay | smoke | test | test-spark | lint | config | logs | down'
install:
	python3 -m venv .venv
	$(PYTHON) -m pip install -e '.[dev]' -r dashboard/requirements.txt
build:
	$(COMPOSE) build api spark dashboard replay
up:
	$(COMPOSE) up -d --build api spark dashboard
init:
	$(COMPOSE) run --rm init-topics
	$(COMPOSE) run --rm init-cassandra
replay:
	$(COMPOSE) run --rm replay
down:
	$(COMPOSE) down
logs:
	$(COMPOSE) logs --tail=100 -f
config:
	$(COMPOSE) config --quiet
test:
	$(PYTHON) -m pytest -q -m 'not integration and not spark'
test-spark:
	$(COMPOSE) run --rm --no-deps spark python -m pytest processing/spark/tests -q
lint:
	.venv/bin/ruff check .
smoke:
	$(PYTHON) scripts/smoke_test.py
