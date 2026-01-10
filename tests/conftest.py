"""
Global pytest configuration and shared fixtures.
Provides test setup, cleanup, and common test utilities.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import logging
import json

# Configure test logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Disable logging during tests unless specifically needed
logging.getLogger('core').setLevel(logging.WARNING)

# Test plugins
pytest_plugins = []


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp(prefix="summeets_test_"))
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def audio_file_samples(temp_dir):
    """Create sample audio files for testing."""
    samples = {}
    
    # Create files with different extensions
    formats = ['.mp3', '.wav', '.flac', '.m4a', '.ogg']
    for fmt in formats:
        file_path = temp_dir / f"sample{fmt}"
        file_path.write_bytes(b"fake audio data")
        samples[fmt] = file_path
    
    # Create a normalized version
    norm_file = temp_dir / "sample_norm.mp3"
    norm_file.write_bytes(b"fake normalized audio data")
    samples['norm'] = norm_file
    
    return samples


@pytest.fixture
def mock_ffprobe():
    """Mock ffprobe_info function with realistic output."""
    def mock_info(path):
        # Return different info based on file type
        if "flac" in str(path).lower():
            return {
                "duration": 180.0,
                "bit_rate": 800000,
                "sample_rate": 48000,
                "channels": 2,
                "codec": "flac",
                "size": 15000000
            }
        elif "mp3" in str(path).lower():
            return {
                "duration": 180.0,
                "bit_rate": 128000,
                "sample_rate": 44100,
                "channels": 2,
                "codec": "mp3",
                "size": 3000000
            }
        else:
            return {
                "duration": 180.0,
                "bit_rate": 192000,
                "sample_rate": 44100,
                "channels": 2,
                "codec": "unknown",
                "size": 4000000
            }
    
    with patch('core.audio.ffmpeg_ops.ffprobe_info', side_effect=mock_info) as mock:
        yield mock


@pytest.fixture
def mock_replicate_output():
    """Mock realistic Replicate API output."""
    return {
        "segments": [
            {
                "start": 0.0,
                "end": 5.432,
                "text": "Hello, welcome to our meeting today.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"start": 0.0, "end": 0.8, "word": "Hello,"},
                    {"start": 0.8, "end": 1.5, "word": "welcome"},
                    {"start": 1.5, "end": 1.8, "word": "to"},
                    {"start": 1.8, "end": 2.1, "word": "our"},
                    {"start": 2.1, "end": 2.8, "word": "meeting"},
                    {"start": 2.8, "end": 5.432, "word": "today."}
                ]
            },
            {
                "start": 5.432,
                "end": 12.156,
                "text": "I'd like to discuss the quarterly results with everyone.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"start": 5.432, "end": 5.9, "word": "I'd"},
                    {"start": 5.9, "end": 6.2, "word": "like"},
                    {"start": 6.2, "end": 6.4, "word": "to"},
                    {"start": 6.4, "end": 7.1, "word": "discuss"},
                    {"start": 7.1, "end": 7.3, "word": "the"},
                    {"start": 7.3, "end": 8.2, "word": "quarterly"},
                    {"start": 8.2, "end": 8.8, "word": "results"},
                    {"start": 8.8, "end": 9.1, "word": "with"},
                    {"start": 9.1, "end": 12.156, "word": "everyone."}
                ]
            },
            {
                "start": 12.156,
                "end": 18.901,
                "text": "That sounds great. I have some questions about the numbers.",
                "speaker": "SPEAKER_01",
                "words": [
                    {"start": 12.156, "end": 12.5, "word": "That"},
                    {"start": 12.5, "end": 13.2, "word": "sounds"},
                    {"start": 13.2, "end": 13.8, "word": "great."},
                    {"start": 13.8, "end": 14.0, "word": "I"},
                    {"start": 14.0, "end": 14.3, "word": "have"},
                    {"start": 14.3, "end": 14.7, "word": "some"},
                    {"start": 14.7, "end": 15.5, "word": "questions"},
                    {"start": 15.5, "end": 15.8, "word": "about"},
                    {"start": 15.8, "end": 16.1, "word": "the"},
                    {"start": 16.1, "end": 18.901, "word": "numbers."}
                ]
            }
        ]
    }


@pytest.fixture
def mock_settings():
    """Mock application settings for testing."""
    from src.utils.config import Settings
    
    settings = Settings()
    settings.ffmpeg_bin = "ffmpeg"
    settings.ffprobe_bin = "ffprobe"
    settings.max_upload_mb = 24.0
    settings.data_dir = Path("/tmp/summeets_test")
    settings.out_dir = Path("/tmp/summeets_test/output")
    
    with patch('core.config.SETTINGS', settings):
        yield settings


@pytest.fixture
def mock_replicate_api():
    """Mock Replicate API client."""
    mock_client = Mock()
    
    # Mock model and version
    mock_model = Mock()
    mock_version = Mock()
    mock_version.id = "test-version-123"
    mock_model.latest_version = mock_version
    
    mock_client.models.get.return_value = mock_model
    
    # Mock prediction
    mock_prediction = Mock()
    mock_prediction.id = "test-prediction-456"
    mock_prediction.status = "succeeded"
    
    mock_client.predictions.create.return_value = mock_prediction
    
    return mock_client


@pytest.fixture
def enable_logging():
    """Enable detailed logging for specific tests."""
    # Store original levels
    original_levels = {}
    loggers_to_enable = ['core.audio', 'core.transcription', 'core.validation']
    
    for logger_name in loggers_to_enable:
        logger = logging.getLogger(logger_name)
        original_levels[logger_name] = logger.level
        logger.setLevel(logging.DEBUG)
    
    yield
    
    # Restore original levels
    for logger_name, level in original_levels.items():
        logging.getLogger(logger_name).setLevel(level)


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks after each test."""
    yield
    # This runs after each test
    patch.stopall()


