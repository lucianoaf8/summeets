"""
Custom Textual messages for thread-safe UI communication.

These messages enable background workers to safely update the UI
by posting messages that are handled on the main thread.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from textual.message import Message


class StageUpdate(Message):
    """Update a pipeline stage status."""

    def __init__(
        self,
        stage_id: str,
        status: str,
        progress: float = 0,
        elapsed: str = ""
    ) -> None:
        self.stage_id = stage_id
        self.status = status  # pending, active, complete, error
        self.progress = progress
        self.elapsed = elapsed
        super().__init__()


class LogMessage(Message):
    """Add a log entry to the activity log."""

    def __init__(self, text: str, style: str = "", level: str = "info") -> None:
        self.text = text
        self.style = style
        self.level = level  # info, warning, error, success
        super().__init__()


class OverallProgress(Message):
    """Update the overall progress bar."""

    def __init__(self, progress: float, label: str = "", eta: str = "") -> None:
        self.progress = progress  # 0-100
        self.label = label
        self.eta = eta
        super().__init__()


class WorkflowStarted(Message):
    """Workflow execution has started."""

    def __init__(self, file_path: Path, file_type: str) -> None:
        self.file_path = file_path
        self.file_type = file_type
        super().__init__()


class WorkflowComplete(Message):
    """Workflow completed successfully."""

    def __init__(self, results: Dict[str, Any], duration: float = 0) -> None:
        self.results = results
        self.duration = duration
        super().__init__()


class WorkflowError(Message):
    """Workflow encountered an error."""

    def __init__(self, error: str, stage: str = "", traceback: str = "") -> None:
        self.error = error
        self.stage = stage
        self.traceback = traceback
        super().__init__()


class WorkflowCancelled(Message):
    """Workflow was cancelled by user."""

    def __init__(self, stage: str = "") -> None:
        self.stage = stage
        super().__init__()


class FileSelected(Message):
    """User selected a file in the explorer."""

    def __init__(self, path: Path, file_type: str) -> None:
        self.path = path
        self.file_type = file_type
        super().__init__()


class ConfigChanged(Message):
    """Configuration setting was changed."""

    def __init__(self, key: str, value: Any) -> None:
        self.key = key
        self.value = value
        super().__init__()


class SummaryLoaded(Message):
    """Summary file was loaded for preview."""

    def __init__(self, content: str, file_path: Path) -> None:
        self.content = content
        self.file_path = file_path
        super().__init__()
