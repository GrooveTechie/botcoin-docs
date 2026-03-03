.PHONY: install dev test seed clean docker-build docker-run help

# Default target
help:
	@echo "Hotel Deal Negotiator - Available Commands"
	@echo ""
	@echo "  make install     - Install dependencies"
	@echo "  make dev         - Run development server"
	@echo "  make test        - Run tests"
	@echo "  make seed        - Seed database with example data"
	@echo "  make clean       - Remove database and cache files"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run  - Run Docker container"
	@echo ""

# Install dependencies
install:
	pip install -r requirements.txt

# Run development server
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	pytest tests/ -v

# Seed database with example data
seed:
	python seed.py

# Clean up
clean:
	rm -rf data/
	rm -rf __pycache__
	rm -rf app/__pycache__
	rm -rf app/routes/__pycache__
	rm -rf app/services/__pycache__
	rm -rf tests/__pycache__
	rm -rf .pytest_cache

# Docker commands
docker-build:
	docker build -t hotel-deal-negotiator .

docker-run:
	docker run -p 8000:8000 -v $(PWD)/secrets:/app/secrets -v $(PWD)/data:/app/data hotel-deal-negotiator
