"""
Thread-safe utilities for background operations.

Provides:
- CancellationToken for cooperative cancellation
- ThreadSafeTaskList for synchronized task tracking
- WorkerPool for managed background execution
"""
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional, List, Dict, Any, TypeVar, Generic
from contextlib import contextmanager

log = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a background task."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class TaskResult:
    """Result of a completed task."""
    status: TaskStatus
    result: Any = None
    error: Optional[Exception] = None
    elapsed_seconds: float = 0.0


class CancellationToken:
    """
    Cooperative cancellation token for long-running operations.

    Usage:
        token = CancellationToken()

        def worker():
            while not token.is_cancelled:
                # Do work
                if token.is_cancelled:
                    return  # Clean exit

        # Later...
        token.cancel()
    """

    def __init__(self):
        self._cancelled = threading.Event()
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[], None]] = []

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancelled.is_set()

    def cancel(self) -> None:
        """Request cancellation and notify callbacks."""
        self._cancelled.set()
        with self._lock:
            for callback in self._callbacks:
                try:
                    callback()
                except Exception as e:
                    log.warning(f"Cancellation callback error: {e}")

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called on cancellation."""
        with self._lock:
            self._callbacks.append(callback)
            # If already cancelled, call immediately
            if self.is_cancelled:
                try:
                    callback()
                except Exception as e:
                    log.warning(f"Cancellation callback error: {e}")

    def wait(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for cancellation.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if cancelled, False if timeout
        """
        return self._cancelled.wait(timeout)

    def check(self) -> None:
        """
        Check if cancelled and raise if so.

        Raises:
            CancelledError: If cancellation was requested
        """
        if self.is_cancelled:
            raise CancelledError("Operation was cancelled")

    def reset(self) -> None:
        """Reset the cancellation token for reuse."""
        self._cancelled.clear()
        with self._lock:
            self._callbacks.clear()


class CancelledError(Exception):
    """Raised when an operation is cancelled."""
    pass


T = TypeVar('T')


class ThreadSafeList(Generic[T]):
    """
    Thread-safe list implementation for task tracking.

    All operations are atomic and safe for concurrent access.
    """

    def __init__(self, initial: Optional[List[T]] = None):
        self._list: List[T] = list(initial) if initial else []
        self._lock = threading.RLock()

    def append(self, item: T) -> None:
        """Thread-safe append."""
        with self._lock:
            self._list.append(item)

    def remove(self, item: T) -> bool:
        """Thread-safe remove. Returns True if found and removed."""
        with self._lock:
            try:
                self._list.remove(item)
                return True
            except ValueError:
                return False

    def pop(self, index: int = -1) -> T:
        """Thread-safe pop."""
        with self._lock:
            return self._list.pop(index)

    def clear(self) -> None:
        """Thread-safe clear."""
        with self._lock:
            self._list.clear()

    def copy(self) -> List[T]:
        """Return a thread-safe copy of the list."""
        with self._lock:
            return list(self._list)

    def __len__(self) -> int:
        with self._lock:
            return len(self._list)

    def __contains__(self, item: T) -> bool:
        with self._lock:
            return item in self._list

    def __iter__(self):
        """Iterate over a snapshot copy for thread safety."""
        with self._lock:
            return iter(list(self._list))

    @contextmanager
    def atomic(self):
        """Context manager for atomic multi-operation sequences."""
        with self._lock:
            yield self._list


class ThreadSafeDict(Generic[T]):
    """Thread-safe dictionary for shared state."""

    def __init__(self, initial: Optional[Dict[str, T]] = None):
        self._dict: Dict[str, T] = dict(initial) if initial else {}
        self._lock = threading.RLock()

    def get(self, key: str, default: T = None) -> Optional[T]:
        """Thread-safe get."""
        with self._lock:
            return self._dict.get(key, default)

    def set(self, key: str, value: T) -> None:
        """Thread-safe set."""
        with self._lock:
            self._dict[key] = value

    def delete(self, key: str) -> bool:
        """Thread-safe delete. Returns True if key existed."""
        with self._lock:
            if key in self._dict:
                del self._dict[key]
                return True
            return False

    def update(self, data: Dict[str, T]) -> None:
        """Thread-safe bulk update."""
        with self._lock:
            self._dict.update(data)

    def copy(self) -> Dict[str, T]:
        """Return a thread-safe copy."""
        with self._lock:
            return dict(self._dict)

    def keys(self) -> List[str]:
        """Return a copy of keys."""
        with self._lock:
            return list(self._dict.keys())

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._dict

    @contextmanager
    def atomic(self):
        """Context manager for atomic multi-operation sequences."""
        with self._lock:
            yield self._dict


@dataclass
class ManagedTask:
    """A task managed by WorkerPool."""
    id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    future: Optional[Future] = None
    result: Any = None
    error: Optional[Exception] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    cancellation_token: CancellationToken = field(default_factory=CancellationToken)


