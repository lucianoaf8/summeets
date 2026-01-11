"""
Unit tests for fsio module.
Tests DataManager and file system I/O operations.
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime


class TestSafeFilename:
    """Test safe_filename function."""

    def test_safe_filename_removes_special_chars(self):
        """Test removal of problematic characters."""
        from src.utils.fsio import safe_filename

        result = safe_filename('file<>:"/\\|?*name')
        assert '<' not in result
        assert '>' not in result
        assert ':' not in result
        assert '"' not in result
        assert '/' not in result
        assert '\\' not in result
        assert '|' not in result
        assert '?' not in result
        assert '*' not in result

    def test_safe_filename_strips_whitespace(self):
        """Test stripping of whitespace and dots."""
        from src.utils.fsio import safe_filename

        result = safe_filename("  filename.  ")
        assert not result.startswith(' ')
        assert not result.endswith(' ')
        assert not result.endswith('.')

    def test_safe_filename_truncates_long_names(self):
        """Test truncation of long filenames."""
        from src.utils.fsio import safe_filename

        long_name = "a" * 300
        result = safe_filename(long_name)
        assert len(result) <= 200

    def test_safe_filename_empty_returns_unnamed(self):
        """Test empty filename returns 'unnamed'."""
        from src.utils.fsio import safe_filename

        result = safe_filename("")
        assert result == "unnamed"

    def test_safe_filename_only_special_chars(self):
        """Test filename with only special chars converts to underscores."""
        from src.utils.fsio import safe_filename

        # Special chars are replaced with underscores, resulting in underscores
        result = safe_filename(":::???")
        # The function replaces special chars with _, so ":::???" becomes "______"
        assert result == "______"

    def test_safe_filename_custom_max_length(self):
        """Test custom max length."""
        from src.utils.fsio import safe_filename

        long_name = "a" * 100
        result = safe_filename(long_name, max_length=50)
        assert len(result) <= 50


class TestEnsureDirectory:
    """Test ensure_directory function."""

    def test_ensure_directory_creates_new(self, tmp_path):
        """Test creating a new directory."""
        from src.utils.fsio import ensure_directory

        new_dir = tmp_path / "new_folder"
        result = ensure_directory(new_dir)

        assert result == new_dir
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_directory_existing(self, tmp_path):
        """Test with existing directory."""
        from src.utils.fsio import ensure_directory

        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        result = ensure_directory(existing_dir)
        assert result == existing_dir

    def test_ensure_directory_nested(self, tmp_path):
        """Test creating nested directories."""
        from src.utils.fsio import ensure_directory

        nested_dir = tmp_path / "a" / "b" / "c"
        result = ensure_directory(nested_dir)

        assert result == nested_dir
        assert nested_dir.exists()


class TestGetFileSizeMB:
    """Test get_file_size_mb function."""

    def test_get_file_size_mb_small(self, tmp_path):
        """Test file size in MB for small file."""
        from src.utils.fsio import get_file_size_mb

        test_file = tmp_path / "small.txt"
        test_file.write_bytes(b"x" * 1024)  # 1KB

        size = get_file_size_mb(test_file)
        assert size == pytest.approx(0.000976562, rel=1e-5)

    def test_get_file_size_mb_megabyte(self, tmp_path):
        """Test file size for 1MB file."""
        from src.utils.fsio import get_file_size_mb

        test_file = tmp_path / "megabyte.bin"
        test_file.write_bytes(b"x" * (1024 * 1024))  # 1MB

        size = get_file_size_mb(test_file)
        assert size == pytest.approx(1.0, rel=1e-3)


class TestFormatDuration:
    """Test format_duration function."""

    def test_format_duration_seconds(self):
        """Test formatting short durations in seconds."""
        from src.utils.fsio import format_duration

        assert format_duration(30.5) == "30.5s"
        assert format_duration(0.5) == "0.5s"
        assert format_duration(59.9) == "59.9s"

    def test_format_duration_minutes(self):
        """Test formatting durations in minutes."""
        from src.utils.fsio import format_duration

        assert format_duration(60) == "1m 0s"
        assert format_duration(90) == "1m 30s"
        assert format_duration(3599) == "59m 59s"

    def test_format_duration_hours(self):
        """Test formatting durations in hours."""
        from src.utils.fsio import format_duration

        assert format_duration(3600) == "1h 0m"
        assert format_duration(7200) == "2h 0m"
        assert format_duration(5400) == "1h 30m"


class TestDataManager:
    """Test DataManager class."""

    def test_init_creates_directories(self, tmp_path):
        """Test DataManager creates required directories."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)

        assert dm.video_dir.exists()
        assert dm.audio_dir.exists()
        assert dm.transcript_dir.exists()
        assert dm.temp_dir.exists()
        assert dm.jobs_dir.exists()

    def test_get_video_path(self, tmp_path):
        """Test getting video file path."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)
        path = dm.get_video_path("video.mp4")

        assert path == dm.video_dir / "video.mp4"

    def test_get_audio_path(self, tmp_path):
        """Test getting audio file path with subfolders."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)
        path = dm.get_audio_path("meeting", "m4a")

        assert path.name == "meeting.m4a"
        assert "meeting" in str(path.parent)

    def test_get_transcript_path(self, tmp_path):
        """Test getting transcript file path with subfolders."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)
        path = dm.get_transcript_path("meeting", "json")

        assert path.name == "meeting.json"
        assert "meeting" in str(path.parent)

    def test_create_temp_file(self, tmp_path):
        """Test creating temporary file."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)
        temp_path = dm.create_temp_file(suffix=".txt", prefix="test_")

        assert temp_path.exists()
        assert temp_path.suffix == ".txt"
        assert temp_path.name.startswith("test_")
        assert dm.temp_dir in temp_path.parents or temp_path.parent == dm.temp_dir

    def test_atomic_write_string(self, tmp_path):
        """Test atomic write with string content."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)
        output_file = tmp_path / "test_output.txt"

        dm.atomic_write(output_file, "test content")

        assert output_file.exists()
        assert output_file.read_text() == "test content"

    def test_atomic_write_dict(self, tmp_path):
        """Test atomic write with dictionary content."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)
        output_file = tmp_path / "test_output.json"
        test_data = {"key": "value", "number": 42}

        dm.atomic_write(output_file, test_data)

        assert output_file.exists()
        loaded = json.loads(output_file.read_text())
        assert loaded == test_data

    def test_atomic_write_list(self, tmp_path):
        """Test atomic write with list content."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)
        output_file = tmp_path / "test_output.json"
        test_data = [1, 2, 3, "four"]

        dm.atomic_write(output_file, test_data)

        assert output_file.exists()
        loaded = json.loads(output_file.read_text())
        assert loaded == test_data

    def test_atomic_write_creates_parent_dirs(self, tmp_path):
        """Test atomic write creates parent directories."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)
        output_file = tmp_path / "subdir" / "nested" / "file.txt"

        dm.atomic_write(output_file, "content")

        assert output_file.exists()

    def test_load_job_state_nonexistent(self, tmp_path):
        """Test loading nonexistent job state."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)
        result = dm.load_job_state(uuid4())

        assert result is None

    def test_load_job_state_invalid_json(self, tmp_path):
        """Test loading job with invalid JSON."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)
        job_id = uuid4()
        job_file = dm.jobs_dir / f"{job_id}.json"
        job_file.write_text("invalid json content")

        result = dm.load_job_state(job_id)
        assert result is None

    def test_cleanup_temp_files_old(self, tmp_path):
        """Test cleanup of old temporary files."""
        from src.utils.fsio import DataManager
        import time

        dm = DataManager(tmp_path)

        # Create old temp file
        old_file = dm.temp_dir / "old_temp.txt"
        old_file.write_text("old")

        # Modify its mtime to be very old (simulate old file)
        import os
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        os.utime(old_file, (old_time, old_time))

        dm.cleanup_temp_files(max_age_hours=24)

        assert not old_file.exists()

    def test_cleanup_temp_files_recent(self, tmp_path):
        """Test that recent temp files are not cleaned."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)

        # Create recent temp file
        recent_file = dm.temp_dir / "recent_temp.txt"
        recent_file.write_text("recent")

        dm.cleanup_temp_files(max_age_hours=24)

        assert recent_file.exists()

    def test_organize_input_file(self, tmp_path):
        """Test organizing input file."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)

        # Create source file
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_file = source_dir / "input.mp4"
        source_file.write_bytes(b"video content")

        organized = dm.organize_input_file(source_file)

        assert organized.exists()
        assert dm.input_dir in organized.parents

    def test_organize_input_file_nonexistent(self, tmp_path):
        """Test organizing nonexistent file raises error."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)
        nonexistent = tmp_path / "nonexistent.mp4"

        with pytest.raises(FileNotFoundError):
            dm.organize_input_file(nonexistent)

    def test_create_job_output_dir(self, tmp_path):
        """Test creating job output directory."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)
        job_id = uuid4()

        output_dir = dm.create_job_output_dir(job_id, "transcription")

        assert output_dir.exists()
        assert "transcription" in str(output_dir)

    def test_create_file_processing_dirs(self, tmp_path):
        """Test creating processing directories."""
        from src.utils.fsio import DataManager

        dm = DataManager(tmp_path)
        dirs = dm.create_file_processing_dirs("my_meeting")

        assert "audio" in dirs
        assert "transcript" in dirs
        assert dirs["audio"].exists()
        assert dirs["transcript"].exists()


class TestGetDataManager:
    """Test get_data_manager function."""

    def test_get_data_manager_singleton(self, tmp_path):
        """Test get_data_manager returns same instance."""
        from src.utils import fsio

        # Reset global state
        fsio._data_manager = None

        dm1 = fsio.get_data_manager(tmp_path)
        dm2 = fsio.get_data_manager()

        assert dm1 is dm2


class TestCreateOutputFilename:
    """Test create_output_filename function."""

    def test_create_output_filename_with_timestamp(self):
        """Test creating output filename with timestamp."""
        from src.utils.fsio import create_output_filename
        from src.models import FileType

        result = create_output_filename("meeting", "transcription", FileType.JSON)

        assert "meeting" in result
        assert "transcription" in result
        assert result.endswith(".json")
        # Contains timestamp pattern
        assert "_20" in result  # Year prefix

    def test_create_output_filename_without_timestamp(self):
        """Test creating output filename without timestamp."""
        from src.utils.fsio import create_output_filename
        from src.models import FileType

        # FileType enum uses MD, not MARKDOWN
        result = create_output_filename("meeting", "summary", FileType.MD, timestamp=False)

        assert result == "meeting_summary.md"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
