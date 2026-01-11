"""
TUI-specific exceptions for error handling and recovery.

Provides categorized exceptions for different error types,
enabling appropriate UI responses and error recovery.
"""
from typing import Optional, Dict, Any


class TUIError(Exception):
    """Base exception for all TUI errors."""

    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        recoverable: bool = True,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize TUI error.

        Args:
            message: Technical error message
            user_message: User-friendly message for display
            recoverable: Whether the error is recoverable
            details: Additional error context
        """
        super().__init__(message)
        self.user_message = user_message or message
        self.recoverable = recoverable
        self.details = details or {}


class ConfigurationError(TUIError):
    """Error in configuration handling."""

    def __init__(self, message: str, key: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            user_message=f"Configuration error: {message}",
            **kwargs
        )
        self.key = key


class ValidationError(TUIError):
    """Error in input validation."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(
            message,
            user_message=f"Invalid input: {message}",
            **kwargs
        )
        self.field = field
        self.value = value


class FileOperationError(TUIError):
    """Error in file operations."""

    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            user_message=f"File error: {message}",
            **kwargs
        )
        self.path = path
        self.operation = operation


class WorkflowError(TUIError):
    """Error during workflow execution."""

    def __init__(
        self,
        message: str,
        stage: Optional[str] = None,
        traceback: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            user_message=f"Processing error: {message}",
            recoverable=False,
            **kwargs
        )
        self.stage = stage
        self.traceback = traceback


class ProviderError(TUIError):
    """Error with LLM provider operations."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            user_message=f"Provider error ({provider or 'unknown'}): {message}",
            **kwargs
        )
        self.provider = provider


class CancellationError(TUIError):
    """Operation was cancelled by user."""

    def __init__(self, stage: Optional[str] = None):
        super().__init__(
            f"Operation cancelled at stage: {stage or 'unknown'}",
            user_message="Operation cancelled",
            recoverable=True
        )
        self.stage = stage


class NetworkError(TUIError):
    """Network-related error."""

    def __init__(self, message: str, url: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            user_message="Network error. Check your connection.",
            recoverable=True,
            **kwargs
        )
        self.url = url


class ResourceExhaustedError(TUIError):
    """Resource limits exceeded (memory, disk, etc.)."""

    def __init__(
        self,
        message: str,
        resource: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            user_message=f"Resource exhausted: {resource or 'unknown'}",
            recoverable=False,
            **kwargs
        )
        self.resource = resource


def format_error_for_display(error: Exception) -> str:
    """
    Format an error for user display.

    Args:
        error: Exception to format

    Returns:
        User-friendly error message
    """
    if isinstance(error, TUIError):
        return error.user_message
    elif isinstance(error, FileNotFoundError):
        return f"File not found: {error.filename if hasattr(error, 'filename') else str(error)}"
    elif isinstance(error, PermissionError):
        return "Permission denied. Check file access rights."
    elif isinstance(error, ConnectionError):
        return "Connection error. Check your network."
    elif isinstance(error, TimeoutError):
        return "Operation timed out. Try again later."
    else:
        return f"Unexpected error: {str(error)}"


def classify_error(error: Exception) -> TUIError:
    """
    Classify a generic exception into a TUI-specific error.

    Args:
        error: Exception to classify

    Returns:
        Appropriate TUIError subclass
    """
    if isinstance(error, TUIError):
        return error

    error_str = str(error).lower()

    # Network errors
    if any(term in error_str for term in ["connection", "network", "timeout", "dns"]):
        return NetworkError(str(error))

    # File errors
    if isinstance(error, (FileNotFoundError, PermissionError, OSError)):
        return FileOperationError(str(error))

    # Validation errors
    if "invalid" in error_str or "validation" in error_str:
        return ValidationError(str(error))

    # Provider errors
    if any(term in error_str for term in ["api", "openai", "anthropic", "rate limit"]):
        return ProviderError(str(error))

    # Default to generic TUI error
    return TUIError(str(error))
