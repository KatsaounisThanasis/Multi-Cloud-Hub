# Testing Guide

Comprehensive guide for testing the Multi-Cloud Infrastructure Management API.

## Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Categories](#test-categories)
5. [Writing Tests](#writing-tests)
6. [Coverage Reports](#coverage-reports)
7. [CI/CD Integration](#cicd-integration)
8. [Troubleshooting](#troubleshooting)

## Overview

The project uses **pytest** as the testing framework with comprehensive test coverage including:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test API endpoints and component interactions
- **E2E Tests**: Test complete workflows including Docker containers

### Test Statistics

- **Target Coverage**: 70%+
- **Test Count**: 100+ tests
- **Test Categories**: Unit, Integration, E2E

## Test Structure

```
tests/
├── __init__.py
├── unit/                      # Unit tests
│   ├── __init__.py
│   ├── test_provider_factory.py
│   ├── test_azure_provider.py
│   ├── test_terraform_provider.py
│   └── test_template_manager.py
├── integration/               # Integration tests
│   ├── __init__.py
│   └── test_api_endpoints.py
└── e2e/                       # End-to-end tests
    ├── __init__.py
    └── test_docker_container.py
```

## Running Tests

### Quick Start

```bash
# Install test dependencies
make install-dev

# Run all tests
make test

# Run with coverage
make test-coverage
```

### Using Makefile

The Makefile provides convenient commands:

```bash
make test              # Run all tests
make test-unit         # Run unit tests only
make test-integration  # Run integration tests only
make test-e2e         # Run E2E tests only
make test-fast        # Skip slow and docker tests
make test-coverage    # Generate coverage report
```

### Using pytest directly

```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_provider_factory.py

# Specific test function
pytest tests/unit/test_provider_factory.py::TestProviderFactory::test_create_azure_provider

# Tests by marker
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Verbose output
pytest -v

# Show print statements
pytest -s

# Parallel execution (requires pytest-xdist)
pytest -n auto
```

### Using Test Script

```bash
# Make script executable (first time only)
chmod +x scripts/run_tests.sh

# Run tests
./scripts/run_tests.sh all          # All tests
./scripts/run_tests.sh unit         # Unit tests
./scripts/run_tests.sh coverage     # With coverage
./scripts/run_tests.sh docker       # Docker tests
./scripts/run_tests.sh ci           # CI pipeline mode
./scripts/run_tests.sh watch        # Watch mode
./scripts/run_tests.sh parallel     # Parallel execution

# Run specific marker
./scripts/run_tests.sh marker slow

# Run specific file
./scripts/run_tests.sh file tests/unit/test_provider_factory.py
```

## Test Categories

### Test Markers

Tests are categorized using pytest markers:

```python
@pytest.mark.unit          # Fast, isolated unit tests
@pytest.mark.integration   # API and integration tests
@pytest.mark.e2e          # End-to-end tests
@pytest.mark.slow         # Long-running tests
@pytest.mark.docker       # Requires Docker
@pytest.mark.azure        # Requires Azure credentials
@pytest.mark.aws          # Requires AWS credentials
@pytest.mark.gcp          # Requires GCP credentials
@pytest.mark.smoke        # Quick smoke tests
```

### Running by Category

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Skip Docker tests
pytest -m "not docker"

# Run smoke tests only
pytest -m smoke

# Combine markers
pytest -m "unit and not slow"
```

## Writing Tests

### Unit Test Example

```python
"""tests/unit/test_my_module.py"""
import pytest
from unittest.mock import Mock, patch
from backend.my_module import MyClass


class TestMyClass:
    """Test cases for MyClass"""

    def test_initialization(self):
        """Test class initialization"""
        obj = MyClass(param="value")
        assert obj.param == "value"

    @patch('backend.my_module.external_service')
    def test_with_mock(self, mock_service):
        """Test with mocked dependencies"""
        mock_service.return_value = "mocked"
        obj = MyClass()
        result = obj.call_external()
        assert result == "mocked"

    @pytest.mark.asyncio
    async def test_async_method(self):
        """Test async methods"""
        obj = MyClass()
        result = await obj.async_method()
        assert result is not None
```

### Integration Test Example

```python
"""tests/integration/test_api.py"""
from fastapi.testclient import TestClient
from backend.api_rest import app


class TestAPIEndpoint:
    """Test API endpoint"""

    def test_endpoint(self):
        """Test GET /api/v1/endpoint"""
        client = TestClient(app)
        response = client.get("/api/v1/endpoint")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
```

### Using Fixtures

```python
@pytest.fixture
def sample_data():
    """Provide sample data for tests"""
    return {
        "name": "test",
        "value": 123
    }

def test_with_fixture(sample_data):
    """Test using fixture"""
    assert sample_data["name"] == "test"
```

### Shared Fixtures

Common fixtures are available in `conftest.py`:

- `project_root`: Project root directory
- `templates_dir`: Templates directory
- `mock_azure_credentials`: Mock Azure credentials
- `mock_aws_credentials`: Mock AWS credentials
- `mock_gcp_credentials`: Mock GCP credentials
- `sample_deployment_parameters`: Sample parameters

## Coverage Reports

### Generating Coverage

```bash
# HTML report
pytest --cov=backend --cov-report=html

# Terminal report
pytest --cov=backend --cov-report=term-missing

# XML report (for CI)
pytest --cov=backend --cov-report=xml

# All reports
make test-coverage
```

### Viewing Coverage

```bash
# Open HTML report in browser
open htmlcov/index.html

# Or navigate to
# http://localhost:8000/htmlcov/index.html
```

### Coverage Configuration

Coverage settings in `pytest.ini`:

```ini
[coverage:run]
source = backend
omit = */tests/*, */venv/*

[coverage:report]
precision = 2
show_missing = True
skip_covered = False
fail_under = 70
```

## CI/CD Integration

### GitHub Actions

Automated testing runs on:
- Every push to `main` or `develop`
- Every pull request
- Manual workflow dispatch

Pipeline includes:
1. **Linting**: Black, isort, Flake8, Pylint
2. **Type Checking**: MyPy
3. **Unit Tests**: Python 3.9, 3.10, 3.11
4. **Integration Tests**
5. **Docker Build and Test**
6. **Security Scanning**: Bandit, Safety
7. **Coverage Report**: Uploaded to Codecov

### Running CI Locally

```bash
# Run full CI pipeline locally
make ci-test

# Or using script
./scripts/run_tests.sh ci
```

### Configuration Files

- `.github/workflows/ci.yml`: GitHub Actions workflow
- `pytest.ini`: Pytest configuration
- `conftest.py`: Shared test fixtures
- `requirements-test.txt`: Test dependencies

## Troubleshooting

### Common Issues

#### 1. Import Errors

```bash
# Ensure you're in project root
cd /path/to/project

# Install in development mode
pip install -e .
```

#### 2. Docker Tests Failing

```bash
# Check Docker is running
docker info

# Build Docker image first
make docker-build

# Run Docker tests
pytest tests/e2e/test_docker_container.py -v
```

#### 3. Async Tests Not Running

```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Check pytest.ini has
# asyncio_mode = auto
```

#### 4. Coverage Too Low

```bash
# See which files lack coverage
pytest --cov=backend --cov-report=term-missing

# Focus on uncovered code
# Add tests for missing lines
```

#### 5. Slow Tests

```bash
# Skip slow tests during development
pytest -m "not slow"

# Or use fast test target
make test-fast
```

### Test Dependencies

If tests fail due to missing dependencies:

```bash
# Reinstall test dependencies
pip install -r requirements-test.txt

# Or use make command
make install-dev
```

### Clean Test Cache

```bash
# Remove pytest cache
rm -rf .pytest_cache

# Remove coverage data
rm -rf .coverage htmlcov/

# Or use make command
make clean
```

## Best Practices

### 1. Test Naming

```python
# Good
def test_create_resource_group_success():
    pass

def test_deploy_with_invalid_parameters_raises_error():
    pass

# Bad
def test1():
    pass

def test_stuff():
    pass
```

### 2. Test Organization

- One test file per module
- Group related tests in classes
- Use descriptive class names: `TestFeatureName`

### 3. Assertions

```python
# Good - specific assertions
assert result.success is True
assert result.deployment_id == "test-123"
assert "error" in result.message

# Bad - vague assertions
assert result
assert len(result) > 0
```

### 4. Mocking

```python
# Mock external services
@patch('backend.providers.azure_native.ResourceManagementClient')
def test_with_mock(mock_client):
    # Test without real Azure calls
    pass
```

### 5. Test Independence

- Each test should run independently
- Don't rely on test execution order
- Clean up after tests (fixtures)

### 6. Documentation

```python
def test_feature():
    """
    Test that the feature works correctly.

    Given: Initial conditions
    When: Action performed
    Then: Expected outcome
    """
    pass
```

## Performance Tips

### 1. Parallel Execution

```bash
# Use all CPU cores
pytest -n auto

# Use specific number of workers
pytest -n 4
```

### 2. Skip Slow Tests

```bash
# During development
pytest -m "not slow and not docker"
```

### 3. Run Specific Tests

```bash
# Run only what you're working on
pytest tests/unit/test_specific.py::test_function
```

### 4. Use Test Cache

```bash
# Run only failed tests
pytest --lf

# Run failed first, then others
pytest --ff
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Python Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

## Getting Help

- Check existing tests for examples
- Review `conftest.py` for available fixtures
- See `pytest.ini` for configuration
- Run `pytest --markers` to see all markers
- Run `pytest --fixtures` to see all fixtures

## Next Steps

1. **Run your first tests**: `make test`
2. **Check coverage**: `make test-coverage`
3. **Write new tests**: Follow the examples
4. **Integrate with CI**: Push to GitHub

Happy Testing! 🧪
