"""Unit tests for graceful shutdown module."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os

from src.utils.shutdown import (
    is_shutdown_requested,
    request_shutdown,
    reset_shutdown,
    register_cleanup_handler,
    unregister_cleanup_handler,
    register_temp_file,
    unregister_temp_file,
    check_shutdown,
    graceful_operation,
    JobStateManager,
    _cleanup_handlers,
    _temp_files
)


class TestShutdownState:
    """Tests for shutdown state management."""

    def setup_method(self):
        """Reset state before each test."""
        reset_shutdown()

    def test_initial_state_not_requested(self):
        """Test initial state is not shutdown."""
        assert is_shutdown_requested() is False

    def test_request_shutdown(self):
        """Test requesting shutdown sets the flag."""
        request_shutdown()
        assert is_shutdown_requested() is True

    def test_reset_shutdown(self):
        """Test resetting shutdown clears the flag."""
        request_shutdown()
        reset_shutdown()
        assert is_shutdown_requested() is False

    def test_check_shutdown_raises_when_requested(self):
        """Test check_shutdown raises when shutdown requested."""
        request_shutdown()
        with pytest.raises(InterruptedError):
            check_shutdown()

    def test_check_shutdown_passes_normally(self):
        """Test check_shutdown doesn't raise when no shutdown."""
        check_shutdown()  # Should not raise


class TestCleanupHandlers:
    """Tests for cleanup handler management."""

    def setup_method(self):
        """Clear handlers before each test."""
        _cleanup_handlers.clear()

    def teardown_method(self):
        """Clear handlers after each test."""
        _cleanup_handlers.clear()

    def test_register_handler(self):
        """Test registering a cleanup handler."""
        handler = MagicMock()
        register_cleanup_handler(handler)
        assert handler in _cleanup_handlers

    def test_unregister_handler(self):
        """Test unregistering a cleanup handler."""
        handler = MagicMock()
        register_cleanup_handler(handler)
        unregister_cleanup_handler(handler)
        assert handler not in _cleanup_handlers

    def test_duplicate_registration(self):
        """Test duplicate registration only adds once."""
        handler = MagicMock()
        register_cleanup_handler(handler)
        register_cleanup_handler(handler)
        assert _cleanup_handlers.count(handler) == 1


class TestTempFileManagement:
    """Tests for temporary file tracking."""

    def setup_method(self):
        """Clear temp files before each test."""
        _temp_files.clear()

    def teardown_method(self):
        """Clear temp files after each test."""
        _temp_files.clear()

    def test_register_temp_file(self):
        """Test registering a temp file."""
        path = Path("/tmp/test.txt")
        register_temp_file(path)
        assert path in _temp_files

    def test_unregister_temp_file(self):
        """Test unregistering a temp file."""
        path = Path("/tmp/test.txt")
        register_temp_file(path)
        unregister_temp_file(path)
        assert path not in _temp_files


class TestGracefulOperation:
    """Tests for graceful_operation context manager."""

    def setup_method(self):
        """Reset state before each test."""
        reset_shutdown()

    def test_normal_operation(self):
        """Test normal operation completes successfully."""
        with graceful_operation("test operation"):
            pass  # Should complete without issue

    def test_shutdown_during_operation(self):
        """Test shutdown during operation is detected."""
        with graceful_operation("test operation"):
            request_shutdown()
        # Context manager should complete, shutdown flag should be set
        assert is_shutdown_requested() is True


class TestJobStateManager:
    """Tests for job state persistence."""

    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.jobs_dir = Path(self.temp_dir) / "jobs"
        self.manager = JobStateManager(self.jobs_dir)

    def teardown_method(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        _cleanup_handlers.clear()

    def test_start_job_creates_state_file(self):
        """Test starting a job creates state file."""
        self.manager.start_job("test-job-1", {"input": "test.mp4"})
        state_file = self.jobs_dir / "test-job-1.state.json"
        assert state_file.exists()

    def test_update_state(self):
        """Test updating job state."""
        self.manager.start_job("test-job-2", {"step": 1})
        self.manager.update_state(step=2, progress=50)

        import json
        state_file = self.jobs_dir / "test-job-2.state.json"
        with open(state_file) as f:
            state = json.load(f)

        assert state["step"] == 2
        assert state["progress"] == 50

    def test_complete_job(self):
        """Test completing a job."""
        self.manager.start_job("test-job-3", {})
        self.manager.complete_job({"output": "summary.json"})

        import json
        state_file = self.jobs_dir / "test-job-3.state.json"
        with open(state_file) as f:
            state = json.load(f)

        assert state["status"] == "completed"
        assert state["result"]["output"] == "summary.json"

    def test_fail_job(self):
        """Test failing a job."""
        self.manager.start_job("test-job-4", {})
        self.manager.fail_job("Connection error")

        import json
        state_file = self.jobs_dir / "test-job-4.state.json"
        with open(state_file) as f:
            state = json.load(f)

        assert state["status"] == "failed"
        assert state["error"] == "Connection error"

    def test_get_interrupted_jobs(self):
        """Test finding interrupted jobs."""
        # Create an interrupted job
        import json
        state_file = self.jobs_dir / "interrupted-job.state.json"
        with open(state_file, 'w') as f:
            json.dump({"job_id": "interrupted-job", "status": "interrupted"}, f)

        # Create a completed job (should not be returned)
        completed_file = self.jobs_dir / "completed-job.state.json"
        with open(completed_file, 'w') as f:
            json.dump({"job_id": "completed-job", "status": "completed"}, f)

        interrupted = self.manager.get_interrupted_jobs()
        assert len(interrupted) == 1
        assert interrupted[0]["job_id"] == "interrupted-job"
