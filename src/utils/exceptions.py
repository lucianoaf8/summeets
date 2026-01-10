"""
Centralized exception hierarchy and error handling patterns.
Provides consistent error handling across the application.
"""
import logging
import traceback
from typing import Optional, Any, Dict
from pathlib import Path

__all__ = [
    'SummeetsError', 'ValidationError', 'AudioProcessingError', 'AudioSelectionError',
    'AudioCompressionError', 'TranscriptionError', 'APIError', 'ReplicateAPIError',
    'LLMProviderError', 'OpenAIError', 'AnthropicError', 'FileOperationError',
    'ConfigurationError', 'create_error_handler', 'sanitize_error_message',
    'sanitize_path', 'log_and_reraise', 'safe_operation', 'ErrorContext'
]


class SummeetsError(Exception):
    """
    Base exception for all Summeets errors.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
            details: Optional additional context
            cause: Optional underlying exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None
        }


class ValidationError(SummeetsError):
    """Raised when input validation fails."""
    pass


class AudioProcessingError(SummeetsError):
    """Raised when audio processing operations fail."""
    pass


class AudioSelectionError(AudioProcessingError):
    """Raised when audio file selection fails."""
    pass


class AudioCompressionError(AudioProcessingError):
    """Raised when audio compression fails."""
    pass


class TranscriptionError(SummeetsError):
    """Raised when transcription operations fail."""
    pass


class APIError(SummeetsError):
    """Raised when external API calls fail."""
    pass


class ReplicateAPIError(APIError):
    """Raised when Replicate API calls fail."""
    pass


class LLMProviderError(SummeetsError):
    """Raised when LLM provider operations fail."""
    pass


class OpenAIError(LLMProviderError):
    """Raised when OpenAI API calls fail."""
    pass


class AnthropicError(LLMProviderError):
    """Raised when Anthropic API calls fail."""
    pass


class FileOperationError(SummeetsError):
    """Raised when file operations fail."""
    pass


class ConfigurationError(SummeetsError):
    """Raised when configuration is invalid."""
    pass


def create_error_handler(logger: logging.Logger, sanitize_paths: bool = True):
    """
    Create a standardized error handler function.
    
    Args:
        logger: Logger instance to use
        sanitize_paths: Whether to sanitize file paths in error messages
        
    Returns:
        Error handler function
    """
    
    def handle_error(
        error: Exception,
        operation: str,
        reraise: bool = True,
        log_level: int = logging.ERROR
    ) -> Optional[SummeetsError]:
        """
        Handle an error with consistent logging and optional re-raising.
        
        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
            reraise: Whether to re-raise the error after logging
            log_level: Logging level to use
            
        Returns:
            Converted SummeetsError if not re-raising, None otherwise
            
        Raises:
            The original or converted exception if reraise=True
        """
        # Convert to SummeetsError if needed
        if isinstance(error, SummeetsError):
            summeets_error = error
        else:
            summeets_error = SummeetsError(
                message=f"Failed to {operation}: {str(error)}",
                cause=error
            )
        
        # Sanitize error message if requested
        message = summeets_error.message
        if sanitize_paths:
            message = sanitize_error_message(message)
        
        # Log the error
        logger.log(
            log_level,
            "Operation failed: %s - %s",
            operation,
            message,
            extra={
                "error_type": summeets_error.__class__.__name__,
                "error_code": summeets_error.error_code,
                "details": summeets_error.details
            }
        )
        
        # Log full traceback at debug level
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Full traceback:", exc_info=error)
        
        if reraise:
            raise summeets_error
        else:
            return summeets_error
    
    return handle_error


def sanitize_error_message(message: str) -> str:
    """
    Sanitize error message to remove sensitive information.

    Args:
        message: Original error message

    Returns:
        Sanitized error message
    """
    import re

    # Replace full paths with just filenames
    # Pattern matches common path patterns
    path_patterns = [
        r'[A-Za-z]:\\[^:\n]*\\([^\\:\n]+)',  # Windows paths
        r'/[^:\n]*/([^/:\n]+)',              # Unix paths
    ]

    sanitized = message
    for pattern in path_patterns:
        sanitized = re.sub(pattern, r'<path>/\1', sanitized)

    # Mask API keys that might appear in error messages
    sanitized = re.sub(r'sk-[a-zA-Z0-9]{20,}', 'sk-***MASKED***', sanitized)
    sanitized = re.sub(r'sk-ant-[a-zA-Z0-9]{20,}', 'sk-ant-***MASKED***', sanitized)
    sanitized = re.sub(r'r8_[a-zA-Z0-9]{20,}', 'r8_***MASKED***', sanitized)

    return sanitized


def sanitize_path(path) -> str:
    """
    Sanitize a path for safe logging - show only filename.

    Args:
        path: Path object or string

    Returns:
        Sanitized path string (filename only)
    """
    from pathlib import Path
    if isinstance(path, Path):
        return f"<path>/{path.name}"
    elif isinstance(path, str):
        return f"<path>/{Path(path).name}"
    return str(path)


def log_and_reraise(
    logger: logging.Logger,
    error: Exception,
    operation: str,
    error_type: type = SummeetsError
) -> None:
    """
    Log an error and re-raise it as a specific type.
    
    Args:
        logger: Logger instance
        error: Original exception
        operation: Description of failed operation
        error_type: Type of exception to raise
        
    Raises:
        Exception of specified type
    """
    message = f"Failed to {operation}: {str(error)}"
    
    logger.error(
        message,
        extra={
            "operation": operation,
            "original_error": str(error),
            "error_type": error.__class__.__name__
        }
    )
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Full traceback:", exc_info=error)
    
    # Create new exception with context
    if issubclass(error_type, SummeetsError):
        raise error_type(message, cause=error)
    else:
        raise error_type(message) from error


def safe_operation(
    operation_name: str,
    logger: logging.Logger,
    reraise_as: type = SummeetsError
):
    """
    Decorator for safe operations with consistent error handling.
    
    Args:
        operation_name: Name of the operation for logging
        logger: Logger instance to use
        reraise_as: Exception type to reraise as
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_and_reraise(logger, e, operation_name, reraise_as)
        
        return wrapper
    return decorator


# Context manager for error handling
class ErrorContext:
    """
    Context manager for handling errors in a specific operation.
    """
    
    def __init__(
        self,
        operation: str,
        logger: logging.Logger,
        reraise_as: Optional[type] = None,
        log_level: int = logging.ERROR
    ):
        """
        Initialize error context.
        
        Args:
            operation: Description of the operation
            logger: Logger instance
            reraise_as: Optional exception type to convert to
            log_level: Logging level for errors
        """
        self.operation = operation
        self.logger = logger
        self.reraise_as = reraise_as or SummeetsError
        self.log_level = log_level
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            log_and_reraise(self.logger, exc_val, self.operation, self.reraise_as)
        return False  # Don't suppress exceptions