"""
Pytest configuration and shared fixtures for Summeets tests.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import logging

# Configure test logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Disable logging during tests unless specifically needed
logging.getLogger('core').setLevel(logging.WARNING)


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
    from core.config import Settings
    
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


# Markers for different test categories
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "external: mark test as requiring external services")


# Custom test collection
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add unit marker to tests in unit/ directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to tests in integration/ directory
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Mark external API tests
        if "replicate" in item.name.lower() or "openai" in item.name.lower():
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