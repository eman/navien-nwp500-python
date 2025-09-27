# NaviLink Development Makefile

.PHONY: help install install-dev format lint test test-integration check clean build upload

# Default target
help:
	@echo "NaviLink Development Commands:"
	@echo ""
	@echo "Setup:"
	@echo "  install     Install package for production use"
	@echo "  install-dev Install package with development dependencies"
	@echo ""
	@echo "Code Quality (REQUIRED before committing):"
	@echo "  format      Format code with Black and isort (REQUIRED)"
	@echo "  lint        Run linting checks"
	@echo "  check       Run all quality checks (format + lint + test)"
	@echo ""
	@echo "Testing:"
	@echo "  test        Run unit and HAR-based tests"
	@echo "  test-integration  Run integration tests (requires credentials)"
	@echo "  test-coverage     Run tests with coverage report"
	@echo ""
	@echo "Build & Release:"
	@echo "  clean       Clean build artifacts"
	@echo "  build       Build package for distribution"
	@echo "  upload      Upload to PyPI (requires TWINE_PASSWORD)"
	@echo ""
	@echo "⚠️  IMPORTANT: Run 'make check' before committing to avoid CI failures!"

# Installation
install:
	pip install .

install-dev:
	pip install -e ".[dev,test]"

# Code formatting (REQUIRED)
format:
	@echo "🎨 Formatting code with Black..."
	black .
	@echo "📚 Sorting imports with isort..."
	isort .
	@echo "✅ Code formatting complete!"

# Linting
lint:
	@echo "🔍 Checking Black formatting..."
	black --check .
	@echo "🔍 Checking import sorting..."
	isort --check-only .
	@echo "🔍 Running type check..."
	mypy navien_nwp500 || echo "⚠️  Type check warnings (non-blocking)"
	@echo "✅ Linting complete!"

# Testing
test:
	@echo "🧪 Running unit and HAR-based tests..."
	pytest tests/ -v --tb=short
	@echo "✅ Tests complete!"

test-integration:
	@echo "🧪 Running integration tests (requires credentials)..."
	pytest tests/test_integration.py -v
	@echo "✅ Integration tests complete!"

test-coverage:
	@echo "📊 Running tests with coverage..."
	pytest --cov=navien_nwp500 --cov-report=term-missing --cov-report=html
	@echo "📄 Coverage report: htmlcov/index.html"

# Complete quality check (REQUIRED before committing)
check: format lint test
	@echo ""
	@echo "🎉 All quality checks passed!"
	@echo "✅ Code is ready for commit"
	@echo ""
	@echo "To commit:"
	@echo "  git add -A"
	@echo "  git commit -m 'Your commit message'"
	@echo "  git push origin your-branch"

# Build and release
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf dist/ build/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✅ Clean complete!"

build: clean
	@echo "📦 Building package..."
	python -m build
	@echo "🔍 Checking package..."
	python -m twine check dist/*
	@echo "✅ Package built successfully!"
	@echo "📄 Artifacts in dist/ directory"

upload: build
	@echo "📤 Uploading to PyPI..."
	python -m twine upload dist/*
	@echo "✅ Package uploaded to PyPI!"

# Development helpers
pre-commit-install:
	@echo "🔧 Installing pre-commit hooks..."
	pre-commit install
	@echo "✅ Pre-commit hooks installed!"
	@echo "Code will be automatically formatted on commit"

example-monitor:
	@echo "🏠 Running production tank monitor (5 minutes)..."
	python examples/tank_monitoring_production.py --interval 60 --duration 5

example-basic:
	@echo "🔧 Running basic usage example..."
	python examples/basic_usage.py

# CI simulation (what GitHub Actions runs)
ci: check
	@echo ""
	@echo "🤖 CI simulation complete!"
	@echo "This is what GitHub Actions will check"