# Extended test configuration and fixtures

@pytest.fixture(scope="session")
def test_data_dir():
    """Provide path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def temp_test_dir():
    """Create and provide temporary directory for test session."""
    temp_dir = Path(tempfile.mkdtemp(prefix="summeets_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_env_vars():
    """Provide common environment variables for testing."""
    return {
        'OPENAI_API_KEY': 'test-openai-key',
        'ANTHROPIC_API_KEY': 'test-anthropic-key',
        'REPLICATE_API_TOKEN': 'test-replicate-token',
        'LLM_PROVIDER': 'openai',
        'LLM_MODEL': 'gpt-4o-mini',
        'SUMMARY_MAX_OUTPUT_TOKENS': '3000',
        'SUMMARY_CHUNK_SECONDS': '1800',
        'SUMMARY_COD_PASSES': '2'
    }


@pytest.fixture
def sample_transcript_data():
    """Provide comprehensive sample transcript data."""
    return {
        "segments": [
            {
                "start": 0.0,
                "end": 5.432,
                "text": "Good morning everyone, and welcome to our quarterly review meeting.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"start": 0.0, "end": 0.5, "word": "Good"},
                    {"start": 0.5, "end": 1.0, "word": "morning"},
                    {"start": 1.0, "end": 1.8, "word": "everyone,"},
                    {"start": 1.8, "end": 2.5, "word": "welcome"},
                    {"start": 2.5, "end": 2.8, "word": "to"},
                    {"start": 2.8, "end": 3.2, "word": "our"},
                    {"start": 3.2, "end": 4.0, "word": "quarterly"},
                    {"start": 4.0, "end": 4.5, "word": "review"},
                    {"start": 4.5, "end": 5.432, "word": "meeting."}
                ]
            },
            {
                "start": 5.432,
                "end": 12.156,
                "text": "I'd like to start by reviewing our performance metrics from Q3.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"start": 5.432, "end": 6.0, "word": "I'd"},
                    {"start": 6.0, "end": 6.5, "word": "like"},
                    {"start": 6.5, "end": 6.8, "word": "to"},
                    {"start": 6.8, "end": 7.3, "word": "start"},
                    {"start": 7.3, "end": 7.6, "word": "by"},
                    {"start": 7.6, "end": 8.3, "word": "reviewing"},
                    {"start": 8.3, "end": 8.6, "word": "our"},
                    {"start": 8.6, "end": 9.4, "word": "performance"},
                    {"start": 9.4, "end": 10.0, "word": "metrics"},
                    {"start": 10.0, "end": 10.5, "word": "from"},
                    {"start": 10.5, "end": 12.156, "word": "Q3."}
                ]
            },
            {
                "start": 25.123,
                "end": 30.456,
                "text": "Does anyone have questions about these customer acquisition numbers?",
                "speaker": "SPEAKER_01",
                "words": [
                    {"start": 25.123, "end": 25.5, "word": "Does"},
                    {"start": 25.5, "end": 26.0, "word": "anyone"},
                    {"start": 26.0, "end": 26.3, "word": "have"},
                    {"start": 26.3, "end": 26.9, "word": "questions"},
                    {"start": 26.9, "end": 27.3, "word": "about"},
                    {"start": 27.3, "end": 27.7, "word": "these"},
                    {"start": 27.7, "end": 28.4, "word": "customer"},
                    {"start": 28.4, "end": 29.2, "word": "acquisition"},
                    {"start": 29.2, "end": 30.456, "word": "numbers?"}
                ]
            }
        ]
    }


@pytest.fixture
def mock_api_responses():
    """Provide mock API responses for external services."""
    return {
        "replicate_transcription": {
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Mock transcription result",
                    "speaker": "SPEAKER_00",
                    "words": []
                }
            ]
        },
        "openai_summary": {
            "summary": "Mock OpenAI summary result",
            "usage": {"total_tokens": 150},
            "model": "gpt-4o-mini"
        },
        "anthropic_summary": {
            "summary": "Mock Anthropic summary result",
            "usage": {"input_tokens": 100, "output_tokens": 75},
            "model": "claude-3-haiku"
        }
    }


@pytest.fixture
def mock_progress_callback():
    """Provide mock progress callback for testing."""
    progress_calls = []
    
    def callback(step, total, step_name, status):
        progress_calls.append({
            'step': step,
            'total': total,
            'step_name': step_name,
            'status': status
        })
    
    callback.calls = progress_calls
    return callback


# Test utilities
class TestUtils:
    """Utility functions for testing."""
    
    @staticmethod
    def create_mock_audio_file(file_path: Path, duration: float = 300.0):
        """Create a mock audio file with metadata."""
        file_path.write_bytes(b"fake audio data")
        return {
            'path': file_path,
            'duration': duration,
            'size': len(b"fake audio data"),
            'format': file_path.suffix[1:]  # Remove leading dot
        }
    
    @staticmethod
    def create_mock_transcript_file(file_path: Path, segments: list = None):
        """Create a mock transcript file."""
        if segments is None:
            segments = [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Test transcript segment",
                    "speaker": "SPEAKER_00",
                    "words": []
                }
            ]
        
        transcript_data = {"segments": segments}
        file_path.write_text(json.dumps(transcript_data, indent=2))
        return transcript_data
    
    @staticmethod
    def assert_file_exists_and_not_empty(file_path: Path):
        """Assert that file exists and has content."""
        assert file_path.exists(), f"File does not exist: {file_path}"
        assert file_path.stat().st_size > 0, f"File is empty: {file_path}"
    
    @staticmethod
    def assert_valid_json_file(file_path: Path):
        """Assert that file contains valid JSON."""
        TestUtils.assert_file_exists_and_not_empty(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"File contains invalid JSON: {file_path} - {e}")


@pytest.fixture
def test_utils():
    """Provide TestUtils instance."""
    return TestUtils


# Markers for different test categories
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "external: mark test as requiring external services")
    config.addinivalue_line("markers", "requires_api: mark test as requiring external API")


# Custom test collection and options
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-performance",
        action="store_true",
        default=False,
        help="Run performance tests"
    )
    parser.addoption(
        "--run-slow",
        action="store_true", 
        default=False,
        help="Run slow tests"
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests"
    )
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run end-to-end tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers and skip conditions."""
    skip_performance = pytest.mark.skip(reason="Performance tests skipped by default")
    skip_slow = pytest.mark.skip(reason="Slow tests skipped by default")
    skip_integration = pytest.mark.skip(reason="Integration tests skipped by default")
    skip_e2e = pytest.mark.skip(reason="E2E tests skipped by default")
    
    for item in items:
        # Add directory-based markers
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            if not config.getoption("--run-integration"):
                item.add_marker(skip_integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            if not config.getoption("--run-e2e"):
                item.add_marker(skip_e2e)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            if not config.getoption("--run-performance"):
                item.add_marker(skip_performance)
        
        # Skip tests based on markers
        if "performance" in item.keywords and not config.getoption("--run-performance"):
            item.add_marker(skip_performance)
        
        if "slow" in item.keywords and not config.getoption("--run-slow"):
            item.add_marker(skip_slow)
        
        # Mark external API tests
        if any(keyword in item.name.lower() for keyword in ["replicate", "openai", "anthropic"]):
            item.add_marker(pytest.mark.external)


# Test environment setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment before any tests run."""
    # Set test-specific environment variables
    import os
    os.environ["TESTING"] = "1"
    os.environ["LOG_LEVEL"] = "WARNING"
    
    yield
    
    # Cleanup after all tests
    if "TESTING" in os.environ:
        del os.environ["TESTING"]