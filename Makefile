# Agent0 Makefile - Common development tasks

.PHONY: help install install-dev run train benchmark monitor test clean

# Default target
help:
	@echo "Agent0 - Self-Evolving AI Agents"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Installation:"
	@echo "  install       Install agent0 package"
	@echo "  install-dev   Install with development dependencies"
	@echo "  install-all   Install with all optional dependencies"
	@echo ""
	@echo "Running:"
	@echo "  run           Run co-evolution loop (10 steps)"
	@echo "  run-100       Run co-evolution loop (100 steps)"
	@echo "  train         Run RL training (10 epochs)"
	@echo "  benchmark     Run MATH benchmark (50 samples)"
	@echo "  monitor       Start real-time monitor"
	@echo "  chat          Start interactive chat"
	@echo "  status        Check system status"
	@echo ""
	@echo "Development:"
	@echo "  test          Run tests"
	@echo "  lint          Run linters"
	@echo "  format        Format code"
	@echo "  clean         Clean build artifacts"
	@echo ""
	@echo "Examples:"
	@echo "  make install && make status"
	@echo "  make run"
	@echo "  make benchmark"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-all:
	pip install -e ".[all]"

# Running targets
status:
	python -m agent0.cli status -v

run:
	python -m agent0.cli run --steps 10 -v

run-100:
	python -m agent0.cli run --steps 100

train:
	python -m agent0.cli train --epochs 10

train-grpo:
	python -m agent0.cli train --epochs 10 --use-grpo

benchmark:
	python -m agent0.cli benchmark --type math --limit 50

benchmark-full:
	python -m agent0.cli benchmark --type math --limit 500

monitor:
	python -m agent0.cli monitor

chat:
	python -m agent0.cli chat

solve:
	@read -p "Problem: " problem; \
	python -m agent0.cli solve "$$problem"

# GUI (optional)
gui:
	python main_gui.py

# Development targets
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=agent0 --cov-report=html

lint:
	ruff check agent0/
	mypy agent0/

format:
	black agent0/
	isort agent0/

# Cleaning
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

clean-runs:
	rm -rf runs/
	rm -rf checkpoints/
	rm -rf eval_results/

# Docker (future)
docker-build:
	docker build -t agent0 .

docker-run:
	docker run -it --rm agent0
