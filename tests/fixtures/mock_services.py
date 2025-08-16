"""
Mock services for external API dependencies.
Provides realistic mocks for Replicate, OpenAI, and Anthropic APIs.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List, Optional
import json
import time
import asyncio
from pathlib import Path


@pytest.fixture
def mock_replicate_client():
    """Mock Replicate client with realistic responses."""
    client = Mock()
    
    # Mock model and version
    model = Mock()
    version = Mock()
    version.id = "test-whisper-version-123"
    model.latest_version = version
    client.models.get.return_value = model
    
    # Mock prediction creation
    prediction = Mock()
    prediction.id = "test-prediction-456"
    prediction.status = "starting"
    prediction.logs = "Initializing transcription..."
    prediction.output = None
    
    client.predictions.create.return_value = prediction
    
    # Mock prediction polling with progression
    def mock_get_prediction(prediction_id):
        if prediction_id == "test-prediction-456":
            # Simulate progression through states
            if not hasattr(mock_get_prediction, 'call_count'):
                mock_get_prediction.call_count = 0
            mock_get_prediction.call_count += 1
            
            if mock_get_prediction.call_count == 1:
                prediction.status = "processing"
                prediction.logs = "Processing audio file..."
            elif mock_get_prediction.call_count == 2:
                prediction.status = "processing"
                prediction.logs = "Running Whisper transcription..."
            elif mock_get_prediction.call_count >= 3:
                prediction.status = "succeeded"
                prediction.logs = "Transcription completed successfully"
                prediction.output = {
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 5.0,
                            "text": "This is a test transcription.",
                            "speaker": "SPEAKER_00",
                            "words": [
                                {"start": 0.0, "end": 1.0, "word": "This"},
                                {"start": 1.0, "end": 2.0, "word": "is"},
                                {"start": 2.0, "end": 3.0, "word": "a"},
                                {"start": 3.0, "end": 4.0, "word": "test"},
                                {"start": 4.0, "end": 5.0, "word": "transcription."}
                            ]
                        }
                    ]
                }
        return prediction
    
    client.predictions.get.side_effect = mock_get_prediction
    
    return client


@pytest.fixture
def mock_replicate_client_with_errors():
    """Mock Replicate client that simulates various error conditions."""
    client = Mock()
    
    # Model not found error
    def mock_model_error():
        from requests.exceptions import HTTPError
        raise HTTPError("Model not found")
    
    # Rate limit error
    def mock_rate_limit_error():
        from requests.exceptions import HTTPError
        error = HTTPError("Rate limit exceeded")
        error.response = Mock()
        error.response.status_code = 429
        raise error
    
    # File too large error
    def mock_file_size_error():
        raise ValueError("File size exceeds maximum limit of 25MB")
    
    # Network timeout error
    def mock_timeout_error():
        from requests.exceptions import Timeout
        raise Timeout("Request timeout")
    
    client.models.get.side_effect = mock_model_error
    client.predictions.create.side_effect = mock_rate_limit_error
    
    return {
        'model_not_found': client,
        'rate_limit': mock_rate_limit_error,
        'file_too_large': mock_file_size_error,
        'timeout': mock_timeout_error
    }


@pytest.fixture 
def mock_openai_client():
    """Mock OpenAI client with realistic chat completion responses."""
    client = Mock()
    
    # Mock chat completions
    response = Mock()
    choice = Mock()
    message = Mock()
    
    # Default summary response
    message.content = """# Meeting Summary

## Key Points
- Discussed quarterly performance metrics
- Customer acquisition increased by 23%
- Revenue growth of 15% this quarter
- New product launch timeline reviewed

## Action Items
- Schedule follow-up meeting for budget review
- Finalize mobile application development priorities
- Address technical challenges identified

## Participants
- SPEAKER_00: Meeting facilitator
- SPEAKER_01: Team member
- SPEAKER_02: Team member

