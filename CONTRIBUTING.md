# Contributing to Drishti

Thank you for your interest in contributing to Drishti! 🙏

## Development Setup

```bash
# Clone the repo
git clone https://github.com/aarambh-darshan/drishti.git
cd drishti

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in dev mode with all optional dependencies
pip install -e ".[dev,all]"

# Run tests
pytest tests/ -v
```

## Running Tests

```bash
# Full test suite
pytest tests/ -v

# With coverage
pytest tests/ --cov=drishti --cov-report=term-missing

# Specific test file
pytest tests/test_cost.py -v
```

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check linting
ruff check drishti/ tests/

# Auto-fix issues
ruff check --fix drishti/ tests/

# Check formatting
ruff format --check drishti/ tests/

# Auto-format
ruff format drishti/ tests/
```

## Adding a New Provider

1. Create `drishti/providers/<provider>.py` implementing `BaseInterceptor`
2. Add the interceptor to `ALL_INTERCEPTORS` in `drishti/providers/__init__.py`
3. Add pricing data to `drishti/cost/pricing.py`
4. Create `tests/providers/test_<provider>.py`
5. Add an example in `examples/`
6. Update `pyproject.toml` optional dependencies

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests and linter
5. Commit with a descriptive message
6. Push and open a PR

## Reporting Bugs

Please open an issue with:
- Python version
- Provider SDK version
- Minimal reproduction code
- Expected vs actual behavior
