"""
Unit tests for input validation module.
Tests comprehensive input sanitization and validation.
"""
import pytest
import os
from pathlib import Path
from unittest.mock import patch

from core.validation import (
    sanitize_path_input,
    validate_audio_path,
    validate_output_directory,
    validate_filename,
    validate_provider_name,
    validate_positive_number,
    validate_integer_range,
    ValidationError
)


class TestSanitizePathInput:
    """Tests for sanitize_path_input function."""
    
    def test_clean_path(self):
        """Test with clean, valid path."""
        result = sanitize_path_input("/home/user/audio.mp3")
        assert result == "/home/user/audio.mp3"
    
    def test_quoted_path(self):
        """Test with quoted path input."""
        result = sanitize_path_input('"/home/user/audio file.mp3"')
        assert result == "/home/user/audio file.mp3"
    
    def test_whitespace_cleanup(self):
        """Test cleanup of surrounding whitespace."""
        result = sanitize_path_input("  /home/user/audio.mp3  ")
        assert result == "/home/user/audio.mp3"
    
    def test_empty_path(self):
        """Test with empty path."""
        with pytest.raises(ValidationError, match="Path cannot be empty"):
            sanitize_path_input("")
    
    def test_whitespace_only_path(self):
        """Test with whitespace-only path."""
        with pytest.raises(ValidationError, match="Path cannot be empty"):
            sanitize_path_input("   ")
    
    def test_directory_traversal(self):
        """Test detection of directory traversal attempts."""
        with pytest.raises(ValidationError, match="invalid characters"):
            sanitize_path_input("../../../etc/passwd")
    
    def test_invalid_characters(self):
        """Test detection of invalid filename characters."""
        invalid_chars = ['<', '>', '"', '|', '*', '?']
        for char in invalid_chars:
            with pytest.raises(ValidationError, match="invalid characters"):
                sanitize_path_input(f"/home/user/file{char}.mp3")
    
    def test_windows_reserved_names(self):
        """Test detection of Windows reserved names."""
        reserved = ["con", "prn", "aux", "nul", "com1", "lpt1"]
        for name in reserved:
            with pytest.raises(ValidationError, match="invalid characters"):
                sanitize_path_input(f"/home/user/{name}")
    
    def test_path_too_long(self):
        """Test path length validation."""
        long_path = "a" * 300
        with pytest.raises(ValidationError, match="Path too long"):
            sanitize_path_input(long_path)


class TestValidateAudioPath:
    """Tests for validate_audio_path function."""
    
    def test_valid_audio_file(self, tmp_path):
        """Test with valid audio file."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        
        result = validate_audio_path(audio_file)
        assert result == audio_file.resolve()
    
    def test_valid_audio_directory(self, tmp_path):
        """Test with directory containing audio files."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        
        result = validate_audio_path(tmp_path)
        assert result == tmp_path.resolve()
    
    def test_string_path_input(self, tmp_path):
        """Test with string path input."""
        audio_file = tmp_path / "test.wav"
        audio_file.touch()
        
        result = validate_audio_path(str(audio_file))
        assert result == audio_file.resolve()
    
    def test_nonexistent_path(self):
        """Test with nonexistent path."""
        with pytest.raises(FileNotFoundError):
            validate_audio_path("/nonexistent/path")
    
    def test_unsupported_file_format(self, tmp_path):
        """Test with unsupported file format."""
        text_file = tmp_path / "test.txt"
        text_file.touch()
        
        with pytest.raises(ValidationError, match="Unsupported audio format"):
            validate_audio_path(text_file)
    
    def test_unreadable_file(self, tmp_path):
        """Test with unreadable file."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        
        with patch('os.access', return_value=False):
            with pytest.raises(ValidationError, match="not readable"):
                validate_audio_path(audio_file)
    
    def test_directory_with_no_audio(self, tmp_path):
        """Test with directory containing no audio files."""
        text_file = tmp_path / "readme.txt"
        text_file.touch()
        
        with pytest.raises(ValidationError, match="No supported audio files found"):
            validate_audio_path(tmp_path)
    
    def test_unreadable_directory(self, tmp_path):
        """Test with unreadable directory."""
        with patch('os.access', return_value=False):
            with pytest.raises(ValidationError, match="not readable"):
                validate_audio_path(tmp_path)


class TestValidateOutputDirectory:
    """Tests for validate_output_directory function."""
    
    def test_existing_writable_directory(self, tmp_path):
        """Test with existing writable directory."""
        result = validate_output_directory(tmp_path)
        assert result == tmp_path.resolve()
    
    def test_create_new_directory(self, tmp_path):
        """Test creation of new directory."""
        new_dir = tmp_path / "output"
        
        result = validate_output_directory(new_dir)
        assert result == new_dir.resolve()
        assert new_dir.exists()
    
    def test_string_path_input(self, tmp_path):
        """Test with string path input."""
        result = validate_output_directory(str(tmp_path))
        assert result == tmp_path.resolve()
    
    def test_parent_not_writable(self, tmp_path):
        """Test with non-writable parent directory."""
        new_dir = tmp_path / "output"
        
        with patch('os.access') as mock_access:
            def access_side_effect(path, mode):
                if mode == os.W_OK and str(path) == str(tmp_path):
                    return False
                return True
            mock_access.side_effect = access_side_effect
            
            with pytest.raises(ValidationError, match="not writable"):
                validate_output_directory(new_dir)
    
    def test_existing_file_not_directory(self, tmp_path):
        """Test with existing file that's not a directory."""
        existing_file = tmp_path / "output.txt"
        existing_file.touch()
        
        with pytest.raises(ValidationError, match="not a directory"):
            validate_output_directory(existing_file)


class TestValidateFilename:
    """Tests for validate_filename function."""
    
    def test_clean_filename(self):
        """Test with clean filename."""
        result = validate_filename("audio_transcript.json")
        assert result == "audio_transcript.json"
    
    def test_invalid_characters_replacement(self):
        """Test replacement of invalid characters."""
        result = validate_filename("audio<file>.json")
        assert result == "audio_file_.json"
    
    def test_windows_reserved_name(self):
        """Test handling of Windows reserved names."""
        result = validate_filename("con.txt")
        assert result == "_con.txt"
    
    def test_empty_filename(self):
        """Test with empty filename."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_filename("")
    
    def test_filename_too_long(self):
        """Test with filename that's too long."""
        long_name = "a" * 300 + ".txt"
        with pytest.raises(ValidationError, match="too long"):
            validate_filename(long_name)
    
    def test_dots_and_spaces_trimming(self):
        """Test trimming of leading/trailing dots and spaces."""
        result = validate_filename("  .filename.txt.  ")
        assert result == "filename.txt"
    
    def test_all_invalid_characters(self):
        """Test filename becomes empty after sanitization."""
        with pytest.raises(ValidationError, match="becomes empty"):
            validate_filename("<<<>>>")


class TestValidateProviderName:
    """Tests for validate_provider_name function."""
    
    def test_valid_provider_names(self):
        """Test with valid provider names."""
        valid_names = ["openai", "anthropic", "replicate", "custom_provider"]
        for name in valid_names:
            result = validate_provider_name(name)
            assert result == name.lower()
    
    def test_case_normalization(self):
        """Test case normalization."""
        result = validate_provider_name("OpenAI")
        assert result == "openai"
    
    def test_empty_provider_name(self):
        """Test with empty provider name."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_provider_name("")
    
    def test_invalid_characters(self):
        """Test with invalid characters in provider name."""
        with pytest.raises(ValidationError, match="letters, numbers, and underscores"):
            validate_provider_name("open-ai")
    
    def test_unknown_provider_warning(self, caplog):
        """Test warning for unknown provider."""
        result = validate_provider_name("unknown_provider")
        assert result == "unknown_provider"
        assert "Unknown provider" in caplog.text


class TestValidatePositiveNumber:
    """Tests for validate_positive_number function."""
    
    def test_valid_positive_numbers(self):
        """Test with valid positive numbers."""
        assert validate_positive_number(5) == 5.0
        assert validate_positive_number(3.14) == 3.14
        assert validate_positive_number("2.5") == 2.5
    
    def test_zero_and_negative_numbers(self):
        """Test with zero and negative numbers."""
        with pytest.raises(ValidationError, match="must be positive"):
            validate_positive_number(0)
        
        with pytest.raises(ValidationError, match="must be positive"):
            validate_positive_number(-1)
    
    def test_invalid_string(self):
        """Test with invalid string input."""
        with pytest.raises(ValidationError, match="must be a valid number"):
            validate_positive_number("not_a_number")
    
    def test_custom_name_in_error(self):
        """Test custom parameter name in error messages."""
        with pytest.raises(ValidationError, match="duration must be positive"):
            validate_positive_number(-1, "duration")


class TestValidateIntegerRange:
    """Tests for validate_integer_range function."""
    
    def test_valid_integers_in_range(self):
        """Test with valid integers in range."""
        assert validate_integer_range(5, 1, 10) == 5
        assert validate_integer_range("7", 1, 10) == 7
    
    def test_boundary_values(self):
        """Test boundary values."""
        assert validate_integer_range(1, 1, 10) == 1
        assert validate_integer_range(10, 1, 10) == 10
    
    def test_out_of_range_values(self):
        """Test values outside the range."""
        with pytest.raises(ValidationError, match="must be between 1 and 10"):
            validate_integer_range(0, 1, 10)
        
        with pytest.raises(ValidationError, match="must be between 1 and 10"):
            validate_integer_range(11, 1, 10)
    
    def test_invalid_string(self):
        """Test with invalid string input."""
        with pytest.raises(ValidationError, match="must be a valid integer"):
            validate_integer_range("not_an_int", 1, 10)
    
    def test_float_input(self):
        """Test with float input."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_integer_range(5.5, 1, 10)


if __name__ == "__main__":
    pytest.main([__file__])