## Next Steps
Follow-up meeting scheduled for next week to continue discussions."""

    choice.message = message
    response.choices = [choice]
    response.usage = Mock()
    response.usage.prompt_tokens = 850
    response.usage.completion_tokens = 150
    response.usage.total_tokens = 1000
    
    client.chat.completions.create.return_value = response
    
    return client


@pytest.fixture
def mock_openai_client_with_errors():
    """Mock OpenAI client that simulates various error conditions."""
    client = Mock()
    
    def mock_rate_limit_error():
        from openai import RateLimitError
        raise RateLimitError(
            message="Rate limit exceeded",
            response=Mock(status_code=429),
            body={"error": {"code": "rate_limit_exceeded"}}
        )
    
    def mock_auth_error():
        from openai import AuthenticationError
        raise AuthenticationError(
            message="Invalid API key",
            response=Mock(status_code=401),
            body={"error": {"code": "invalid_api_key"}}
        )
    
    def mock_context_length_error():
        from openai import BadRequestError
        raise BadRequestError(
            message="Context length exceeded",
            response=Mock(status_code=400),
            body={"error": {"code": "context_length_exceeded"}}
        )
    
    return {
        'rate_limit': mock_rate_limit_error,
        'auth_error': mock_auth_error,
        'context_length': mock_context_length_error
    }


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client with realistic message responses."""
    client = Mock()
    
    # Mock message response
    response = Mock()
    content_block = Mock()
    content_block.text = """# Meeting Summary

## Executive Summary
This quarterly review meeting covered performance metrics, customer acquisition progress, and strategic planning for the upcoming quarter.

## Key Metrics Discussed
- Customer acquisition: 1,247 new customers (23% increase from Q2)
- Revenue growth: 15% quarter-over-quarter
- Customer satisfaction: Improved significantly

## Main Discussion Points
1. **Performance Review**: Q3 metrics exceeded expectations
2. **Product Strategy**: New product launch timeline discussed
3. **Marketing Results**: Campaign performed better than projected
4. **Technical Challenges**: Several issues identified for resolution

## Action Items & Next Steps
- Budget allocation review for Q4
- Mobile application development prioritization
- Technical challenge resolution planning
- Follow-up meeting scheduled for next week

## Participants & Roles
- **SPEAKER_00**: Meeting facilitator, presented metrics
- **SPEAKER_01**: Asked questions about customer acquisition
- **SPEAKER_02**: Inquired about retention rates

This meeting demonstrated strong team collaboration and data-driven decision making."""

    response.content = [content_block]
    response.usage = Mock()
    response.usage.input_tokens = 920
    response.usage.output_tokens = 180
    
    client.messages.create.return_value = response
    
    return client


@pytest.fixture
def mock_anthropic_client_with_errors():
    """Mock Anthropic client that simulates various error conditions."""
    client = Mock()
    
    def mock_rate_limit_error():
        from anthropic import RateLimitError
        raise RateLimitError(
            message="Rate limit exceeded",
            response=Mock(status_code=429),
            body={"error": {"type": "rate_limit_error"}}
        )
    
    def mock_auth_error():
        from anthropic import AuthenticationError
        raise AuthenticationError(
            message="Invalid API key",
            response=Mock(status_code=401),
            body={"error": {"type": "authentication_error"}}
        )
    
    def mock_overloaded_error():
        from anthropic import OverloadedError
        raise OverloadedError(
            message="Service temporarily overloaded",
            response=Mock(status_code=529),
            body={"error": {"type": "overloaded_error"}}
        )
    
    return {
        'rate_limit': mock_rate_limit_error,
        'auth_error': mock_auth_error,
        'overloaded': mock_overloaded_error
    }


@pytest.fixture
def mock_ffmpeg_operations():
    """Mock FFmpeg operations for audio/video processing."""
    mocks = {}
    
    # Mock probe function
    def mock_probe(input_path: str) -> str:
        return f"""
Input #0, mp3, from '{input_path}':
  Duration: 00:30:00.50, start: 0.000000, bitrate: 128 kb/s
    Stream #0:0: Audio: mp3, 44100 Hz, stereo, fltp, 128 kb/s
"""
    
    # Mock normalize function
    def mock_normalize(input_path: str, output_path: str) -> None:
        # Simulate file creation
        Path(output_path).touch()
    
    # Mock extract audio functions
    def mock_extract_audio_copy(input_path: str, output_path: str, stream_index: int = 0) -> None:
        Path(output_path).touch()
    
    def mock_extract_audio_reencode(input_path: str, output_path: str, codec: str = "aac") -> None:
        Path(output_path).touch()
    
    mocks['probe'] = mock_probe
    mocks['normalize_loudness'] = mock_normalize
    mocks['extract_audio_copy'] = mock_extract_audio_copy
    mocks['extract_audio_reencode'] = mock_extract_audio_reencode
    
    return mocks


@pytest.fixture
def mock_ffprobe_responses():
    """Mock ffprobe responses for different file types."""
    return {
        'valid_audio': {
            "duration": 1800.5,
            "bit_rate": 128000,
            "sample_rate": 44100,
            "channels": 2,
            "codec": "mp3",
            "size": 14000000
        },
        'valid_video': {
            "duration": 1800.5,
            "video_codec": "h264",
            "audio_codec": "aac",
            "audio_bit_rate": 192000,
            "video_bit_rate": 2000000,
            "size": 250000000
        },
        'corrupted_file': {
            "error": "Invalid data found when processing input"
        },
        'no_audio_track': {
            "duration": 300.0,
            "video_codec": "h264",
            "audio_codec": None,
            "error": "No audio stream found"
        }
    }


