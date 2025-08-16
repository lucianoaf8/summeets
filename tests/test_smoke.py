"""Smoke tests for summeets core functionality."""
import pytest
from pathlib import Path

from core.utils.config import SETTINGS
from core.audio.ffmpeg_ops import probe
from core.providers.openai_client import client as openai_client
from core.providers.anthropic_client import client as anthropic_client
from core.utils.fsio import get_data_manager
from core.models import TranscriptionJob, SummarizationJob, ProcessingStatus


def test_settings_loading():
    """Test that settings can be loaded."""
    assert SETTINGS.provider in ["openai", "anthropic"]
    assert SETTINGS.data_dir == Path("data")
    assert SETTINGS.output_dir == Path("data/output")


def test_ffmpeg_probe():
    """Test FFmpeg probe functionality if available."""
    try:
        # This will fail if ffmpeg isn't installed, which is fine
        result = probe("nonexistent.mp3")
        assert "No such file" in result or "does not exist" in result.lower()
    except (FileNotFoundError, RuntimeError):
        pytest.skip("FFmpeg not available")


def test_openai_client_creation():
    """Test OpenAI client can be created."""
    # This might fail without API key, which is expected in testing
    try:
        client = openai_client()
        assert client is not None
    except Exception:
        pytest.skip("OpenAI client setup failed (likely missing API key)")


def test_anthropic_client_creation():
    """Test Anthropic client can be created."""
    # This might fail without API key, which is expected in testing
    try:
        client = anthropic_client()
        assert client is not None
    except Exception:
        pytest.skip("Anthropic client setup failed (likely missing API key)")


def test_output_directory_creation():
    """Test output directory is created."""
    SETTINGS.output_dir.mkdir(parents=True, exist_ok=True)
    assert SETTINGS.output_dir.exists()
    assert SETTINGS.output_dir.is_dir()


def test_data_manager_creation():
    """Test data manager can be created."""
    dm = get_data_manager()
    assert dm.base_dir == Path("data")
    assert dm.input_dir.exists()
    assert dm.output_dir.exists()
    assert dm.temp_dir.exists()


def test_job_models():
    """Test job model creation."""
    audio_file = Path("test.mp3")
    output_dir = Path("output")
    
    # Test transcription job
    trans_job = TranscriptionJob(
        audio_file=audio_file,
        output_dir=output_dir
    )
    assert trans_job.status == ProcessingStatus.PENDING
    assert trans_job.audio_file == audio_file
    
    # Test summarization job
    summary_job = SummarizationJob(
        transcript_file=Path("transcript.json"),
        output_dir=output_dir
    )
    assert summary_job.status == ProcessingStatus.PENDING


if __name__ == "__main__":
    pytest.main([__file__])