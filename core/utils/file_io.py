"""
Shared file I/O utility functions.
Provides consistent file operations across the application.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from .error_handling import handle_file_operation_errors, safe_file_operation

log = logging.getLogger(__name__)


@handle_file_operation_errors("JSON file read")
def read_json_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Read and parse a JSON file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON data
        
    Raises:
        SummeetsError: If file cannot be read or parsed
    """
    file_path = Path(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    log.debug(f"Read JSON file: {file_path}")
    return data


@handle_file_operation_errors("JSON file write")
def write_json_file(
    file_path: Union[str, Path], 
    data: Any, 
    indent: int = 2,
    ensure_ascii: bool = False
) -> None:
    """
    Write data to a JSON file.
    
    Args:
        file_path: Path to output JSON file
        data: Data to write
        indent: JSON indentation level
        ensure_ascii: Whether to ensure ASCII encoding
        
    Raises:
        SummeetsError: If file cannot be written
    """
    file_path = Path(file_path)
    
    # Create parent directory if needed
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
    
    log.debug(f"Wrote JSON file: {file_path}")


@handle_file_operation_errors("text file read")
def read_text_file(file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
    """
    Read a text file.
    
    Args:
        file_path: Path to text file
        encoding: File encoding
        
    Returns:
        File contents as string
        
    Raises:
        SummeetsError: If file cannot be read
    """
    file_path = Path(file_path)
    
    with open(file_path, 'r', encoding=encoding) as f:
        content = f.read()
    
    log.debug(f"Read text file: {file_path}")
    return content


@handle_file_operation_errors("text file write")
def write_text_file(
    file_path: Union[str, Path], 
    content: str, 
    encoding: str = 'utf-8',
    append: bool = False
) -> None:
    """
    Write content to a text file.
    
    Args:
        file_path: Path to output text file
        content: Content to write
        encoding: File encoding
        append: Whether to append to existing file
        
    Raises:
        SummeetsError: If file cannot be written
    """
    file_path = Path(file_path)
    
    # Create parent directory if needed
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    mode = 'a' if append else 'w'
    with open(file_path, mode, encoding=encoding) as f:
        f.write(content)
    
    action = "Appended to" if append else "Wrote"
    log.debug(f"{action} text file: {file_path}")


@handle_file_operation_errors("lines file read")
def read_lines_file(file_path: Union[str, Path], encoding: str = 'utf-8') -> List[str]:
    """
    Read a text file and return lines as a list.
    
    Args:
        file_path: Path to text file
        encoding: File encoding
        
    Returns:
        List of lines (with newlines stripped)
        
    Raises:
        SummeetsError: If file cannot be read
    """
    file_path = Path(file_path)
    
    with open(file_path, 'r', encoding=encoding) as f:
        lines = [line.rstrip('\n\r') for line in f]
    
    log.debug(f"Read {len(lines)} lines from file: {file_path}")
    return lines


@handle_file_operation_errors("lines file write")
def write_lines_file(
    file_path: Union[str, Path], 
    lines: List[str], 
    encoding: str = 'utf-8',
    append: bool = False
) -> None:
    """
    Write lines to a text file.
    
    Args:
        file_path: Path to output text file
        lines: List of lines to write
        encoding: File encoding
        append: Whether to append to existing file
        
    Raises:
        SummeetsError: If file cannot be written
    """
    file_path = Path(file_path)
    
    # Create parent directory if needed
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    mode = 'a' if append else 'w'
    with open(file_path, mode, encoding=encoding) as f:
        for line in lines:
            f.write(line + '\n')
    
    action = "Appended" if append else "Wrote"
    log.debug(f"{action} {len(lines)} lines to file: {file_path}")


def ensure_directory(dir_path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        dir_path: Path to directory
        
    Returns:
        Path object for the directory
        
    Raises:
        SummeetsError: If directory cannot be created
    """
    dir_path = Path(dir_path)
    
    return safe_file_operation(
        lambda: dir_path.mkdir(parents=True, exist_ok=True) or dir_path,
        f"Failed to create directory {dir_path}"
    )


def safe_remove_file(file_path: Union[str, Path]) -> bool:
    """
    Safely remove a file if it exists.
    
    Args:
        file_path: Path to file to remove
        
    Returns:
        True if file was removed, False if it didn't exist
        
    Raises:
        SummeetsError: If file cannot be removed
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return False
    
    safe_file_operation(
        file_path.unlink,
        f"Failed to remove file {file_path}"
    )
    
    log.debug(f"Removed file: {file_path}")
    return True


def copy_file(source: Union[str, Path], destination: Union[str, Path]) -> None:
    """
    Copy a file from source to destination.
    
    Args:
        source: Source file path
        destination: Destination file path
        
    Raises:
        SummeetsError: If file cannot be copied
    """
    import shutil
    
    source = Path(source)
    destination = Path(destination)
    
    # Create destination directory if needed
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    safe_file_operation(
        lambda: shutil.copy2(source, destination),
        f"Failed to copy file from {source} to {destination}"
    )
    
    log.debug(f"Copied file: {source} -> {destination}")


def move_file(source: Union[str, Path], destination: Union[str, Path]) -> None:
    """
    Move a file from source to destination.
    
    Args:
        source: Source file path
        destination: Destination file path
        
    Raises:
        SummeetsError: If file cannot be moved
    """
    import shutil
    
    source = Path(source)
    destination = Path(destination)
    
    # Create destination directory if needed
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    safe_file_operation(
        lambda: shutil.move(str(source), str(destination)),
        f"Failed to move file from {source} to {destination}"
    )
    
    log.debug(f"Moved file: {source} -> {destination}")


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes
        
    Raises:
        SummeetsError: If file cannot be accessed
    """
    file_path = Path(file_path)
    
    size = safe_file_operation(
        lambda: file_path.stat().st_size,
        f"Failed to get size of file {file_path}"
    )
    
    return size


def list_files_with_extension(
    directory: Union[str, Path], 
    extensions: Union[str, List[str]],
    recursive: bool = False
) -> List[Path]:
    """
    List files in a directory with specific extensions.
    
    Args:
        directory: Directory to search
        extensions: File extension(s) to match (with or without leading dot)
        recursive: Whether to search recursively
        
    Returns:
        List of matching file paths
        
    Raises:
        SummeetsError: If directory cannot be accessed
    """
    directory = Path(directory)
    
    if isinstance(extensions, str):
        extensions = [extensions]
    
    # Normalize extensions to include leading dot
    normalized_extensions = []
    for ext in extensions:
        if not ext.startswith('.'):
            ext = '.' + ext
        normalized_extensions.append(ext.lower())
    
    def find_files():
        files = []
        pattern = "**/*" if recursive else "*"
        
        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in normalized_extensions:
                files.append(file_path)
        
        return sorted(files)
    
    files = safe_file_operation(
        find_files,
        f"Failed to list files in directory {directory}"
    )
    
    log.debug(f"Found {len(files)} files with extensions {extensions} in {directory}")
    return files


def create_timestamped_directory(base_path: Union[str, Path], prefix: str = "") -> Path:
    """
    Create a directory with timestamp in the name.
    
    Args:
        base_path: Base directory path
        prefix: Optional prefix for directory name
        
    Returns:
        Path to created directory
        
    Raises:
        SummeetsError: If directory cannot be created
    """
    from datetime import datetime
    
    base_path = Path(base_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if prefix:
        dir_name = f"{prefix}_{timestamp}"
    else:
        dir_name = timestamp
    
    dir_path = base_path / dir_name
    
    return ensure_directory(dir_path)


def backup_file(file_path: Union[str, Path], backup_suffix: str = ".bak") -> Optional[Path]:
    """
    Create a backup of a file if it exists.
    
    Args:
        file_path: Path to file to backup
        backup_suffix: Suffix to add to backup file
        
    Returns:
        Path to backup file if created, None if original file doesn't exist
        
    Raises:
        SummeetsError: If backup cannot be created
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return None
    
    backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)
    copy_file(file_path, backup_path)
    
    log.debug(f"Created backup: {file_path} -> {backup_path}")
    return backup_path