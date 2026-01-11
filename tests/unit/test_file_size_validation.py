"""Unit tests for file size validation."""
import pytest
from pathlib import Path
import tempfile
import os

from src.utils.validation import (
    validate_file_size,
    validate_workflow_input_with_size,
    MAX_FILE_SIZE_MB
)
from src.utils.exceptions import ValidationError


class TestValidateFileSize:
    """Tests for file size validation."""

    def test_small_file_passes(self, tmp_path):
        """Test small file passes validation."""
        test_file = tmp_path / "small.txt"
        test_file.write_text("Hello, World!")

        result = validate_file_size(test_file, max_size_mb=1.0)
        assert result == test_file

    def test_large_file_fails(self, tmp_path):
        """Test file exceeding limit fails validation."""
        test_file = tmp_path / "large.bin"
        # Create a file larger than the limit
        with open(test_file, 'wb') as f:
            f.write(b'0' * (2 * 1024 * 1024))  # 2MB

        with pytest.raises(ValidationError) as exc_info:
            validate_file_size(test_file, max_size_mb=1.0)

        assert "exceeds maximum size" in str(exc_info.value)

    def test_file_at_limit_passes(self, tmp_path):
        """Test file exactly at limit passes."""
        test_file = tmp_path / "exact.bin"
        # Create a file of exactly 1MB
        with open(test_file, 'wb') as f:
            f.write(b'0' * (1 * 1024 * 1024))

        result = validate_file_size(test_file, max_size_mb=1.0)
        assert result == test_file

    def test_nonexistent_file_raises(self, tmp_path):
        """Test nonexistent file raises FileNotFoundError."""
        fake_file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            validate_file_size(fake_file)

    def test_directory_raises_validation_error(self, tmp_path):
        """Test directory raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_file_size(tmp_path)

        assert "not a file" in str(exc_info.value)

    def test_string_path_works(self, tmp_path):
        """Test string path is accepted."""
        test_file = tmp_path / "string_test.txt"
        test_file.write_text("Test content")

        result = validate_file_size(str(test_file), max_size_mb=1.0)
        assert result == test_file

    def test_default_limit_is_500mb(self):
        """Test default limit is 500MB."""
        assert MAX_FILE_SIZE_MB == 500

    def test_file_type_context_in_error(self, tmp_path):
        """Test file type is included in error message."""
        test_file = tmp_path / "video.mp4"
        with open(test_file, 'wb') as f:
            f.write(b'0' * (2 * 1024 * 1024))  # 2MB

        with pytest.raises(ValidationError) as exc_info:
            validate_file_size(test_file, max_size_mb=1.0, file_type="video")

        assert "video" in str(exc_info.value)


class TestValidateWorkflowInputWithSize:
    """Tests for workflow input validation with size check."""

    def test_small_audio_file_passes(self, tmp_path):
        """Test small audio file passes all validation."""
        test_file = tmp_path / "audio.m4a"
        test_file.write_bytes(b'fake audio content')

        path, file_type = validate_workflow_input_with_size(test_file, max_size_mb=1.0)

        assert path == test_file
        assert file_type == "audio"

    def test_large_video_file_fails(self, tmp_path):
        """Test large video file fails size validation."""
        test_file = tmp_path / "video.mp4"
        with open(test_file, 'wb') as f:
            f.write(b'0' * (2 * 1024 * 1024))  # 2MB

        with pytest.raises(ValidationError) as exc_info:
            validate_workflow_input_with_size(test_file, max_size_mb=1.0)

        assert "exceeds maximum size" in str(exc_info.value)

    def test_transcript_not_size_checked(self, tmp_path):
        """Test transcript files work (would be checked in workflow validator)."""
        test_file = tmp_path / "transcript.json"
        test_file.write_text('{"segments": []}')

        path, file_type = validate_workflow_input_with_size(test_file)

        assert path == test_file
        assert file_type == "transcript"
