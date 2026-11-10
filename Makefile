# Everyday Nepal - developer tasks (Windows-friendly PowerShell + make)
.DEFAULT_GOAL := help

PY ?= python
VENV := .venv

.PHONY: help venv install dev test lint format coverage run docker-build docker-up migrate webhook stats clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

venv: ## Create the virtual environment
	$(PY) -m venv $(VENV)

install: ## Install runtime + dev dependencies
	$(VENV)/Scripts/python -m pip install --upgrade pip
	$(VENV)/Scripts/python -m pip install -r requirements-dev.txt

dev: ## Run the bot with autoreload
	$(VENV)/Scripts/python -m uvicorn app.main:app --reload --port 8000

test: ## Run the test suite
	$(VENV)/Scripts/python -m pytest

lint: ## Lint with ruff
	$(VENV)/Scripts/python -m ruff check .

format: ## Auto-fix lint issues
	$(VENV)/Scripts/python -m ruff check --fix .

coverage: ## Run tests with coverage
	$(VENV)/Scripts/python -m pytest --cov=app --cov-report=term-missing

migrate: ## Apply database migrations
	$(VENV)/Scripts/python -m alembic upgrade head

webhook: ## Register the Telegram webhook (and publish commands)
	$(VENV)/Scripts/python scripts/set_webhook.py

stats: ## Print 7-day analytics
	$(VENV)/Scripts/python scripts/stats.py 7

docker-build: ## Build the container image
	docker compose build

docker-up: ## Start app + postgres
	docker compose up -d

clean: ## Remove caches and local db
	-$(VENV)/Scripts/python -c "import shutil,glob;[shutil.rmtree(p,ignore_errors=True) for p in glob.glob('**/__pycache__',recursive=True)]"
