PYTHON ?= .venv/bin/python
COMPOSE ?= docker compose
FULL_COMPOSE = $(COMPOSE) -f docker-compose.yml -f docker-compose.hdfs.yml --profile full

.PHONY: help install up down logs init replay smoke test test-spark lint config build up-full down-full config-full smoke-full
help:
	@echo 'install | up | up-full | init | replay | smoke | smoke-full | test | test-spark | lint | config | config-full | logs | down | down-full'
install:
	python3 -m venv .venv
	$(PYTHON) -m pip install -e '.[dev]' -r dashboard/requirements.txt
build:
	$(COMPOSE) build api spark dashboard replay
up:
	$(COMPOSE) up -d --build api spark dashboard
up-full:
	$(FULL_COMPOSE) up -d --build --wait --wait-timeout 240 api spark dashboard
down-full:
	$(FULL_COMPOSE) down
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
config-full:
	$(FULL_COMPOSE) config --quiet
test:
	$(PYTHON) -m pytest -q -m 'not integration and not spark'
test-spark:
	$(COMPOSE) run --rm --no-deps spark python -m pytest processing/spark/tests -q
lint:
	.venv/bin/ruff check .
smoke:
	$(PYTHON) scripts/smoke_test.py
smoke-full:
	$(PYTHON) scripts/smoke_test.py --hdfs
