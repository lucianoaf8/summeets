"""
Unit tests for error handling utilities.
Tests decorators, context managers, and error handling patterns.
"""
import pytest
import tempfile
import logging
from pathlib import Path
from unittest.mock import Mock, patch

from core.utils.error_handling import (
    handle_file_operation_errors, handle_api_errors, handle_validation_errors,
    log_and_raise_error, safe_file_operation, with_retry, ErrorContext
)
from core.utils.exceptions import SummeetsError


class TestFileOperationErrorDecorator:
    """Test the file operation error decorator."""
    
    def test_successful_operation(self):
        """Test decorator doesn't interfere with successful operations."""
        @handle_file_operation_errors("test operation")
        def successful_func():
            return "success"
        
        result = successful_func()
        assert result == "success"
    
    def test_file_not_found_error(self):
        """Test handling of FileNotFoundError."""
        @handle_file_operation_errors("test operation")
        def failing_func():
            raise FileNotFoundError("File not found")
        
        with pytest.raises(SummeetsError, match="File not found during test operation"):
            failing_func()
    
    def test_permission_error(self):
        """Test handling of PermissionError."""
        @handle_file_operation_errors("test operation")
        def failing_func():
            raise PermissionError("Permission denied")
        
        with pytest.raises(SummeetsError, match="Permission denied during test operation"):
            failing_func()
    
    def test_os_error(self):
        """Test handling of OSError."""
        @handle_file_operation_errors("test operation")
        def failing_func():
            raise OSError("OS error")
        
        with pytest.raises(SummeetsError, match="OS error during test operation"):
            failing_func()
    
    def test_unexpected_error(self):
        """Test handling of unexpected errors."""
        @handle_file_operation_errors("test operation")
        def failing_func():
            raise ValueError("Unexpected error")
        
        with pytest.raises(SummeetsError, match="Unexpected error during test operation"):
            failing_func()
    
    def test_with_file_path_context(self):
        """Test decorator with file path context."""
        @handle_file_operation_errors("test operation", file_path="/test/path")
        def failing_func():
            raise FileNotFoundError("File not found")
        
        with pytest.raises(SummeetsError, match="File not found during test operation for /test/path"):
            failing_func()


class TestAPIErrorDecorator:
    """Test the API error decorator."""
    
    def test_successful_operation(self):
        """Test decorator doesn't interfere with successful operations."""
        @handle_api_errors("TestAPI", "test operation")
        def successful_func():
            return "success"
        
        result = successful_func()
        assert result == "success"
    
    def test_authentication_error(self):
        """Test handling of authentication errors."""
        @handle_api_errors("TestAPI", "test operation")
        def failing_func():
            raise Exception("Authentication failed")
        
        with pytest.raises(SummeetsError, match="TestAPI authentication failed"):
            failing_func()
    
    def test_rate_limit_error(self):
        """Test handling of rate limit errors."""
        @handle_api_errors("TestAPI", "test operation")
        def failing_func():
            raise Exception("Rate limit exceeded")
        
        with pytest.raises(SummeetsError, match="TestAPI rate limit exceeded"):
            failing_func()
    
    def test_network_error(self):
        """Test handling of network errors."""
        @handle_api_errors("TestAPI", "test operation")
        def failing_func():
            raise Exception("Network timeout")
        
        with pytest.raises(SummeetsError, match="TestAPI network error"):
            failing_func()
    
    def test_generic_api_error(self):
        """Test handling of generic API errors."""
        @handle_api_errors("TestAPI", "test operation")
        def failing_func():
            raise Exception("Some API error")
        
        with pytest.raises(SummeetsError, match="TestAPI API error"):
            failing_func()


