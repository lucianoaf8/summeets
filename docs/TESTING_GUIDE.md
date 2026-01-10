# Summeets Testing Guide

## Test Structure

```
tests/
├── unit/              # Unit tests for individual components
├── integration/       # Integration tests for component interactions
├── e2e/               # End-to-end workflow tests
├── performance/       # Performance benchmarks
├── playwright/        # Browser automation tests
├── fixtures/          # Test fixtures and mock services
├── reports/           # Test output artifacts
│   ├── htmlcov/       # HTML coverage reports
│   └── coverage.xml   # XML coverage data
├── conftest.py        # Shared pytest fixtures
├── pytest.ini         # Pytest configuration
├── .pytest_cache/     # Pytest cache (gitignored)
└── tests.log          # Test execution log

scripts/
└── run_tests.py       # Comprehensive test runner
```

## Running Tests

### Using Test Runner (Recommended)
```bash
python scripts/run_tests.py smoke      # Quick smoke tests
python scripts/run_tests.py unit       # Unit tests with coverage
python scripts/run_tests.py all        # All tests
python scripts/run_tests.py coverage   # Generate coverage report
python scripts/run_tests.py clean      # Clean test artifacts
```

### Full Test Suite
```bash
pytest
```

### Specific Test Categories
```bash
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m e2e            # End-to-end tests only
pytest -m performance    # Performance tests
pytest -m "not slow"     # Skip slow tests
```

### With Coverage
```bash
pytest --cov=src --cov=cli --cov-report=html:tests/reports/htmlcov
```

### Verbose Output
```bash
pytest -v --tb=long
```

## Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.unit` | Unit tests |
| `@pytest.mark.integration` | Integration tests |
| `@pytest.mark.e2e` | End-to-end tests |
| `@pytest.mark.performance` | Performance benchmarks |
| `@pytest.mark.slow` | Tests > 5 seconds |
| `@pytest.mark.external` | Requires external services |
| `@pytest.mark.requires_api` | Requires API access |

## Coverage Requirements

- Minimum coverage: **80%**
- Branch coverage enabled
- Reports generated to `tests/reports/`

## Test Artifacts

All test artifacts are centralized in `tests/`:

| Artifact | Location |
|----------|----------|
| Cache | `tests/.pytest_cache/` |
| HTML Coverage | `tests/reports/htmlcov/` |
| XML Coverage | `tests/reports/coverage.xml` |
| Test Log | `tests/tests.log` |

## Writing Tests

### Unit Test Example
```python
import pytest
from src.models import TranscriptSegment

@pytest.mark.unit
def test_segment_creation():
    segment = TranscriptSegment(
        speaker="SPEAKER_00",
        text="Hello world",
        start=0.0,
        end=1.5
    )
    assert segment.speaker == "SPEAKER_00"
    assert segment.duration == 1.5
```

### Integration Test Example
```python
import pytest
from src.workflow import WorkflowEngine

@pytest.mark.integration
def test_workflow_execution(tmp_path):
    engine = WorkflowEngine()
    result = engine.process(tmp_path / "test.m4a")
    assert result.success
```

## CI/CD Integration

Tests run automatically on:
- Pull requests
- Main branch commits

Coverage reports uploaded to `tests/reports/` on each run.
