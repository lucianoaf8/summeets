"""
Graceful shutdown handling for long-running operations.
Provides signal handlers and cleanup utilities.
"""
import atexit
import logging
import signal
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Callable, List, Set

log = logging.getLogger(__name__)

# Global shutdown state
_shutdown_requested = threading.Event()
_cleanup_handlers: List[Callable[[], None]] = []
_temp_files: Set[Path] = set()
_signal_handlers_installed = False
_original_sigint = None
_original_sigterm = None


def is_shutdown_requested() -> bool:
    """Check if shutdown has been requested.

    Returns:
        True if shutdown was requested via signal
    """
    return _shutdown_requested.is_set()


def request_shutdown():
    """Request a graceful shutdown."""
    _shutdown_requested.set()


def reset_shutdown():
    """Reset the shutdown state (for testing)."""
    _shutdown_requested.clear()


def register_cleanup_handler(handler: Callable[[], None]) -> None:
    """Register a cleanup handler to run on shutdown.

    Args:
        handler: Callable that performs cleanup
    """
    if handler not in _cleanup_handlers:
        _cleanup_handlers.append(handler)


def unregister_cleanup_handler(handler: Callable[[], None]) -> None:
    """Unregister a cleanup handler.

    Args:
        handler: Previously registered handler
    """
    if handler in _cleanup_handlers:
        _cleanup_handlers.remove(handler)


def register_temp_file(path: Path) -> None:
    """Register a temporary file for cleanup on shutdown.

    Args:
        path: Path to temporary file
    """
    _temp_files.add(path)


def unregister_temp_file(path: Path) -> None:
    """Unregister a temporary file (e.g., after successful processing).

    Args:
        path: Path to temporary file
    """
    _temp_files.discard(path)


def _cleanup_temp_files() -> None:
    """Clean up all registered temporary files."""
    for path in list(_temp_files):
        try:
            if path.exists():
                if path.is_file():
                    path.unlink()
                    log.debug(f"Cleaned up temp file: {path}")
                elif path.is_dir():
                    import shutil
                    shutil.rmtree(path, ignore_errors=True)
                    log.debug(f"Cleaned up temp directory: {path}")
        except Exception as e:
            log.warning(f"Failed to clean up {path}: {e}")
        finally:
            _temp_files.discard(path)


def _run_cleanup_handlers() -> None:
    """Run all registered cleanup handlers."""
    for handler in reversed(_cleanup_handlers):  # Run in reverse order
        try:
            handler()
        except Exception as e:
            log.warning(f"Cleanup handler failed: {e}")


def _signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals (SIGINT, SIGTERM).

    Sets the shutdown flag only. Actual cleanup runs via the atexit handler
    (_atexit_cleanup) which is safe to call during interpreter shutdown.
    Calling sys.exit() inside a signal handler risks deadlocks and double
    cleanup when the atexit handler also fires.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    signal_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
    log.info(f"Received {signal_name}, initiating graceful shutdown...")

    # Set shutdown flag; cleanup happens in _atexit_cleanup
    request_shutdown()


def install_signal_handlers() -> None:
    """Install signal handlers for graceful shutdown.

    Safe to call multiple times - will only install once.
    """
    global _signal_handlers_installed, _original_sigint, _original_sigterm

    if _signal_handlers_installed:
        return

    try:
        # Store original handlers
        _original_sigint = signal.getsignal(signal.SIGINT)
        _original_sigterm = signal.getsignal(signal.SIGTERM)

        # Install new handlers
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        _signal_handlers_installed = True
        log.debug("Signal handlers installed for graceful shutdown")
    except ValueError:
        # Signal handling only works in main thread
        log.debug("Could not install signal handlers (not in main thread)")


