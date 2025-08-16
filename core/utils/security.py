"""
Security utilities for safe file operations and data handling.
Provides secure temporary file management and input sanitization.
"""
import os
import tempfile
import logging
import shutil
from pathlib import Path
from typing import Optional, Union, ContextManager, Any
from contextlib import contextmanager

from .exceptions import FileOperationError, ValidationError
from .validation import sanitize_path_input

log = logging.getLogger(__name__)


class SecureTempFile:
    """
    Context manager for secure temporary file handling.
    Ensures proper cleanup and secure permissions.
    """
    
    def __init__(
        self,
        suffix: str = "",
        prefix: str = "summeets_",
        dir: Optional[Union[str, Path]] = None,
        delete_on_exit: bool = True
    ):
        """
        Initialize secure temporary file.
        
        Args:
            suffix: File suffix/extension
            prefix: File prefix
            dir: Directory for temp file (uses system temp if None)
            delete_on_exit: Whether to delete file when context exits
        """
        self.suffix = suffix
        self.prefix = prefix
        self.dir = str(dir) if dir else None
        self.delete_on_exit = delete_on_exit
        self.temp_file = None
        self.path = None
    
    def __enter__(self) -> Path:
        """Create and return the temporary file path."""
        try:
            self.temp_file = tempfile.NamedTemporaryFile(
                suffix=self.suffix,
                prefix=self.prefix,
                dir=self.dir,
                delete=False  # We'll handle deletion manually
            )
            self.path = Path(self.temp_file.name)
            
            # Set secure permissions (readable/writable by owner only)
            os.chmod(self.path, 0o600)
            
            log.debug(f"Created secure temp file: {self.path}")
            return self.path
            
        except Exception as e:
            log.error(f"Failed to create secure temp file: {e}")
            raise FileOperationError(f"Could not create temporary file: {e}") from e
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the temporary file."""
        self._cleanup()
    
    def _cleanup(self):
        """Safely clean up temporary file and handle."""
        if self.temp_file:
            try:
                self.temp_file.close()
            except Exception as e:
                log.warning(f"Error closing temp file handle: {e}")
        
        if self.path and self.path.exists() and self.delete_on_exit:
            try:
                # Ensure file is writable before deletion
                os.chmod(self.path, 0o600)
                self.path.unlink()
                log.debug(f"Cleaned up temp file: {self.path}")
            except Exception as e:
                log.warning(f"Failed to clean up temp file {self.path}: {e}")
    
    def keep_file(self) -> Path:
        """
        Keep the temporary file (don't delete on exit).
        
        Returns:
            Path to the temporary file
        """
        self.delete_on_exit = False
        return self.path


class SecureTempDir:
    """
    Context manager for secure temporary directories.
    Ensures proper cleanup and secure permissions.
    """
    
    def __init__(
        self,
        prefix: str = "summeets_",
        dir: Optional[Union[str, Path]] = None,
        delete_on_exit: bool = True
    ):
        """
        Initialize secure temporary directory.
        
        Args:
            prefix: Directory prefix
            dir: Parent directory (uses system temp if None)
            delete_on_exit: Whether to delete directory when context exits
        """
        self.prefix = prefix
        self.dir = str(dir) if dir else None
        self.delete_on_exit = delete_on_exit
        self.path = None
    
    def __enter__(self) -> Path:
        """Create and return the temporary directory path."""
        try:
            self.path = Path(tempfile.mkdtemp(
                prefix=self.prefix,
                dir=self.dir
            ))
            
            # Set secure permissions (accessible by owner only)
            os.chmod(self.path, 0o700)
            
            log.debug(f"Created secure temp directory: {self.path}")
            return self.path
            
        except Exception as e:
            log.error(f"Failed to create secure temp directory: {e}")
            raise FileOperationError(f"Could not create temporary directory: {e}") from e
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the temporary directory."""
        self._cleanup()
    
    def _cleanup(self):
        """Safely clean up temporary directory and contents."""
        if self.path and self.path.exists() and self.delete_on_exit:
            try:
                shutil.rmtree(self.path)
                log.debug(f"Cleaned up temp directory: {self.path}")
            except Exception as e:
                log.warning(f"Failed to clean up temp directory {self.path}: {e}")
    
    def keep_dir(self) -> Path:
        """
        Keep the temporary directory (don't delete on exit).
        
        Returns:
            Path to the temporary directory
        """
        self.delete_on_exit = False
        return self.path


@contextmanager
def secure_temp_file(
    suffix: str = "",
    prefix: str = "summeets_",
    dir: Optional[Union[str, Path]] = None
) -> ContextManager[Path]:
    """
    Context manager for creating secure temporary files.
    
    Args:
        suffix: File suffix/extension
        prefix: File prefix
        dir: Directory for temp file
        
    Yields:
        Path to the temporary file
        
    Example:
        with secure_temp_file(suffix=".wav") as temp_path:
            # Use temp_path
            process_audio(temp_path)
        # File is automatically cleaned up
    """
    with SecureTempFile(suffix=suffix, prefix=prefix, dir=dir) as temp_path:
        yield temp_path


@contextmanager
def secure_temp_dir(
    prefix: str = "summeets_",
    dir: Optional[Union[str, Path]] = None
) -> ContextManager[Path]:
    """
    Context manager for creating secure temporary directories.
    
    Args:
        prefix: Directory prefix
        dir: Parent directory
        
    Yields:
        Path to the temporary directory
        
    Example:
        with secure_temp_dir() as temp_dir:
            # Use temp_dir
            process_files_in(temp_dir)
        # Directory is automatically cleaned up
    """
    with SecureTempDir(prefix=prefix, dir=dir) as temp_path:
        yield temp_path


def secure_copy(src: Path, dst: Path, preserve_permissions: bool = False) -> None:
    """
    Securely copy a file with validation.
    
    Args:
        src: Source file path
        dst: Destination file path
        preserve_permissions: Whether to preserve source permissions
        
    Raises:
        FileOperationError: If copy operation fails
        ValidationError: If paths are invalid
    """
    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")
    
    if not src.is_file():
        raise ValidationError(f"Source is not a file: {src}")
    
    try:
        # Ensure destination directory exists
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        shutil.copy2(src, dst)
        
        if not preserve_permissions:
            # Set secure permissions on destination
            os.chmod(dst, 0o600)
        
        log.debug(f"Securely copied {src} to {dst}")
        
    except Exception as e:
        log.error(f"Failed to copy {src} to {dst}: {e}")
        raise FileOperationError(f"Could not copy file: {e}") from e


def secure_move(src: Path, dst: Path, preserve_permissions: bool = False) -> None:
    """
    Securely move a file with validation.
    
    Args:
        src: Source file path
        dst: Destination file path
        preserve_permissions: Whether to preserve source permissions
        
    Raises:
        FileOperationError: If move operation fails
        ValidationError: If paths are invalid
    """
    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")
    
    if not src.is_file():
        raise ValidationError(f"Source is not a file: {src}")
    
    try:
        # Ensure destination directory exists
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # Move file
        shutil.move(str(src), str(dst))
        
        if not preserve_permissions:
            # Set secure permissions on destination
            os.chmod(dst, 0o600)
        
        log.debug(f"Securely moved {src} to {dst}")
        
    except Exception as e:
        log.error(f"Failed to move {src} to {dst}: {e}")
        raise FileOperationError(f"Could not move file: {e}") from e


def sanitize_for_logging(message: str) -> str:
    """
    Sanitize message for safe logging by removing sensitive information.
    
    Args:
        message: Original message
        
    Returns:
        Sanitized message safe for logging
    """
    import re
    
    # Remove potential file paths
    message = re.sub(r'[A-Za-z]:\\[^\s]*', '<path>', message)  # Windows paths
    message = re.sub(r'/[^\s]*', '<path>', message)  # Unix paths
    
    # Remove potential API keys or tokens
    message = re.sub(r'[a-zA-Z0-9]{32,}', '<token>', message)
    
    # Remove potential email addresses
    message = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '<email>', message)
    
    return message