class TestValidationErrorDecorator:
    """Test the validation error decorator."""
    
    def test_successful_operation(self):
        """Test decorator doesn't interfere with successful operations."""
        @handle_validation_errors("test operation")
        def successful_func():
            return "success"
        
        result = successful_func()
        assert result == "success"
    
    def test_value_error(self):
        """Test handling of ValueError."""
        @handle_validation_errors("test operation")
        def failing_func():
            raise ValueError("Invalid value")
        
        with pytest.raises(SummeetsError, match="Validation error during test operation"):
            failing_func()
    
    def test_type_error(self):
        """Test handling of TypeError."""
        @handle_validation_errors("test operation")
        def failing_func():
            raise TypeError("Invalid type")
        
        with pytest.raises(SummeetsError, match="Validation error during test operation"):
            failing_func()
    
    def test_unexpected_error(self):
        """Test handling of unexpected errors."""
        @handle_validation_errors("test operation")
        def failing_func():
            raise RuntimeError("Unexpected error")
        
        with pytest.raises(SummeetsError, match="Unexpected error during test operation"):
            failing_func()


class TestLogAndRaiseError:
    """Test the log_and_raise_error function."""
    
    @patch('core.utils.error_handling.log')
    def test_basic_error_logging(self, mock_log):
        """Test basic error logging and raising."""
        with pytest.raises(SummeetsError, match="Test error message"):
            log_and_raise_error("Test error message")
        
        mock_log.log.assert_called_once_with(logging.ERROR, "Test error message")
    
    @patch('core.utils.error_handling.log')
    def test_custom_exception_type(self, mock_log):
        """Test with custom exception type."""
        with pytest.raises(ValueError, match="Test error message"):
            log_and_raise_error("Test error message", exception_type=ValueError)
    
    @patch('core.utils.error_handling.log')
    def test_custom_log_level(self, mock_log):
        """Test with custom log level."""
        with pytest.raises(SummeetsError):
            log_and_raise_error("Test error message", log_level=logging.WARNING)
        
        mock_log.log.assert_called_once_with(logging.WARNING, "Test error message")
    
    @patch('core.utils.error_handling.log')
    def test_with_original_exception(self, mock_log):
        """Test with original exception chaining."""
        original_error = ValueError("Original error")
        
        with pytest.raises(SummeetsError) as exc_info:
            log_and_raise_error("New error message", original_exception=original_error)
        
        assert exc_info.value.__cause__ == original_error


class TestSafeFileOperation:
    """Test the safe_file_operation function."""
    
    def test_successful_operation(self):
        """Test successful operation."""
        def successful_op():
            return "success"
        
        result = safe_file_operation(successful_op, "Test operation")
        assert result == "success"
    
    def test_file_not_found_error(self):
        """Test handling of FileNotFoundError."""
        def failing_op():
            raise FileNotFoundError("File not found")
        
        with pytest.raises(SummeetsError, match="Test operation: File not found"):
            safe_file_operation(failing_op, "Test operation")
    
    def test_permission_error(self):
        """Test handling of PermissionError."""
        def failing_op():
            raise PermissionError("Permission denied")
        
        with pytest.raises(SummeetsError, match="Test operation: Permission denied"):
            safe_file_operation(failing_op, "Test operation")
    
    def test_with_arguments(self):
        """Test operation with arguments."""
        def op_with_args(x, y, z=None):
            return x + y + (z or 0)
        
        result = safe_file_operation(op_with_args, "Test operation", 1, 2, z=3)
        assert result == 6


