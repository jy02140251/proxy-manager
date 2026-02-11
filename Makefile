.PHONY: help install test lint run docker-build docker-up clean

help:  ## Show available commands
	@grep -E "^[a-zA-Z_-]+:.*?## .*$$" $(MAKEFILE_LIST) | sort | \
		awk "BEGIN {FS = \":.*?## \"}; {printf \"\033[36m%-18s\033[0m %s\n\", $$1, $$2}"

install:  ## Install dependencies
	pip install -r requirements.txt

dev:  ## Install dev dependencies
	pip install -r requirements.txt pytest pytest-asyncio pytest-cov black flake8

test:  ## Run tests with coverage
	pytest tests/ -v --cov=. --cov-report=term-missing --ignore=venv

lint:  ## Run code quality checks
	black --check *.py tests/
	flake8 *.py tests/ --max-line-length=100

format:  ## Auto-format code
	black *.py tests/

run:  ## Start the proxy manager
	python proxy_manager.py

run-api:  ## Start the API server
	uvicorn api:app --reload --host 0.0.0.0 --port 8080

docker-build:  ## Build Docker image
	docker-compose build

docker-up:  ## Start all services
	docker-compose up -d

docker-down:  ## Stop all services
	docker-compose down

clean:  ## Clean up artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov