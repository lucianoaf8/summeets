"""Unit tests for audio compression module."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

from src.audio.compression import (
    get_file_size_mb,
    compress_audio_for_upload,
    cleanup_temp_file,
    CompressionError,
    DEFAULT_MAX_MB,
    BITRATE_OPTIONS
)


class TestGetFileSizeMb:
    """Tests for get_file_size_mb function."""

    def test_get_size_in_mb(self, tmp_path):
        """Correctly calculates file size in MB."""
        # Create 1MB test file
        test_file = tmp_path / "test.wav"
        test_file.write_bytes(b"x" * (1024 * 1024))

        size = get_file_size_mb(test_file)
        assert size == pytest.approx(1.0, rel=0.01)

    def test_small_file(self, tmp_path):
        """Handles small files."""
        test_file = tmp_path / "small.wav"
        test_file.write_bytes(b"x" * 1024)  # 1KB

        size = get_file_size_mb(test_file)
        # 1024 bytes = 0.0009765625 MB (binary: 1024/1024/1024)
        assert size == pytest.approx(0.0009765625, rel=0.01)


class TestCompressAudioForUpload:
    """Tests for compress_audio_for_upload function."""

    def test_no_compression_needed(self, tmp_path):
        """Returns original file when under limit."""
        test_file = tmp_path / "small.wav"
        test_file.write_bytes(b"x" * (1024 * 1024))  # 1MB

        result = compress_audio_for_upload(test_file, max_mb=10.0)

        assert result == test_file

    def test_file_not_found(self, tmp_path):
        """Raises error for missing file."""
        missing = tmp_path / "missing.wav"

        with pytest.raises(FileNotFoundError, match="not found"):
            compress_audio_for_upload(missing)

    @patch('src.audio.compression.run_cmd')
    @patch('src.audio.compression.get_file_size_mb')
    def test_successful_compression(self, mock_size, mock_cmd, tmp_path):
        """Compresses file to fit under limit."""
        test_file = tmp_path / "large.wav"
        test_file.write_bytes(b"x" * (30 * 1024 * 1024))  # 30MB

        # First call returns 30MB (original), subsequent calls return compressed sizes
        mock_size.side_effect = [30.0, 10.0]  # Original, then compressed
        mock_cmd.return_value = (0, "", "")

        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = str(tmp_path / "temp.ogg")
            (tmp_path / "temp.ogg").write_bytes(b"compressed")

            result = compress_audio_for_upload(test_file, max_mb=20.0)

            assert result.suffix == ".ogg"

    @patch('src.audio.compression.run_cmd')
    @patch('src.audio.compression.get_file_size_mb')
    def test_compression_failure(self, mock_size, mock_cmd, tmp_path):
        """Raises error when compression fails."""
        test_file = tmp_path / "large.wav"
        test_file.write_bytes(b"x" * (30 * 1024 * 1024))

        mock_size.return_value = 30.0  # Always too large
        mock_cmd.return_value = (1, "", "FFmpeg error")

        with pytest.raises(CompressionError):
            compress_audio_for_upload(test_file, max_mb=10.0)

    @patch('src.audio.compression.run_cmd')
    @patch('src.audio.compression.get_file_size_mb')
    def test_cannot_compress_enough(self, mock_size, mock_cmd, tmp_path):
        """Raises error when file can't be compressed enough."""
        test_file = tmp_path / "huge.wav"
        test_file.write_bytes(b"x" * 100)

        # Original size 100MB, compressed always 50MB (still too large for 10MB limit)
        mock_size.side_effect = [100.0] + [50.0] * len(BITRATE_OPTIONS)
        mock_cmd.return_value = (0, "", "")

        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = str(tmp_path / "temp.ogg")
            (tmp_path / "temp.ogg").write_bytes(b"x")

            with pytest.raises(CompressionError, match="Could not compress"):
                compress_audio_for_upload(test_file, max_mb=10.0)


class TestCleanupTempFile:
    """Tests for cleanup_temp_file function."""

    def test_cleans_up_temp_file(self, tmp_path):
        """Removes temporary file."""
        temp_file = tmp_path / "temp.ogg"
        original = tmp_path / "original.wav"
        temp_file.write_bytes(b"temp")
        original.write_bytes(b"original")

        cleanup_temp_file(temp_file, original)

        assert not temp_file.exists()
        assert original.exists()

    def test_preserves_original(self, tmp_path):
        """Does not delete original file."""
        original = tmp_path / "original.wav"
        original.write_bytes(b"content")

        cleanup_temp_file(original, original)

        assert original.exists()

    def test_handles_missing_file(self, tmp_path):
        """Handles already-deleted file gracefully."""
        temp_file = tmp_path / "missing.ogg"
        original = tmp_path / "original.wav"
        original.write_bytes(b"content")

        # Should not raise
        cleanup_temp_file(temp_file, original)


class TestConstants:
    """Tests for module constants."""

    def test_default_max_mb(self):
        """Default limit is reasonable."""
        assert DEFAULT_MAX_MB == 24.0

    def test_bitrate_options_descending(self):
        """Bitrate options in descending order."""
        for i in range(len(BITRATE_OPTIONS) - 1):
            assert BITRATE_OPTIONS[i] > BITRATE_OPTIONS[i + 1]

    def test_bitrate_options_reasonable(self):
        """Bitrate options are reasonable values."""
        assert all(8 <= b <= 320 for b in BITRATE_OPTIONS)
