"""Unit tests for startup validation module."""
import pytest
from unittest.mock import patch, MagicMock

from src.utils.startup import (
    validate_openai_api_key,
    validate_anthropic_api_key,
    validate_replicate_api_token,
    validate_ffmpeg_availability,
    validate_disk_space,
    validate_startup,
    check_startup_requirements,
    ValidationLevel,
    ValidationResult,
    StartupValidationResult
)
from src.utils.exceptions import ConfigurationError


class TestValidateOpenAIApiKey:
    """Tests for OpenAI API key validation."""

    def test_valid_key(self):
        """Test valid OpenAI API key."""
        result = validate_openai_api_key("sk-1234567890abcdefghijklmnopqrstuvwxyz")
        assert result.passed is True

    def test_valid_project_key(self):
        """Test valid OpenAI project API key."""
        result = validate_openai_api_key("sk-proj-1234567890abcdefghijklmnopqrstuvwxyz")
        assert result.passed is True

    def test_none_key(self):
        """Test None API key returns warning."""
        result = validate_openai_api_key(None)
        assert result.passed is False
        assert result.level == ValidationLevel.WARN

    def test_empty_key(self):
        """Test empty API key returns warning."""
        result = validate_openai_api_key("")
        assert result.passed is False
        assert result.level == ValidationLevel.WARN

    def test_invalid_prefix(self):
        """Test API key with wrong prefix fails."""
        result = validate_openai_api_key("invalid-1234567890abcdefghijklmnopqrstuvwxyz")
        assert result.passed is False
        assert result.level == ValidationLevel.ERROR

    def test_too_short(self):
        """Test API key that's too short fails."""
        result = validate_openai_api_key("sk-short")
        assert result.passed is False
        assert result.level == ValidationLevel.ERROR


class TestValidateAnthropicApiKey:
    """Tests for Anthropic API key validation."""

    def test_valid_key(self):
        """Test valid Anthropic API key."""
        result = validate_anthropic_api_key("sk-ant-1234567890abcdefghijklmnopqrstuvwxyz")
        assert result.passed is True

    def test_none_key(self):
        """Test None API key returns warning."""
        result = validate_anthropic_api_key(None)
        assert result.passed is False
        assert result.level == ValidationLevel.WARN

    def test_invalid_prefix(self):
        """Test API key with wrong prefix fails."""
        result = validate_anthropic_api_key("sk-1234567890abcdefghijklmnopqrstuvwxyz")
        assert result.passed is False
        assert result.level == ValidationLevel.ERROR


class TestValidateReplicateApiToken:
    """Tests for Replicate API token validation."""

    def test_valid_token(self):
        """Test valid Replicate API token."""
        result = validate_replicate_api_token("r8_1234567890abcdefghijklmnopqrstuvwxyz")
        assert result.passed is True

    def test_none_token(self):
        """Test None token returns warning."""
        result = validate_replicate_api_token(None)
        assert result.passed is False
        assert result.level == ValidationLevel.WARN

    def test_invalid_prefix(self):
        """Test token with wrong prefix fails."""
        result = validate_replicate_api_token("invalid_1234567890abcdefghijklmnopqrstuvwxyz")
        assert result.passed is False
        assert result.level == ValidationLevel.ERROR


class TestValidateFFmpegAvailability:
    """Tests for FFmpeg availability check."""

    @patch('shutil.which')
    def test_ffmpeg_available(self, mock_which):
        """Test when FFmpeg is available."""
        mock_which.side_effect = lambda x: f"/usr/bin/{x}" if x in ['ffmpeg', 'ffprobe'] else None
        result = validate_ffmpeg_availability()
        assert result.passed is True

    @patch('shutil.which')
    def test_ffmpeg_not_found(self, mock_which):
        """Test when FFmpeg is not available."""
        mock_which.return_value = None
        result = validate_ffmpeg_availability()
        assert result.passed is False
        assert result.level == ValidationLevel.WARN


class TestValidateDiskSpace:
    """Tests for disk space validation."""

    def test_sufficient_space(self):
        """Test when sufficient disk space is available."""
        result = validate_disk_space(min_gb=0.001)  # 1MB should always pass
        assert result.passed is True

    def test_insufficient_space(self):
        """Test when disk space is below minimum."""
        result = validate_disk_space(min_gb=999999)  # Impossibly high
        assert result.passed is False
        assert result.level == ValidationLevel.WARN


class TestStartupValidationResult:
    """Tests for StartupValidationResult aggregation."""

    def test_empty_result_passes(self):
        """Test empty result passes by default."""
        result = StartupValidationResult(passed=True)
        assert result.passed is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_add_error_fails_result(self):
        """Test adding error fails the overall result."""
        result = StartupValidationResult(passed=True)
        result.add_result(ValidationResult(
            passed=False,
            message="Test error",
            level=ValidationLevel.ERROR
        ))
        assert result.passed is False
        assert len(result.errors) == 1

    def test_add_warning_keeps_passing(self):
        """Test adding warning doesn't fail the result."""
        result = StartupValidationResult(passed=True)
        result.add_result(ValidationResult(
            passed=False,
            message="Test warning",
            level=ValidationLevel.WARN
        ))
        assert result.passed is True
        assert len(result.warnings) == 1


class TestCheckStartupRequirements:
    """Tests for check_startup_requirements function."""

    @patch('src.utils.startup.SETTINGS')
    def test_raises_on_missing_transcription_key(self, mock_settings):
        """Test raises ConfigurationError when transcription key is missing."""
        mock_settings.replicate_api_token = None
        mock_settings.openai_api_key = "sk-valid1234567890abcdefghij"
        mock_settings.anthropic_api_key = None
        mock_settings.ffmpeg_bin = "ffmpeg"
        mock_settings.ffprobe_bin = "ffprobe"
        mock_settings.data_dir = MagicMock()
        mock_settings.data_dir.exists.return_value = False

        with pytest.raises(ConfigurationError):
            check_startup_requirements(require_transcription=True)

    @patch('src.utils.startup.SETTINGS')
    def test_raises_on_missing_summarization_key(self, mock_settings):
        """Test raises ConfigurationError when summarization key is missing."""
        mock_settings.replicate_api_token = "r8_valid1234567890abcdefghij"
        mock_settings.openai_api_key = None
        mock_settings.anthropic_api_key = None
        mock_settings.ffmpeg_bin = "ffmpeg"
        mock_settings.ffprobe_bin = "ffprobe"
        mock_settings.data_dir = MagicMock()
        mock_settings.data_dir.exists.return_value = False

        with pytest.raises(ConfigurationError):
            check_startup_requirements(require_summarization=True, provider="openai")