@pytest.fixture
def mock_progress_callbacks():
    """Mock progress callback functions for testing."""
    def create_progress_tracker():
        tracker = Mock()
        tracker.calls = []
        
        def track_progress(step=None, total=None, step_name=None, status=None, **kwargs):
            tracker.calls.append({
                'step': step,
                'total': total,
                'step_name': step_name,
                'status': status,
                'kwargs': kwargs
            })
        
        tracker.side_effect = track_progress
        return tracker
    
    return {
        'transcription': create_progress_tracker(),
        'summarization': create_progress_tracker(),
        'workflow': create_progress_tracker(),
        'audio_processing': create_progress_tracker()
    }


@pytest.fixture
def mock_file_operations():
    """Mock file system operations."""
    mocks = {}
    
    def mock_copy_file(src: Path, dst: Path):
        dst.touch()
        return dst
    
    def mock_move_file(src: Path, dst: Path):
        dst.touch()
        if src.exists():
            src.unlink()
        return dst
    
    def mock_cleanup_temp_file(temp_file: Path, original_file: Path):
        if temp_file.exists() and temp_file != original_file:
            temp_file.unlink()
    
    mocks['copy_file'] = mock_copy_file
    mocks['move_file'] = mock_move_file
    mocks['cleanup_temp_file'] = mock_cleanup_temp_file
    
    return mocks


@pytest.fixture
def mock_configuration():
    """Mock application configuration for testing."""
    from core.utils.config import Settings
    
    settings = Settings()
    settings.provider = "openai"
    settings.model = "gpt-4o-mini"
    settings.ffmpeg_bin = "ffmpeg"
    settings.ffprobe_bin = "ffprobe"
    settings.max_upload_mb = 25.0
    settings.data_dir = Path("/tmp/summeets_test")
    settings.out_dir = Path("/tmp/summeets_test/output")
    settings.summary_max_tokens = 3000
    settings.summary_chunk_seconds = 1800
    settings.summary_cod_passes = 2
    
    # Mock environment variables
    settings.openai_api_key = "test-openai-key-123"
    settings.anthropic_api_key = "test-anthropic-key-456"
    settings.replicate_api_token = "test-replicate-token-789"
    
    return settings


class MockProgressCallback:
    """Mock progress callback that tracks calls."""
    
    def __init__(self):
        self.calls = []
        self.last_status = None
        self.last_step = None
        self.last_total = None
    
    def __call__(self, step=None, total=None, step_name=None, status=None, **kwargs):
        call_data = {
            'step': step,
            'total': total,
            'step_name': step_name,
            'status': status,
            'timestamp': time.time(),
            'kwargs': kwargs
        }
        self.calls.append(call_data)
        
        self.last_status = status
        self.last_step = step
        self.last_total = total
    
    def get_status_calls(self, status: str) -> List[Dict]:
        """Get all calls with a specific status."""
        return [call for call in self.calls if call['status'] == status]
    
    def get_step_calls(self, step_name: str) -> List[Dict]:
        """Get all calls for a specific step."""
        return [call for call in self.calls if call['step_name'] == step_name]
    
    def was_called_with(self, **kwargs) -> bool:
        """Check if callback was called with specific parameters."""
        for call in self.calls:
            if all(call.get(k) == v for k, v in kwargs.items()):
                return True
        return False


def create_mock_api_responses():
    """Create a comprehensive set of mock API responses."""
    return {
        'replicate': {
            'success': {
                "status": "succeeded",
                "output": {"segments": []},
                "logs": "Processing completed"
            },
            'processing': {
                "status": "processing",
                "logs": "Running transcription..."
            },
            'failed': {
                "status": "failed",
                "error": "Processing failed"
            }
        },
        'openai': {
            'success': {
                "choices": [{"message": {"content": "Summary content"}}],
                "usage": {"total_tokens": 1000}
            },
            'rate_limit': {
                "error": {"code": "rate_limit_exceeded"}
            }
        },
        'anthropic': {
            'success': {
                "content": [{"text": "Summary content"}],
                "usage": {"input_tokens": 500, "output_tokens": 200}
            },
            'overloaded': {
                "error": {"type": "overloaded_error"}
            }
        }
    }