def validate_file_operation(
    file_path: Path,
    operation: str,
    required_permissions: str = "r"
) -> None:
    """
    Validate that a file operation is safe and permitted.
    
    Args:
        file_path: Path to validate
        operation: Description of the operation
        required_permissions: Required permissions ("r", "w", "rw")
        
    Raises:
        ValidationError: If operation is not safe
        FileNotFoundError: If file doesn't exist when required
    """
    # Basic path validation
    try:
        resolved_path = file_path.resolve()
    except (OSError, ValueError) as e:
        raise ValidationError(f"Invalid file path for {operation}: {e}")
    
    # Check for directory traversal attempts
    if ".." in str(file_path):
        raise ValidationError(f"Directory traversal not allowed in {operation}")
    
    # Check permissions if file exists
    if resolved_path.exists():
        if "r" in required_permissions and not os.access(resolved_path, os.R_OK):
            raise ValidationError(f"File not readable for {operation}: {resolved_path}")
        
        if "w" in required_permissions and not os.access(resolved_path, os.W_OK):
            raise ValidationError(f"File not writable for {operation}: {resolved_path}")
    
    elif "r" in required_permissions:
        raise FileNotFoundError(f"File not found for {operation}: {resolved_path}")


class SecureFileManager:
    """
    Manager for secure file operations within a session.
    Tracks temporary files and ensures cleanup.
    """
    
    def __init__(self):
        """Initialize the secure file manager."""
        self.temp_files = set()
        self.temp_dirs = set()
    
    def create_temp_file(self, suffix: str = "", prefix: str = "summeets_") -> Path:
        """
        Create a temporary file and track it for cleanup.
        
        Args:
            suffix: File suffix
            prefix: File prefix
            
        Returns:
            Path to temporary file
        """
        temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix,
            prefix=prefix,
            delete=False
        )
        temp_path = Path(temp_file.name)
        temp_file.close()
        
        # Set secure permissions
        os.chmod(temp_path, 0o600)
        
        self.temp_files.add(temp_path)
        log.debug(f"Created tracked temp file: {temp_path}")
        
        return temp_path
    
    def create_temp_dir(self, prefix: str = "summeets_") -> Path:
        """
        Create a temporary directory and track it for cleanup.
        
        Args:
            prefix: Directory prefix
            
        Returns:
            Path to temporary directory
        """
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        os.chmod(temp_dir, 0o700)
        
        self.temp_dirs.add(temp_dir)
        log.debug(f"Created tracked temp directory: {temp_dir}")
        
        return temp_dir
    
    def cleanup(self):
        """Clean up all tracked temporary files and directories."""
        # Clean up files
        for temp_file in list(self.temp_files):
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    log.debug(f"Cleaned up tracked temp file: {temp_file}")
            except Exception as e:
                log.warning(f"Failed to clean up temp file {temp_file}: {e}")
        
        self.temp_files.clear()
        
        # Clean up directories
        for temp_dir in list(self.temp_dirs):
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    log.debug(f"Cleaned up tracked temp directory: {temp_dir}")
            except Exception as e:
                log.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
        
        self.temp_dirs.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()