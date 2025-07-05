# Makefile for Bangladesh Education Data API

# ==============================================================================
# Environment
# ==============================================================================

# Project variables
PROJECT_NAME := bossnet
ENV_FILE := .env

# Executables
PYTHON := python3
PIP := pip3
DOCKER := docker
DOCKER_COMPOSE := docker-compose
PYTEST := python -m pytest
ALEMBIC := alembic
BLACK := black
ISORT := isort
FLAKE8 := flake8
MYPY := mypy
BANDIT := bandit
SAFETY := safety
PRECOMMIT := pre-commit
UVICORN := uvicorn

# Directories
SRC_DIR := src
TESTS_DIR := tests
DOCS_DIR := docs
MIGRATIONS_DIR := alembic

# Default values
PYTHON_VERSION := 3.9
PORT := 8000

# Default target
.DEFAULT_GOAL := help

# ==============================================================================
# Help
# ==============================================================================

.PHONY: help
help:  ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup

setup:  ## Setup development environment
	@echo "Setting up development environment..."
	$(PYTHON) -m venv .venv
	@echo "Activate virtual environment with: source .venv/bin/activate"
	@echo "Then run 'make install' to install dependencies"

install: check-env  ## Install development dependencies
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"
	$(PIP) install -r requirements.txt
	$(PRECOMMIT) install

check-env:  ## Check if .env file exists
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "Error: $(ENV_FILE) file not found. Please create one from .env.example"; \
		exit 1; \
	fi

##@ Development

format:  ## Format code with Black and isort
	$(BLACK) $(SRC_DIR) $(TESTS_DIR)
	$(ISORT) $(SRC_DIR) $(TESTS_DIR)

lint:  ## Lint code with flake8, mypy, and bandit
	$(FLAKE8) $(SRC_DIR) $(TESTS_DIR)
	$(MYPY) $(SRC_DIR) $(TESTS_DIR)
	$(BANDIT) -r $(SRC_DIR) -c pyproject.toml

security:  ## Check for security vulnerabilities
	$(SAFETY) check --full-report

pre-commit:  ## Run all pre-commit hooks
	$(PRECOMMIT) run --all-files

test:  ## Run tests with coverage
	$(PYTEST) --cov=$(SRC_DIR) \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-fail-under=80 \
		$(TESTS_DIR)

test-watch:  ## Run tests in watch mode
	$(PYTEST) --cov=$(SRC_DIR) --cov-report=term-missing -xvs --pdb

coverage: test  ## Generate and open coverage report
	open htmlcov/index.html

format:  ## Format code with Black and isort
	black .
	isort .

lint:  ## Lint code with flake8 and mypy
	flake8
	mypy .

test:  ## Run tests
	$(PYTEST) --cov=src --cov-report=term-missing

##@ Database

db-up: check-env  ## Start database containers
	$(DOCKER_COMPOSE) up -d db redis


db-down:  ## Stop database containers
	$(DOCKER_COMPOSE) stop db redis


db-shell: check-env  ## Connect to the database with psql
	$(DOCKER_COMPOSE) exec db psql -U postgres -d student_data_db


db-backup:  ## Create a database backup
	@mkdir -p backups
	@timestamp=$$(date +%Y%m%d_%H%M%S) && \
	$(DOCKER_COMPOSE) exec -T db pg_dump -U postgres student_data_db > backups/backup_$$timestamp.sql && \
	echo "Backup created: backups/backup_$$timestamp.sql"


db-restore: check-env  ## Restore database from backup
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Error: Please specify a backup file with BACKUP_FILE=path/to/backup.sql"; \
		exit 1; \
	fi
	@if [ ! -f "$(BACKUP_FILE)" ]; then \
		echo "Error: Backup file $(BACKUP_FILE) not found"; \
		exit 1; \
	fi
	@echo "Restoring database from $(BACKUP_FILE)..."
	@$(DOCKER_COMPOSE) exec -T db psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS student_data_db;"
	@$(DOCKER_COMPOSE) exec -T db psql -U postgres -d postgres -c "CREATE DATABASE student_data_db;"
	@cat $(BACKUP_FILE) | $(DOCKER_COMPOSE) exec -T db psql -U postgres -d student_data_db
	@echo "Database restored successfully"


migrate: check-env  ## Run database migrations
	$(ALEMBIC) upgrade head


migrate-create: check-env  ## Create a new migration
	@if [ -z "$(MESSAGE)" ]; then \
		read -p "Enter migration message: " message; \
		$(ALEMBIC) revision --autogenerate -m "$$message"; \
	else \
		$(ALEMBIC) revision --autogenerate -m "$(MESSAGE)"; \
	fi


db-reset: db-down db-up migrate  ## Reset database (drop, create, migrate)

##@ Docker

docker-build:  ## Build Docker images
	$(DOCKER_COMPOSE) build --no-cache


docker-up: check-env  ## Start all services in detached mode
	$(DOCKER_COMPOSE) up -d


docker-down:  ## Stop all services
	$(DOCKER_COMPOSE) down


docker-logs:  ## View logs from all services
	$(DOCKER_COMPOSE) logs -f --tail=100


docker-clean:  ## Remove all containers, networks, and volumes
	$(DOCKER_COMPOSE) down -v --remove-orphans
	$(DOCKER) system prune -f


docker-stats:  ## Show container resource usage
	$(DOCKER) stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

##@ Application

run: check-env  ## Run the application locally with auto-reload
	$(UVICORN) src.main:app --host 0.0.0.0 --port $(PORT) --reload


run-prod: check-env  ## Run the application in production mode
	$(UVICORN) src.main:app --host 0.0.0.0 --port $(PORT) --workers 4


shell:  ## Open a Python shell with the application context
	$(PYTHON) -m IPython


check: lint test security  ## Run all checks (lint, test, security)

##@ Documentation

docs-serve:  ## Serve documentation locally
	mkdocs serve -a localhost:8001


docs-build:  ## Build documentation
	mkdocs build --clean


docs-deploy:  ## Deploy documentation to GitHub Pages
	mkdocs gh-deploy --force

##@ Cleanup

clean:  ## Clean up temporary files and caches
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	rm -rf \
		.coverage \
		htmlcov/ \
		build/ \
		dist/ \
		.pytest_cache/ \
		.mypy_cache/ \
		.ipynb_checkpoints/ \
		*.egg-info/ \
		*.pyc \
		*.pyo \
		.python-version


clean-all: clean  ## Clean everything including Docker resources
	$(DOCKER) system prune -a --volumes --force

.PHONY: help \
	setup install check-env \
	format lint security pre-commit test test-watch coverage \
	db-up db-down db-shell db-backup db-restore migrate migrate-create db-reset \
	docker-build docker-up docker-down docker-logs docker-clean docker-stats \
	run run-prod shell check \
	docs-serve docs-build docs-deploy \
	clean clean-all