class TestRetryDecorator:
    """Test the retry decorator."""
    
    def test_successful_operation(self):
        """Test decorator doesn't interfere with successful operations."""
        @with_retry(max_attempts=3)
        def successful_func():
            return "success"
        
        result = successful_func()
        assert result == "success"
    
    @patch('time.sleep')
    def test_retry_with_recovery(self, mock_sleep):
        """Test retry mechanism with eventual success."""
        call_count = 0
        
        @with_retry(max_attempts=3, delay=0.1)
        def sometimes_failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = sometimes_failing_func()
        assert result == "success"
        assert call_count == 3
        assert mock_sleep.call_count == 2
    
    @patch('time.sleep')
    def test_retry_exhaustion(self, mock_sleep):
        """Test retry exhaustion with final exception."""
        @with_retry(max_attempts=2, delay=0.1)
        def always_failing_func():
            raise ValueError("Persistent error")
        
        with pytest.raises(ValueError, match="Persistent error"):
            always_failing_func()
        
        assert mock_sleep.call_count == 1
    
    @patch('time.sleep')
    def test_exponential_backoff(self, mock_sleep):
        """Test exponential backoff delays."""
        @with_retry(max_attempts=3, delay=1.0, backoff_multiplier=2.0)
        def always_failing_func():
            raise ValueError("Error")
        
        with pytest.raises(ValueError):
            always_failing_func()
        
        # Should sleep for 1.0, then 2.0
        expected_calls = [pytest.approx(1.0), pytest.approx(2.0)]
        actual_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_calls == expected_calls
    
    def test_specific_exceptions_only(self):
        """Test that only specified exceptions are retried."""
        @with_retry(max_attempts=3, exceptions=(ValueError,))
        def mixed_errors_func():
            raise TypeError("This should not be retried")
        
        with pytest.raises(TypeError):
            mixed_errors_func()


class TestErrorContext:
    """Test the ErrorContext context manager."""
    
    @patch('core.utils.error_handling.log')
    def test_successful_context(self, mock_log):
        """Test context manager with successful operation."""
        with ErrorContext("test operation"):
            result = "success"
        
        assert result == "success"
        mock_log.log.assert_not_called()
    
    @patch('core.utils.error_handling.log')
    def test_error_in_context(self, mock_log):
        """Test context manager with error."""
        with pytest.raises(SummeetsError, match="Error during test operation"):
            with ErrorContext("test operation"):
                raise ValueError("Some error")
        
        mock_log.log.assert_called_once()
    
    @patch('core.utils.error_handling.log')
    def test_context_with_variables(self, mock_log):
        """Test context manager with context variables."""
        with pytest.raises(SummeetsError) as exc_info:
            with ErrorContext("test operation", file_path="test.txt", user_id=123):
                raise ValueError("Some error")
        
        assert "file_path=test.txt" in str(exc_info.value)
        assert "user_id=123" in str(exc_info.value)
    
    def test_summeets_error_preservation(self):
        """Test that SummeetsError is preserved without re-wrapping."""
        original_error = SummeetsError("Original error")
        
        with pytest.raises(SummeetsError, match="Original error"):
            with ErrorContext("test operation"):
                raise original_error
    
    @patch('core.utils.error_handling.log')
    def test_custom_log_level(self, mock_log):
        """Test context manager with custom log level."""
        with pytest.raises(SummeetsError):
            with ErrorContext("test operation", log_level=logging.WARNING):
                raise ValueError("Some error")
        
        mock_log.log.assert_called_once_with(
            logging.WARNING, 
            pytest.any(str)  # We don't care about the exact message
        )


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple error handling patterns."""
    
    def test_decorator_with_context_manager(self):
        """Test combining decorators with context managers."""
        @handle_file_operation_errors("file operation")
        def file_operation_with_context():
            with ErrorContext("processing file", file_name="test.txt"):
                raise FileNotFoundError("File not found")
        
        with pytest.raises(SummeetsError):
            file_operation_with_context()
    
    @patch('time.sleep')
    def test_retry_with_error_handling(self, mock_sleep):
        """Test retry decorator with error handling."""
        attempt_count = 0
        
        @with_retry(max_attempts=2, delay=0.1)
        @handle_file_operation_errors("file operation")
        def failing_file_operation():
            nonlocal attempt_count
            attempt_count += 1
            raise FileNotFoundError("File not found")
        
        with pytest.raises(SummeetsError):
            failing_file_operation()
        
        assert attempt_count == 2  # Should have retried once
        assert mock_sleep.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])