def restore_signal_handlers() -> None:
    """Restore original signal handlers."""
    global _signal_handlers_installed, _original_sigint, _original_sigterm

    if not _signal_handlers_installed:
        return

    try:
        if _original_sigint is not None:
            signal.signal(signal.SIGINT, _original_sigint)
        if _original_sigterm is not None:
            signal.signal(signal.SIGTERM, _original_sigterm)

        _signal_handlers_installed = False
        log.debug("Original signal handlers restored")
    except ValueError:
        pass


def _atexit_cleanup() -> None:
    """Cleanup handler called at interpreter exit."""
    _run_cleanup_handlers()
    _cleanup_temp_files()


# Register atexit handler
atexit.register(_atexit_cleanup)


@contextmanager
def graceful_operation(description: str = "operation"):
    """Context manager for operations that should handle shutdown gracefully.

    Args:
        description: Description of the operation for logging

    Yields:
        None

    Raises:
        InterruptedError: If shutdown was requested during operation
    """
    log.debug(f"Starting {description}")

    try:
        yield
    finally:
        if is_shutdown_requested():
            log.info(f"Shutdown requested during {description}")


def check_shutdown() -> None:
    """Check if shutdown was requested and raise if so.

    Raises:
        InterruptedError: If shutdown was requested
    """
    if is_shutdown_requested():
        raise InterruptedError("Shutdown requested")


class JobStateManager:
    """Manages job state persistence for graceful shutdown recovery.

    Saves job state periodically so work can be resumed after interruption.
    """

    def __init__(self, jobs_dir: Path):
        """Initialize job state manager.

        Args:
            jobs_dir: Directory for storing job state files
        """
        self.jobs_dir = jobs_dir
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._current_job_id: Optional[str] = None
        self._current_state: dict = {}

    def start_job(self, job_id: str, initial_state: dict) -> None:
        """Start tracking a new job.

        Args:
            job_id: Unique job identifier
            initial_state: Initial job state
        """
        self._current_job_id = job_id
        self._current_state = {
            "job_id": job_id,
            "status": "running",
            **initial_state
        }
        self._save_state()

        # Register cleanup handler for this job
        register_cleanup_handler(self._on_shutdown)

    def update_state(self, **kwargs) -> None:
        """Update current job state.

        Args:
            **kwargs: State fields to update
        """
        if self._current_job_id:
            self._current_state.update(kwargs)
            self._save_state()

    def complete_job(self, result: dict = None) -> None:
        """Mark job as completed.

        Args:
            result: Optional result data
        """
        if self._current_job_id:
            self._current_state["status"] = "completed"
            if result:
                self._current_state["result"] = result
            self._save_state()
            unregister_cleanup_handler(self._on_shutdown)
            self._current_job_id = None

    def fail_job(self, error: str) -> None:
        """Mark job as failed.

        Args:
            error: Error message
        """
        if self._current_job_id:
            self._current_state["status"] = "failed"
            self._current_state["error"] = error
            self._save_state()
            unregister_cleanup_handler(self._on_shutdown)
            self._current_job_id = None

    def _save_state(self) -> None:
        """Save current state to disk."""
        if not self._current_job_id:
            return

        import json
        from datetime import datetime

        state_file = self.jobs_dir / f"{self._current_job_id}.state.json"
        self._current_state["updated_at"] = datetime.now().isoformat()

        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(self._current_state, f, indent=2, default=str)
        except Exception as e:
            log.warning(f"Failed to save job state: {e}")

    def _on_shutdown(self) -> None:
        """Handle shutdown - save interrupted state."""
        if self._current_job_id:
            self._current_state["status"] = "interrupted"
            self._save_state()
            log.info(f"Saved interrupted state for job {self._current_job_id}")

    def get_interrupted_jobs(self) -> List[dict]:
        """Get list of interrupted jobs that can be resumed.

        Returns:
            List of interrupted job states
        """
        import json

        interrupted = []
        for state_file in self.jobs_dir.glob("*.state.json"):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                if state.get("status") == "interrupted":
                    interrupted.append(state)
            except Exception:
                pass

        return interrupted
