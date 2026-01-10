# Summeets Testing Documentation

## Overview

This document provides comprehensive documentation for the Summeets testing suite, covering all test types, execution methods, and testing strategies implemented for the audio/video transcription and summarization application.

## Table of Contents

- [Test Architecture](#test-architecture)
- [Test Types](#test-types)
- [Test Coverage](#test-coverage)
- [Running Tests](#running-tests)
- [Test Configuration](#test-configuration)
- [Writing New Tests](#writing-new-tests)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## Test Architecture

The Summeets testing suite follows a layered approach with clear separation of concerns:

```
tests/
├── unit/                    # Unit tests (isolated component testing)
├── integration/             # Integration tests (component interaction)
├── e2e/                     # End-to-end tests (complete workflows)
├── performance/             # Performance and scalability tests
├── fixtures/                # Shared test data and utilities
├── conftest.py             # Global test configuration
└── __init__.py             # Test package initialization
```

### Testing Principles

1. **Isolation**: Each test is independent and doesn't rely on external state
2. **Mocking**: External services (APIs, file system) are mocked for reliability
3. **Realistic Data**: Test fixtures simulate real-world scenarios
4. **Performance Awareness**: Tests monitor memory usage and execution time
5. **CI/CD Ready**: Automated execution with coverage reporting

## Test Types

### 1. Unit Tests (`tests/unit/`)

**Purpose**: Test individual components in isolation

**Coverage Areas**:
- **Data Models** (`test_models.py`)
  - Pydantic model validation
  - Data serialization/deserialization
  - Model relationships and constraints
  - Edge cases and error handling

- **Workflow Engine** (`test_workflow.py`)
  - Workflow step execution
  - Conditional logic and branching
  - Configuration validation
  - Error propagation and recovery

- **Audio Processing** (`test_audio/`)
  - FFmpeg operations (extraction, normalization, compression)
  - Audio file selection and ranking
  - Format conversion and quality optimization
  - Metadata extraction and validation

- **Transcription** (`test_transcribe/`)
  - Replicate API integration
  - Audio preprocessing for transcription
  - Progress tracking and callbacks
  - Error handling and retry logic

- **Summarization** (`test_summarize/`)
  - LLM provider integration (OpenAI, Anthropic)
  - Chain-of-Density processing
  - Template-based summarization
  - Token usage tracking

- **Utilities** (`test_utils/`)
  - Configuration management
  - File system operations
  - Logging and error handling
  - Validation functions

**Execution Time**: ~30 seconds  
**Mock Level**: High (all external dependencies mocked)

### 2. Integration Tests (`tests/integration/`)

**Purpose**: Test component interactions and data flow

**Coverage Areas**:
- **Pipeline Integration** (`test_pipeline_integration.py`)
  - Audio → Transcription → Summarization workflow
  - Data transformation between components
  - Error propagation across pipeline stages
  - Progress tracking throughout workflow

- **API Integration** (`test_api_integration.py`)
  - Replicate transcription service integration
  - OpenAI/Anthropic summarization services
  - Rate limiting and retry mechanisms
  - Authentication and error handling

- **File System Integration** (`test_file_integration.py`)
  - Input/output file handling
  - Directory structure management
  - Temporary file cleanup
  - File format validation

**Execution Time**: ~2 minutes  
**Mock Level**: Medium (external APIs mocked, file system partially real)

### 3. End-to-End Tests (`tests/e2e/`)

**Purpose**: Test complete user workflows from start to finish

**Coverage Areas**:
- **CLI Interface** (`test_cli_interface.py`)
  - Command-line argument parsing
  - Complete processing workflows
  - Error messages and user feedback
  - File input/output validation
  - Progress indicators and logging

- **GUI Interface** (`test_gui_interface.py`)
  - Electron application lifecycle
  - File selection and drag-drop
  - Processing workflow initiation
  - Progress tracking and cancellation
  - Results display and export
  - Configuration management
  - Error handling and user feedback
  - Accessibility features

**Execution Time**: ~5 minutes  
**Mock Level**: Low (simulates real user interactions)

### 4. Performance Tests (`tests/performance/`)

**Purpose**: Validate performance characteristics and scalability

**Coverage Areas**:
- **Audio Processing Performance** (`test_performance.py`)
  - Large file processing efficiency
  - Memory usage during audio operations
  - Compression and format conversion speed
  - Audio selection algorithm performance

- **Transcription Performance**
  - Large transcript processing
  - Memory efficiency with long audio files
  - Chunking algorithm optimization
  - Progress callback overhead

- **Summarization Performance**
  - Large transcript summarization
  - Chain-of-Density processing efficiency
  - Token usage optimization
  - Memory usage during LLM operations

- **Workflow Performance**
  - End-to-end processing benchmarks
  - Concurrent workflow execution
  - Memory cleanup validation
  - Resource utilization monitoring

- **Scalability Tests**
  - Maximum file size handling
  - Concurrent processing limits
  - Memory usage patterns
  - Performance degradation thresholds

**Execution Time**: ~10 minutes  
**Mock Level**: High (focuses on algorithmic performance)

## Test Coverage

### Code Coverage Targets

- **Overall Coverage**: ≥80%
- **Critical Paths**: ≥95%
- **Error Handling**: ≥90%
- **User Interfaces**: ≥85%

### Coverage Areas

| Component | Unit Tests | Integration Tests | E2E Tests | Performance Tests |
|-----------|------------|-------------------|-----------|-------------------|
| Core Models | ✅ | ✅ | ✅ | ✅ |
| Workflow Engine | ✅ | ✅ | ✅ | ✅ |
| Audio Processing | ✅ | ✅ | ✅ | ✅ |
| Transcription | ✅ | ✅ | ✅ | ✅ |
| Summarization | ✅ | ✅ | ✅ | ✅ |
| CLI Interface | ✅ | ✅ | ✅ | ❌ |
| GUI Interface | ✅ | ✅ | ✅ | ❌ |
| Configuration | ✅ | ✅ | ✅ | ❌ |
| Error Handling | ✅ | ✅ | ✅ | ✅ |
| File Operations | ✅ | ✅ | ✅ | ✅ |

## Running Tests

### Test Runner Script

The project includes a comprehensive test runner (`run_tests.py`) with multiple execution modes:

```bash
# Install test dependencies
pip install -e ".[test]"

# Basic test execution
python run_tests.py unit                    # Unit tests only
python run_tests.py integration             # Integration tests
python run_tests.py e2e                     # End-to-end tests
python run_tests.py performance             # Performance tests
python run_tests.py all                     # All test types

# Advanced options
python run_tests.py all -v                  # Verbose output
python run_tests.py unit --no-coverage      # Skip coverage
python run_tests.py parallel -j 4           # Parallel execution
python run_tests.py quick                   # Fast subset (no slow tests)

# Quality and analysis
python run_tests.py coverage                # Coverage report
python run_tests.py lint                    # Code quality checks
python run_tests.py security                # Security scan
python run_tests.py validate                # Test structure validation

# Maintenance
python run_tests.py clean                   # Clean test artifacts
```

### Direct Pytest Execution

```bash
# Run specific test categories
pytest tests/unit/ -v
pytest tests/integration/ --run-integration
pytest tests/e2e/ --run-e2e
pytest tests/performance/ --run-performance

# Run specific test files
pytest tests/unit/test_models.py -v
pytest tests/integration/test_pipeline_integration.py

# Run with coverage
pytest tests/unit/ --cov=core --cov-report=html

# Run specific test functions
pytest tests/unit/test_models.py::TestTranscriptData::test_segment_validation -v
```

### Test Markers

Tests are organized using pytest markers:

```bash
# Run by marker
pytest -m unit                   # Unit tests only
pytest -m integration            # Integration tests only
pytest -m e2e                    # End-to-end tests only
pytest -m performance            # Performance tests only
pytest -m slow                   # Slow-running tests
pytest -m external               # Tests requiring external services

# Exclude markers
pytest -m "not slow"             # Skip slow tests
pytest -m "not external"         # Skip external service tests
```

## Test Configuration

### Pytest Configuration (`pytest.ini`)

```ini
[tool:pytest]
testpaths = tests
addopts = 
    --strict-markers
    --cov=core --cov=cli
    --cov-fail-under=80
    --tb=short
    --verbose

markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    performance: Performance tests
    slow: Slow running tests
    external: Tests requiring external services
```

### Global Test Configuration (`conftest.py`)

Key fixtures available across all tests:

- `temp_dir`: Temporary directory for test files
- `audio_file_samples`: Sample audio files in various formats
- `mock_ffprobe`: Mocked FFmpeg metadata extraction
- `mock_replicate_output`: Realistic transcription API responses
- `mock_settings`: Application configuration for testing
- `sample_transcript_data`: Comprehensive transcript test data
- `mock_api_responses`: External API response simulation
- `test_utils`: Utility functions for test setup

### Environment Variables

Tests use environment-specific settings:

```bash
# Required for API integration tests
export OPENAI_API_KEY="test-key"
export ANTHROPIC_API_KEY="test-key" 
export REPLICATE_API_TOKEN="test-token"

# Test-specific settings
export TESTING="1"
export LOG_LEVEL="WARNING"
```

## Writing New Tests

### Test Structure Guidelines

1. **File Naming**: `test_<module_name>.py`
2. **Class Naming**: `Test<ComponentName>`
3. **Method Naming**: `test_<specific_behavior>`
4. **Docstrings**: Required for all test classes and methods

### Unit Test Template

```python
"""
Unit tests for [component name].
[Brief description of what this module tests]
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

class TestComponentName:
    """Test [component] functionality."""
    
    def test_specific_behavior(self):
        """Test [specific behavior description]."""
        # Arrange
        input_data = "test_input"
        expected_result = "expected_output"
        
        # Act
        result = component_function(input_data)
        
        # Assert
        assert result == expected_result
    
    @patch('module.external_dependency')
    def test_with_mocked_dependency(self, mock_dependency):
        """Test behavior with mocked external dependency."""
        mock_dependency.return_value = "mocked_response"
        
        result = component_function_with_dependency()
        
        assert result is not None
        mock_dependency.assert_called_once()
```

### Integration Test Template

```python
"""
Integration tests for [component interaction].
[Description of integration scenarios tested]
"""
import pytest
from pathlib import Path
import tempfile

class TestComponentIntegration:
    """Test integration between components."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        # Additional setup
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.integration
    def test_component_interaction(self):
        """Test interaction between ComponentA and ComponentB."""
        # Test implementation
        pass
```

### Performance Test Template

```python
"""
Performance tests for [component].
[Description of performance characteristics tested]
"""
import pytest
import time
import psutil
from contextlib import contextmanager

@contextmanager
def measure_time():
    """Measure execution time."""
    start = time.perf_counter()
    yield lambda: time.perf_counter() - start

@contextmanager 
def measure_memory():
    """Measure memory usage."""
    process = psutil.Process()
    start_memory = process.memory_info().rss
    yield lambda: process.memory_info().rss - start_memory

class TestComponentPerformance:
    """Test performance characteristics."""
    
    @pytest.mark.performance
    def test_processing_speed(self):
        """Test processing completes within time limit."""
        with measure_time() as get_duration:
            # Perform operation
            result = expensive_operation()
        
        duration = get_duration()
        assert duration < 5.0  # Should complete in under 5 seconds
        assert result is not None
    
    @pytest.mark.performance
    def test_memory_usage(self):
        """Test memory usage stays within limits."""
        with measure_memory() as get_memory:
            # Perform memory-intensive operation
            result = memory_intensive_operation()
        
        memory_used = get_memory()
        assert memory_used < 100 * 1024 * 1024  # Less than 100MB
```

### Mock Strategy Guidelines

1. **External APIs**: Always mock external service calls
2. **File System**: Mock for unit tests, use temp directories for integration
3. **Time-dependent**: Mock `time.sleep()` and `datetime.now()`
4. **Network Operations**: Mock all HTTP requests
5. **System Commands**: Mock `subprocess` calls

## CI/CD Integration

### GitHub Actions Configuration

```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e ".[test]"
    
    - name: Run test suite
      run: |
        python run_tests.py all --no-coverage
    
    - name: Generate coverage report
      run: |
        python run_tests.py coverage
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tests
        name: Run test suite
        entry: python run_tests.py quick
        language: system
        pass_filenames: false
```

## Test Data Management

### Fixtures and Test Data

Test data is organized in the `tests/fixtures/` directory:

```
tests/fixtures/
├── audio/              # Sample audio files
│   ├── short_meeting.mp3
│   ├── long_presentation.wav
│   └── multi_speaker.flac
├── video/              # Sample video files
│   ├── screen_recording.mp4
│   └── conference_call.mkv
├── transcripts/        # Sample transcript data
│   ├── basic_meeting.json
│   ├── technical_discussion.json
│   └── multilingual_content.json
└── summaries/          # Expected summary outputs
    ├── quarterly_review.json
    └── project_planning.json
```

### Data Generation

For tests requiring large datasets:

```python
def generate_large_transcript(num_segments=1000):
    """Generate large transcript for performance testing."""
    segments = []
    for i in range(num_segments):
        segments.append({
            "start": i * 5.0,
            "end": (i + 1) * 5.0,
            "text": f"This is segment {i} with sample content.",
            "speaker": f"SPEAKER_{i % 5}",
            "words": generate_words_for_segment(i)
        })
    return {"segments": segments}
```

## Troubleshooting

### Common Issues

#### 1. Test Failures Due to Missing Dependencies

**Problem**: `ModuleNotFoundError` for test dependencies
**Solution**: 
```bash
pip install -e ".[test]"
# or install specific dependencies
pip install pytest pytest-cov pytest-mock
```

#### 2. Slow Test Execution

**Problem**: Tests take too long to complete
**Solution**:
```bash
# Run quick subset
python run_tests.py quick

# Run in parallel
python run_tests.py parallel -j 4

# Skip slow tests
pytest -m "not slow"
```

#### 3. Coverage Issues

**Problem**: Coverage below threshold
**Solution**:
```bash
# Generate detailed coverage report
python run_tests.py coverage

# View HTML coverage report
open htmlcov/index.html

# Identify uncovered lines
pytest --cov=core --cov-report=term-missing
```

#### 4. Mock-related Failures

**Problem**: Tests fail due to incorrect mocking
**Solution**:
- Verify mock patch targets match actual import paths
- Use `side_effect` for complex mock behaviors
- Check mock assertion methods (`assert_called_once()`, etc.)

#### 5. Environment-specific Failures

**Problem**: Tests pass locally but fail in CI
**Solution**:
- Check environment variable configuration
- Verify file path separators (Windows vs. Unix)
- Ensure all dependencies are properly declared

### Debug Mode

Enable detailed logging for test debugging:

```bash
# Enable debug logging
LOG_LEVEL=DEBUG python run_tests.py unit -v

# Run with pytest debug options
pytest tests/unit/test_models.py -v -s --tb=long
```

### Test Isolation Issues

If tests interfere with each other:

```bash
# Run tests in random order
pytest --random-order

# Run specific test in isolation
pytest tests/unit/test_models.py::TestTranscriptData::test_validation -v
```

## Best Practices

### Test Writing Best Practices

1. **AAA Pattern**: Arrange, Act, Assert
2. **Single Responsibility**: One assertion per test method
3. **Descriptive Names**: Test names should describe the scenario
4. **Independent Tests**: No test should depend on another
5. **Mock External Dependencies**: Don't rely on external services
6. **Use Fixtures**: Share setup code through fixtures
7. **Test Edge Cases**: Include boundary conditions and error cases

### Performance Test Best Practices

1. **Baseline Measurements**: Establish performance baselines
2. **Statistical Significance**: Run performance tests multiple times
3. **Resource Monitoring**: Monitor memory, CPU, and I/O usage
4. **Scalability Testing**: Test with varying input sizes
5. **Regression Detection**: Compare against previous benchmarks

### Maintenance Best Practices

1. **Regular Review**: Review and update tests regularly
2. **Coverage Monitoring**: Maintain coverage above thresholds
3. **Test Documentation**: Keep test documentation current
4. **Dependency Updates**: Update test dependencies regularly
5. **Performance Baselines**: Update baselines when architecture changes

## Conclusion

The Summeets testing suite provides comprehensive coverage across all application layers, ensuring reliability, performance, and maintainability. The testing infrastructure supports both development workflow and production deployment confidence through automated validation of all features and integration points.

For questions or issues with the testing suite, refer to the troubleshooting section or review the test implementation files for specific examples and patterns.