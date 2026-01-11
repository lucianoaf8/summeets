"""
Unit tests for file I/O utilities.
Tests JSON, text, and line-based file operations with error handling.
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from src.utils.file_io import (
    read_json_file, write_json_file, read_text_file, write_text_file,
    read_lines_file, write_lines_file, ensure_directory, safe_remove_file,
    copy_file, move_file, get_file_size, list_files_with_extension,
    create_timestamped_directory, backup_file
)
from src.utils.exceptions import SummeetsError


class TestJSONOperations:
    """Test JSON file operations."""
    
    def test_read_json_file_success(self, tmp_path):
        """Test successful JSON file reading."""
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        json_file = tmp_path / "test.json"
        
        with open(json_file, 'w') as f:
            json.dump(test_data, f)
        
        result = read_json_file(json_file)
        assert result == test_data
    
    def test_read_json_file_nonexistent(self, tmp_path):
        """Test reading nonexistent JSON file."""
        json_file = tmp_path / "nonexistent.json"
        
        with pytest.raises(SummeetsError, match="File not found during JSON file read"):
            read_json_file(json_file)
    
    def test_read_json_file_invalid_json(self, tmp_path):
        """Test reading invalid JSON file."""
        json_file = tmp_path / "invalid.json"
        
        with open(json_file, 'w') as f:
            f.write("invalid json content")
        
        with pytest.raises(SummeetsError):
            read_json_file(json_file)
    
    def test_write_json_file_success(self, tmp_path):
        """Test successful JSON file writing."""
        test_data = {"key": "value", "number": 42}
        json_file = tmp_path / "output.json"
        
        write_json_file(json_file, test_data)
        
        assert json_file.exists()
        with open(json_file, 'r') as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data
    
    def test_write_json_file_create_directory(self, tmp_path):
        """Test JSON file writing with directory creation."""
        test_data = {"key": "value"}
        json_file = tmp_path / "subdir" / "output.json"
        
        write_json_file(json_file, test_data)
        
        assert json_file.exists()
        assert json_file.parent.is_dir()
    
    def test_write_json_file_custom_indent(self, tmp_path):
        """Test JSON file writing with custom indentation."""
        test_data = {"key": "value"}
        json_file = tmp_path / "output.json"
        
        write_json_file(json_file, test_data, indent=4)
        
        with open(json_file, 'r') as f:
            content = f.read()
        assert "    " in content  # 4-space indentation
    
    def test_json_file_string_path(self, tmp_path):
        """Test JSON operations with string paths."""
        test_data = {"key": "value"}
        json_file = str(tmp_path / "test.json")
        
        write_json_file(json_file, test_data)
        result = read_json_file(json_file)
        
        assert result == test_data


class TestTextOperations:
    """Test text file operations."""
    
    def test_read_text_file_success(self, tmp_path):
        """Test successful text file reading."""
        test_content = "Hello, World!\nThis is a test."
        text_file = tmp_path / "test.txt"
        
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        result = read_text_file(text_file)
        assert result == test_content
    
    def test_read_text_file_custom_encoding(self, tmp_path):
        """Test text file reading with custom encoding."""
        test_content = "Hello, World!"
        text_file = tmp_path / "test.txt"
        
        with open(text_file, 'w', encoding='latin-1') as f:
            f.write(test_content)
        
        result = read_text_file(text_file, encoding='latin-1')
        assert result == test_content
    
    def test_read_text_file_nonexistent(self, tmp_path):
        """Test reading nonexistent text file."""
        text_file = tmp_path / "nonexistent.txt"
        
        with pytest.raises(SummeetsError, match="File not found during text file read"):
            read_text_file(text_file)
    
    def test_write_text_file_success(self, tmp_path):
        """Test successful text file writing."""
        test_content = "Hello, World!\nThis is a test."
        text_file = tmp_path / "output.txt"
        
        write_text_file(text_file, test_content)
        
        assert text_file.exists()
        with open(text_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == test_content
    
    def test_write_text_file_append(self, tmp_path):
        """Test text file writing in append mode."""
        text_file = tmp_path / "output.txt"
        
        write_text_file(text_file, "First line\n")
        write_text_file(text_file, "Second line\n", append=True)
        
        with open(text_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "First line\nSecond line\n"
    
    def test_write_text_file_custom_encoding(self, tmp_path):
        """Test text file writing with custom encoding."""
        test_content = "Hello, World!"
        text_file = tmp_path / "output.txt"
        
        write_text_file(text_file, test_content, encoding='latin-1')
        
        with open(text_file, 'r', encoding='latin-1') as f:
            content = f.read()
        assert content == test_content


class TestLineOperations:
    """Test line-based file operations."""
    
    def test_read_lines_file_success(self, tmp_path):
        """Test successful lines file reading."""
        test_lines = ["Line 1", "Line 2", "Line 3"]
        text_file = tmp_path / "test.txt"
        
        with open(text_file, 'w', encoding='utf-8') as f:
            for line in test_lines:
                f.write(line + '\n')
        
        result = read_lines_file(text_file)
        assert result == test_lines
    
    def test_read_lines_file_mixed_line_endings(self, tmp_path):
        """Test reading file with mixed line endings."""
        text_file = tmp_path / "test.txt"
        
        with open(text_file, 'wb') as f:
            f.write(b"Line 1\nLine 2\r\nLine 3\r")
        
        result = read_lines_file(text_file)
        assert result == ["Line 1", "Line 2", "Line 3"]
    
    def test_write_lines_file_success(self, tmp_path):
        """Test successful lines file writing."""
        test_lines = ["Line 1", "Line 2", "Line 3"]
        text_file = tmp_path / "output.txt"
        
        write_lines_file(text_file, test_lines)
        
        with open(text_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "Line 1\nLine 2\nLine 3\n"
    
    def test_write_lines_file_append(self, tmp_path):
        """Test lines file writing in append mode."""
        text_file = tmp_path / "output.txt"
        
        write_lines_file(text_file, ["Line 1", "Line 2"])
        write_lines_file(text_file, ["Line 3", "Line 4"], append=True)
        
        result = read_lines_file(text_file)
        assert result == ["Line 1", "Line 2", "Line 3", "Line 4"]


class TestDirectoryOperations:
    """Test directory operations."""
    
    def test_ensure_directory_new(self, tmp_path):
        """Test creating a new directory."""
        new_dir = tmp_path / "new_directory"
        
        result = ensure_directory(new_dir)
        
        assert result == new_dir
        assert new_dir.is_dir()
    
    def test_ensure_directory_existing(self, tmp_path):
        """Test ensuring an existing directory."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        
        result = ensure_directory(existing_dir)
        
        assert result == existing_dir
        assert existing_dir.is_dir()
    
    def test_ensure_directory_nested(self, tmp_path):
        """Test creating nested directories."""
        nested_dir = tmp_path / "level1" / "level2" / "level3"
        
        result = ensure_directory(nested_dir)
        
        assert result == nested_dir
        assert nested_dir.is_dir()
    
    def test_create_timestamped_directory(self, tmp_path):
        """Test creating timestamped directory."""
        result = create_timestamped_directory(tmp_path)

        # Check directory was created
        assert result.is_dir()
        assert result.parent == tmp_path
        # Check name contains timestamp pattern (YYYYMMDD)
        assert result.name[0:4].isdigit()  # Year

    def test_create_timestamped_directory_with_prefix(self, tmp_path):
        """Test creating timestamped directory with prefix."""
        result = create_timestamped_directory(tmp_path, prefix="backup")

        # Check directory was created
        assert result.is_dir()
        assert result.parent == tmp_path
        # Check name starts with prefix
        assert result.name.startswith("backup_")
        # Check timestamp follows prefix
        assert result.name[7:11].isdigit()  # Year after "backup_"


