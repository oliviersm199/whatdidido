# Test Suite

This directory contains the test suite for the whatdidido project.

## Running Tests

To run the tests locally:

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_config.py

# Run specific test class or function
pytest tests/test_config.py::TestConfigModels::test_openai_config_defaults
```

## Test Structure

- `test_config.py` - Tests for the configuration module, including:
  - Pydantic model validation
  - Environment variable loading
  - Config file management
  - Integration tests

## Coverage

Current test coverage:

- `config.py`: 100%

## GitHub Actions

Tests run automatically on:

- Push to main branch
- Pull requests to main branch

See [.github/workflows/tests.yml](../.github/workflows/tests.yml) for the CI configuration.

## Writing Tests

When adding new tests:

1. Create test files with the `test_*.py` naming pattern
2. Organize tests into classes with `Test*` prefix
3. Name test functions with `test_*` prefix
4. Use pytest fixtures for common setup
5. Mock external dependencies and file I/O
6. Ensure proper test isolation (use `tmp_path`, `patch.dict` for env vars)

## Test Configuration

Test settings are configured in `pyproject.toml` under `[tool.pytest.ini_options]`.