class WorkerPool:
    """
    Managed thread pool for background operations.

    Features:
    - Task submission with cancellation support
    - Progress tracking and status monitoring
    - Graceful shutdown with timeout
    - Task lifecycle callbacks
    """

    def __init__(
        self,
        max_workers: int = 4,
        thread_name_prefix: str = "summeets-worker"
    ):
        """
        Initialize the worker pool.

        Args:
            max_workers: Maximum concurrent workers
            thread_name_prefix: Prefix for worker thread names
        """
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix
        )
        self._tasks: ThreadSafeDict[ManagedTask] = ThreadSafeDict()
        self._lock = threading.Lock()
        self._shutdown = False
        self._task_counter = 0

    def submit(
        self,
        func: Callable,
        *args,
        task_name: str = "",
        task_id: Optional[str] = None,
        cancellation_token: Optional[CancellationToken] = None,
        on_complete: Optional[Callable[[TaskResult], None]] = None,
        **kwargs
    ) -> str:
        """
        Submit a task for execution.

        Args:
            func: Function to execute
            *args: Function arguments
            task_name: Human-readable task name
            task_id: Optional task ID (auto-generated if not provided)
            cancellation_token: Optional cancellation token
            on_complete: Optional callback when task completes
            **kwargs: Function keyword arguments

        Returns:
            Task ID for tracking
        """
        if self._shutdown:
            raise RuntimeError("WorkerPool is shut down")

        with self._lock:
            self._task_counter += 1
            if task_id is None:
                task_id = f"task-{self._task_counter}"

        task = ManagedTask(
            id=task_id,
            name=task_name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
            cancellation_token=cancellation_token or CancellationToken()
        )

        self._tasks.set(task_id, task)

        # Wrap function to handle lifecycle
        def wrapper():
            task.status = TaskStatus.RUNNING
            task.start_time = time.time()

            try:
                # Inject cancellation token if function accepts it
                if 'cancellation_token' in func.__code__.co_varnames:
                    result = func(*args, cancellation_token=task.cancellation_token, **kwargs)
                else:
                    result = func(*args, **kwargs)

                if task.cancellation_token.is_cancelled:
                    task.status = TaskStatus.CANCELLED
                else:
                    task.status = TaskStatus.COMPLETED
                    task.result = result

            except CancelledError:
                task.status = TaskStatus.CANCELLED

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = e
                log.error(f"Task {task_id} failed: {e}")

            finally:
                task.end_time = time.time()

                # Call completion callback
                if on_complete:
                    elapsed = (task.end_time - task.start_time) if task.start_time else 0
                    try:
                        on_complete(TaskResult(
                            status=task.status,
                            result=task.result,
                            error=task.error,
                            elapsed_seconds=elapsed
                        ))
                    except Exception as e:
                        log.warning(f"Task completion callback error: {e}")

        task.future = self._executor.submit(wrapper)
        return task_id

    def cancel(self, task_id: str) -> bool:
        """
        Cancel a running or pending task.

        Args:
            task_id: ID of the task to cancel

        Returns:
            True if cancellation was initiated
        """
        task = self._tasks.get(task_id)
        if task is None:
            return False

        # Cancel via token (cooperative)
        task.cancellation_token.cancel()

        # Try to cancel the future if not yet started
        if task.future and not task.future.done():
            task.future.cancel()

        return True

    def cancel_all(self) -> int:
        """Cancel all running and pending tasks. Returns count cancelled."""
        count = 0
        for task_id in self._tasks.keys():
            if self.cancel(task_id):
                count += 1
        return count

    def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a task."""
        task = self._tasks.get(task_id)
        return task.status if task else None

    def get_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[TaskResult]:
        """
        Get the result of a completed task.

        Args:
            task_id: ID of the task
            timeout: Maximum seconds to wait for completion

        Returns:
            TaskResult or None if task not found
        """
        task = self._tasks.get(task_id)
        if task is None:
            return None

        if task.future and not task.future.done():
            try:
                task.future.result(timeout=timeout)
            except Exception:
                pass  # Error is captured in task

        elapsed = 0.0
        if task.start_time and task.end_time:
            elapsed = task.end_time - task.start_time

        return TaskResult(
            status=task.status,
            result=task.result,
            error=task.error,
            elapsed_seconds=elapsed
        )

    def wait_all(self, timeout: Optional[float] = None) -> Dict[str, TaskResult]:
        """
        Wait for all tasks to complete.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            Dict mapping task IDs to results
        """
        futures = {}
        for task_id in self._tasks.keys():
            task = self._tasks.get(task_id)
            if task and task.future:
                futures[task_id] = task.future

        results = {}
        try:
            for task_id, future in futures.items():
                try:
                    future.result(timeout=timeout)
                except Exception:
                    pass
                results[task_id] = self.get_result(task_id)
        except Exception:
            pass

        return results

    def cleanup_completed(self) -> int:
        """Remove completed tasks from tracking. Returns count removed."""
        count = 0
        for task_id in list(self._tasks.keys()):
            task = self._tasks.get(task_id)
            if task and task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                self._tasks.delete(task_id)
                count += 1
        return count

    def shutdown(self, wait: bool = True, timeout: Optional[float] = None) -> None:
        """
        Shut down the worker pool.

        Args:
            wait: Whether to wait for pending tasks
            timeout: Maximum seconds to wait
        """
        self._shutdown = True

        # Cancel all running tasks
        self.cancel_all()

        # Shutdown executor
        self._executor.shutdown(wait=wait)

        log.info("WorkerPool shutdown complete")

    @property
    def active_count(self) -> int:
        """Get count of active (running) tasks."""
        count = 0
        for task_id in self._tasks.keys():
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.RUNNING:
                count += 1
        return count

    @property
    def pending_count(self) -> int:
        """Get count of pending tasks."""
        count = 0
        for task_id in self._tasks.keys():
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                count += 1
        return count


# Global worker pool instance
_worker_pool: Optional[WorkerPool] = None


def get_worker_pool() -> WorkerPool:
    """Get the global worker pool instance."""
    global _worker_pool
    if _worker_pool is None:
        _worker_pool = WorkerPool()
    return _worker_pool


def shutdown_worker_pool() -> None:
    """Shutdown the global worker pool."""
    global _worker_pool
    if _worker_pool is not None:
        _worker_pool.shutdown()
        _worker_pool = None