class TestFileManipulation:
    """Test file manipulation operations."""
    
    def test_safe_remove_file_existing(self, tmp_path):
        """Test removing an existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        result = safe_remove_file(test_file)
        
        assert result is True
        assert not test_file.exists()
    
    def test_safe_remove_file_nonexistent(self, tmp_path):
        """Test removing a nonexistent file."""
        test_file = tmp_path / "nonexistent.txt"
        
        result = safe_remove_file(test_file)
        
        assert result is False
    
    def test_copy_file_success(self, tmp_path):
        """Test successful file copying."""
        source = tmp_path / "source.txt"
        destination = tmp_path / "dest.txt"
        test_content = "test content"
        
        source.write_text(test_content)
        copy_file(source, destination)
        
        assert destination.exists()
        assert destination.read_text() == test_content
        assert source.exists()  # Original should still exist
    
    def test_copy_file_create_destination_dir(self, tmp_path):
        """Test file copying with destination directory creation."""
        source = tmp_path / "source.txt"
        destination = tmp_path / "subdir" / "dest.txt"
        test_content = "test content"
        
        source.write_text(test_content)
        copy_file(source, destination)
        
        assert destination.exists()
        assert destination.read_text() == test_content
        assert destination.parent.is_dir()
    
    def test_move_file_success(self, tmp_path):
        """Test successful file moving."""
        source = tmp_path / "source.txt"
        destination = tmp_path / "dest.txt"
        test_content = "test content"
        
        source.write_text(test_content)
        move_file(source, destination)
        
        assert destination.exists()
        assert destination.read_text() == test_content
        assert not source.exists()  # Original should be gone
    
    def test_get_file_size(self, tmp_path):
        """Test getting file size."""
        test_file = tmp_path / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)
        
        size = get_file_size(test_file)
        
        assert size == len(test_content.encode('utf-8'))
    
    def test_backup_file_existing(self, tmp_path):
        """Test backing up an existing file."""
        original = tmp_path / "original.txt"
        test_content = "original content"
        original.write_text(test_content)
        
        backup_path = backup_file(original)
        
        expected_backup = tmp_path / "original.txt.bak"
        assert backup_path == expected_backup
        assert backup_path.exists()
        assert backup_path.read_text() == test_content
        assert original.exists()  # Original should still exist
    
    def test_backup_file_nonexistent(self, tmp_path):
        """Test backing up a nonexistent file."""
        nonexistent = tmp_path / "nonexistent.txt"
        
        backup_path = backup_file(nonexistent)
        
        assert backup_path is None
    
    def test_backup_file_custom_suffix(self, tmp_path):
        """Test backing up with custom suffix."""
        original = tmp_path / "original.txt"
        original.write_text("content")
        
        backup_path = backup_file(original, backup_suffix=".backup")
        
        expected_backup = tmp_path / "original.txt.backup"
        assert backup_path == expected_backup
        assert backup_path.exists()


class TestFileSearch:
    """Test file search operations."""
    
    def test_list_files_with_extension_single(self, tmp_path):
        """Test listing files with single extension."""
        # Create test files
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()
        (tmp_path / "file3.log").touch()
        (tmp_path / "file4.py").touch()
        
        result = list_files_with_extension(tmp_path, "txt")
        
        assert len(result) == 2
        assert all(f.suffix == ".txt" for f in result)
        assert all(f.name in ["file1.txt", "file2.txt"] for f in result)
    
    def test_list_files_with_extension_multiple(self, tmp_path):
        """Test listing files with multiple extensions."""
        # Create test files
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.log").touch()
        (tmp_path / "file3.py").touch()
        
        result = list_files_with_extension(tmp_path, ["txt", "log"])
        
        assert len(result) == 2
        assert all(f.suffix in [".txt", ".log"] for f in result)
    
    def test_list_files_with_extension_recursive(self, tmp_path):
        """Test listing files recursively."""
        # Create nested structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "file1.txt").touch()
        (subdir / "file2.txt").touch()
        
        result = list_files_with_extension(tmp_path, "txt", recursive=True)
        
        assert len(result) == 2
        assert any(f.name == "file1.txt" for f in result)
        assert any(f.name == "file2.txt" for f in result)
    
    def test_list_files_with_extension_non_recursive(self, tmp_path):
        """Test listing files non-recursively."""
        # Create nested structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "file1.txt").touch()
        (subdir / "file2.txt").touch()
        
        result = list_files_with_extension(tmp_path, "txt", recursive=False)
        
        assert len(result) == 1
        assert result[0].name == "file1.txt"
    
    def test_list_files_with_extension_dot_prefix(self, tmp_path):
        """Test extension matching with and without dot prefix."""
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.log").touch()
        
        result_with_dot = list_files_with_extension(tmp_path, ".txt")
        result_without_dot = list_files_with_extension(tmp_path, "txt")
        
        assert len(result_with_dot) == 1
        assert len(result_without_dot) == 1
        assert result_with_dot == result_without_dot


class TestErrorHandling:
    """Test error handling in file operations."""
    
    def test_permission_error_handling(self, tmp_path):
        """Test handling of permission errors."""
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with pytest.raises(SummeetsError, match="Permission denied during text file read"):
                read_text_file(tmp_path / "test.txt")
    
    def test_os_error_handling(self, tmp_path):
        """Test handling of OS errors."""
        with patch('pathlib.Path.mkdir', side_effect=OSError("OS error")):
            with pytest.raises(SummeetsError, match="Failed to create directory"):
                ensure_directory(tmp_path / "new_dir")
    
    def test_file_not_found_with_context(self, tmp_path):
        """Test file not found error with proper context."""
        nonexistent = tmp_path / "nonexistent.txt"
        
        with pytest.raises(SummeetsError) as exc_info:
            read_text_file(nonexistent)
        
        assert "text file read" in str(exc_info.value)
        assert str(nonexistent) in str(exc_info.value) or "File not found" in str(exc_info.value)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_file_operations(self, tmp_path):
        """Test operations with empty files."""
        empty_file = tmp_path / "empty.txt"
        empty_file.touch()
        
        # Reading empty text file
        content = read_text_file(empty_file)
        assert content == ""
        
        # Reading empty lines file - returns empty list for empty file
        lines = read_lines_file(empty_file)
        assert lines == []  # Empty file returns empty list
        
        # File size of empty file
        size = get_file_size(empty_file)
        assert size == 0
    
    def test_unicode_content(self, tmp_path):
        """Test operations with Unicode content."""
        unicode_content = "Hello, 世界! 🌍"
        text_file = tmp_path / "unicode.txt"
        
        write_text_file(text_file, unicode_content)
        result = read_text_file(text_file)
        
        assert result == unicode_content
    
    def test_large_file_simulation(self, tmp_path):
        """Test operations with simulated large files."""
        large_lines = [f"Line {i}" for i in range(1000)]
        text_file = tmp_path / "large.txt"
        
        write_lines_file(text_file, large_lines)
        result = read_lines_file(text_file)
        
        assert len(result) == 1000
        assert result[0] == "Line 0"
        assert result[-1] == "Line 999"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])