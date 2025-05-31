# PhotosSorter Makefile
# Provides convenient commands for development and deployment

.PHONY: help install install-dev clean test lint format check setup run dry-run build dist upload

# Default target
help:
	@echo "PhotosSorter Development Commands:"
	@echo ""
	@echo "Setup and Installation:"
	@echo "  make install      - Install package and dependencies"
	@echo "  make install-dev  - Install package with development dependencies"
	@echo "  make setup        - Setup development environment"
	@echo ""
	@echo "Development:"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Check code style with flake8"
	@echo "  make format       - Format code with black"
	@echo "  make check        - Run all checks (lint + format check)"
	@echo ""
	@echo "Running:"
	@echo "  make run          - Run photos sorter"
	@echo "  make dry-run      - Run in dry-run mode (safe preview)"
	@echo ""
	@echo "Building and Distribution:"
	@echo "  make build        - Build package"
	@echo "  make dist         - Create distribution files"
	@echo "  make clean        - Clean build artifacts"
	@echo ""
	@echo "  make help         - Show this help message"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev,video]"

setup: install-dev
	@echo "Setting up development environment..."
	@if [ ! -f config.yaml ]; then \
		cp config.yaml.example config.yaml; \
		echo "Created config.yaml from example"; \
	fi
	@echo "Development environment ready!"

# Development tools
test:
	@if command -v pytest >/dev/null 2>&1; then \
		pytest; \
	else \
		echo "pytest not installed. Run 'make install-dev' first."; \
	fi

lint:
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 src/; \
	else \
		echo "flake8 not installed. Run 'make install-dev' first."; \
	fi

format:
	@if command -v black >/dev/null 2>&1; then \
		black src/; \
	else \
		echo "black not installed. Run 'make install-dev' first."; \
	fi

check: lint
	@if command -v black >/dev/null 2>&1; then \
		black --check src/; \
	else \
		echo "black not installed. Run 'make install-dev' first."; \
	fi

# Running
run:
	python run.py

dry-run:
	python run.py --dry-run

# Building and distribution
build:
	python -m build

dist: clean build
	@echo "Distribution files created in dist/"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete

# Check dependencies
check-deps:
	@echo "Checking system dependencies..."
	@command -v ffmpeg >/dev/null 2>&1 && echo "✓ ffmpeg found" || echo "✗ ffmpeg not found (needed for video processing)"
	@python -c "import PIL; print('✓ Pillow found')" 2>/dev/null || echo "✗ Pillow not found"
	@python -c "import yaml; print('✓ PyYAML found')" 2>/dev/null || echo "✗ PyYAML not found"
	@python -c "import exifread; print('✓ exifread found')" 2>/dev/null || echo "✗ exifread not found"

# Development helpers
config:
	@if [ ! -f config.yaml ]; then \
		cp config.yaml.example config.yaml; \
		echo "Created config.yaml from example. Please edit it with your settings."; \
	else \
		echo "config.yaml already exists"; \
	fi

logs:
	@mkdir -p logs
	@echo "Logs directory ready"

# Quick start for new users
quick-start: setup config logs check-deps
	@echo ""
	@echo "🎉 PhotosSorter is ready to use!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit config.yaml with your photo directory path"
	@echo "2. Run 'make dry-run' to preview what will happen"
	@echo "3. Run 'make run' to actually sort your photos"
	@echo ""