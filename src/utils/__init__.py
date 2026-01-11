"""
Core utilities for summeets application.

This module contains shared utility functions and classes:
- cache: Caching utilities
- config: Application configuration management
- logging: Structured logging setup
- security: Security utilities and validation
- validation: Input validation functions
- fsio: File system I/O operations
- jobs: Job management and tracking
- exceptions: Custom exception classes
- error_handling: Shared error handling patterns
- file_io: Shared file I/O operations
- secure_config: Secure credential storage with keyring
- threading: Thread-safe utilities and worker pool
"""

# Re-export commonly used utilities for convenience
from .config import SETTINGS
from .logging import setup_logging
from .exceptions import (
    SummeetsError,
    ValidationError,
    TranscriptionError,
    AudioProcessingError,
    FileOperationError
)
from .fsio import get_data_manager
from .validation import (
    sanitize_path_input,
    validate_transcript_file,
    validate_output_dir,
    validate_model_name
)
from .file_io import read_json_file, write_json_file, read_text_file, write_text_file
from .error_handling import handle_file_operation_errors, handle_api_errors
from .secure_config import SecureConfigManager, get_secure_config
from .threading import (
    CancellationToken,
    CancelledError,
    ThreadSafeList,
    ThreadSafeDict,
    WorkerPool,
    get_worker_pool,
)

__all__ = [
    "SETTINGS",
    "setup_logging",
    "SummeetsError",
    "ValidationError",
    "TranscriptionError",
    "AudioProcessingError",
    "FileOperationError",
    "get_data_manager",
    "sanitize_path_input",
    "validate_transcript_file",
    "validate_output_dir",
    "validate_model_name",
    "read_json_file",
    "write_json_file",
    "read_text_file",
    "write_text_file",
    "handle_file_operation_errors",
    "handle_api_errors",
    # Secure config
    "SecureConfigManager",
    "get_secure_config",
    # Threading utilities
    "CancellationToken",
    "CancelledError",
    "ThreadSafeList",
    "ThreadSafeDict",
    "WorkerPool",
    "get_worker_pool",
]