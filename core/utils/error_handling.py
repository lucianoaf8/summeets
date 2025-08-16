"""
Shared error handling utilities and patterns.
Provides consistent error handling across the application.
"""
import logging
import functools
from typing import TypeVar, Callable, Any, Optional, Union, Type
from pathlib import Path

from .exceptions import SummeetsError

log = logging.getLogger(__name__)

T = TypeVar('T')


def handle_file_operation_errors(
    operation: str, 
    file_path: Optional[Union[str, Path]] = None,
    log_level: int = logging.ERROR
) -> Callable:
    """
    Decorator for handling common file operation errors.
    
    Args:
        operation: Description of the operation being performed
        file_path: Optional file path for context
        log_level: Logging level for errors
        
    Returns:
        Decorated function that handles file operation errors
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except FileNotFoundError as e:
                error_msg = f"File not found during {operation}"
                if file_path:
                    error_msg += f" for {file_path}"
                error_msg += f": {e}"
                log.log(log_level, error_msg)
                raise SummeetsError(error_msg) from e
            except PermissionError as e:
                error_msg = f"Permission denied during {operation}"
                if file_path:
                    error_msg += f" for {file_path}"
                error_msg += f": {e}"
                log.log(log_level, error_msg)
                raise SummeetsError(error_msg) from e
            except OSError as e:
                error_msg = f"OS error during {operation}"
                if file_path:
                    error_msg += f" for {file_path}"
                error_msg += f": {e}"
                log.log(log_level, error_msg)
                raise SummeetsError(error_msg) from e
            except Exception as e:
                error_msg = f"Unexpected error during {operation}"
                if file_path:
                    error_msg += f" for {file_path}"
                error_msg += f": {e}"
                log.log(log_level, error_msg)
                raise SummeetsError(error_msg) from e
        return wrapper
    return decorator


def handle_api_errors(
    provider: str,
    operation: str,
    log_level: int = logging.ERROR
) -> Callable:
    """
    Decorator for handling API operation errors.
    
    Args:
        provider: API provider name (e.g., "OpenAI", "Anthropic")
        operation: Description of the operation being performed
        log_level: Logging level for errors
        
    Returns:
        Decorated function that handles API errors
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Check for common API error types
                error_type = type(e).__name__
                if "Auth" in error_type or "auth" in str(e).lower():
                    error_msg = f"{provider} authentication failed during {operation}: {e}"
                elif "Rate" in error_type or "rate" in str(e).lower():
                    error_msg = f"{provider} rate limit exceeded during {operation}: {e}"
                elif "Network" in error_type or "network" in str(e).lower():
                    error_msg = f"{provider} network error during {operation}: {e}"
                elif "Timeout" in error_type or "timeout" in str(e).lower():
                    error_msg = f"{provider} request timeout during {operation}: {e}"
                else:
                    error_msg = f"{provider} API error during {operation}: {e}"
                
                log.log(log_level, error_msg)
                raise SummeetsError(error_msg) from e
        return wrapper
    return decorator


def handle_validation_errors(
    operation: str,
    log_level: int = logging.WARNING
) -> Callable:
    """
    Decorator for handling validation errors.
    
    Args:
        operation: Description of the operation being performed
        log_level: Logging level for errors
        
    Returns:
        Decorated function that handles validation errors
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except (ValueError, TypeError) as e:
                error_msg = f"Validation error during {operation}: {e}"
                log.log(log_level, error_msg)
                raise SummeetsError(error_msg) from e
            except Exception as e:
                error_msg = f"Unexpected error during {operation}: {e}"
                log.log(log_level, error_msg)
                raise SummeetsError(error_msg) from e
        return wrapper
    return decorator


def log_and_raise_error(
    message: str,
    exception_type: Type[Exception] = SummeetsError,
    log_level: int = logging.ERROR,
    original_exception: Optional[Exception] = None
) -> None:
    """
    Log an error message and raise an exception.
    
    Args:
        message: Error message to log and include in exception
        exception_type: Type of exception to raise
        log_level: Logging level for the error
        original_exception: Original exception to chain (optional)
        
    Raises:
        The specified exception type
    """
    log.log(log_level, message)
    if original_exception:
        raise exception_type(message) from original_exception
    else:
        raise exception_type(message)


def safe_file_operation(
    operation: Callable[..., T],
    error_message: str,
    *args,
    **kwargs
) -> T:
    """
    Safely execute a file operation with error handling.
    
    Args:
        operation: Function to execute
        error_message: Base error message for failures
        *args: Arguments to pass to operation
        **kwargs: Keyword arguments to pass to operation
        
    Returns:
        Result of the operation
        
    Raises:
        SummeetsError: If operation fails
    """
    try:
        return operation(*args, **kwargs)
    except FileNotFoundError as e:
        log_and_raise_error(f"{error_message}: File not found - {e}", original_exception=e)
    except PermissionError as e:
        log_and_raise_error(f"{error_message}: Permission denied - {e}", original_exception=e)
    except OSError as e:
        log_and_raise_error(f"{error_message}: OS error - {e}", original_exception=e)
    except Exception as e:
        log_and_raise_error(f"{error_message}: Unexpected error - {e}", original_exception=e)


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator for retrying operations with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_multiplier: Multiplier for delay between retries
        exceptions: Tuple of exceptions to catch and retry
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import time
            
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        # Last attempt, re-raise the exception
                        raise
                    
                    log.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff_multiplier
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


class ErrorContext:
    """
    Context manager for consistent error handling and logging.
    
    Usage:
        with ErrorContext("processing audio file", file_path="audio.mp3"):
            # operations that might fail
            process_audio()
    """
    
    def __init__(
        self,
        operation: str,
        log_level: int = logging.ERROR,
        **context_vars
    ):
        self.operation = operation
        self.log_level = log_level
        self.context_vars = context_vars
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            context_str = ""
            if self.context_vars:
                context_parts = [f"{k}={v}" for k, v in self.context_vars.items()]
                context_str = f" ({', '.join(context_parts)})"
            
            error_msg = f"Error during {self.operation}{context_str}: {exc_val}"
            log.log(self.log_level, error_msg)
            
            # Convert to SummeetsError if it's not already
            if not isinstance(exc_val, SummeetsError):
                raise SummeetsError(error_msg) from exc_val
        
        return False  # Don't suppress the exception