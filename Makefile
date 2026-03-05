.PHONY: dev test lint fmt check install docker clean

install:  ## Install dependencies
	pip install -e ".[dev]"

dev:  ## Start development server
	API_KEY=dev-test-key uvicorn main:app --app-dir src --reload --port 8000

test:  ## Run tests with coverage
	python -m pytest src/modules/credit/tests/ -x -q

coverage:  ## Run tests with coverage report
	coverage run -m pytest src/modules/credit/tests/ -x -q
	coverage report --show-missing

lint:  ## Run linter
	ruff check src/

fmt:  ## Format code
	ruff format src/
	ruff check --fix src/

check:  ## Run all checks (lint + format check + tests)
	ruff check src/
	ruff format --check src/
	python -m pytest src/modules/credit/tests/ -x -q

docker:  ## Build Docker image
	docker build -t credit-assessment .

clean:  ## Remove build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf *.egg-info .coverage htmlcov/ *.db

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
