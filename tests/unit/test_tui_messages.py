"""
Unit tests for TUI message classes.
Tests the custom Textual messages for thread-safe UI communication.
"""
import pytest
from pathlib import Path

from cli.tui.messages import (
    StageUpdate,
    LogMessage,
    OverallProgress,
    WorkflowStarted,
    WorkflowComplete,
    WorkflowError,
    WorkflowCancelled,
    FileSelected,
    ConfigChanged,
    SummaryLoaded,
)


class TestStageUpdate:
    """Test StageUpdate message."""

    def test_stage_update_basic(self):
        """Test basic StageUpdate creation."""
        msg = StageUpdate("transcribe", "active")

        assert msg.stage_id == "transcribe"
        assert msg.status == "active"
        assert msg.progress == 0
        assert msg.elapsed == ""

    def test_stage_update_with_progress(self):
        """Test StageUpdate with progress values."""
        msg = StageUpdate("summarize", "complete", progress=100, elapsed="5.2s")

        assert msg.stage_id == "summarize"
        assert msg.status == "complete"
        assert msg.progress == 100
        assert msg.elapsed == "5.2s"

    def test_stage_update_status_values(self):
        """Test various stage status values."""
        statuses = ["pending", "active", "complete", "error"]
        for status in statuses:
            msg = StageUpdate("test_stage", status)
            assert msg.status == status


class TestLogMessage:
    """Test LogMessage message."""

    def test_log_message_basic(self):
        """Test basic LogMessage creation."""
        msg = LogMessage("Test log entry")

        assert msg.text == "Test log entry"
        assert msg.style == ""
        assert msg.level == "info"

    def test_log_message_with_style(self):
        """Test LogMessage with style."""
        msg = LogMessage("Error occurred", style="bold red", level="error")

        assert msg.text == "Error occurred"
        assert msg.style == "bold red"
        assert msg.level == "error"

    def test_log_message_levels(self):
        """Test various log levels."""
        levels = ["info", "warning", "error", "success"]
        for level in levels:
            msg = LogMessage(f"Message at {level}", level=level)
            assert msg.level == level


class TestOverallProgress:
    """Test OverallProgress message."""

    def test_overall_progress_basic(self):
        """Test basic OverallProgress creation."""
        msg = OverallProgress(50.0)

        assert msg.progress == 50.0
        assert msg.label == ""
        assert msg.eta == ""

    def test_overall_progress_full(self):
        """Test OverallProgress with all values."""
        msg = OverallProgress(75.5, label="Transcribing...", eta="2m 30s")

        assert msg.progress == 75.5
        assert msg.label == "Transcribing..."
        assert msg.eta == "2m 30s"

    def test_overall_progress_range(self):
        """Test progress values at boundaries."""
        msg_start = OverallProgress(0.0)
        msg_end = OverallProgress(100.0)

        assert msg_start.progress == 0.0
        assert msg_end.progress == 100.0


class TestWorkflowStarted:
    """Test WorkflowStarted message."""

    def test_workflow_started(self):
        """Test WorkflowStarted creation."""
        path = Path("/test/video.mp4")
        msg = WorkflowStarted(path, "video")

        assert msg.file_path == path
        assert msg.file_type == "video"

    def test_workflow_started_types(self):
        """Test various file types."""
        types = ["video", "audio", "transcript"]
        for file_type in types:
            msg = WorkflowStarted(Path(f"/test/file.{file_type}"), file_type)
            assert msg.file_type == file_type


class TestWorkflowComplete:
    """Test WorkflowComplete message."""

    def test_workflow_complete_basic(self):
        """Test basic WorkflowComplete creation."""
        results = {"transcribe": {"file": "transcript.json"}}
        msg = WorkflowComplete(results)

        assert msg.results == results
        assert msg.duration == 0

    def test_workflow_complete_with_duration(self):
        """Test WorkflowComplete with duration."""
        results = {
            "transcribe": {"file": "transcript.json"},
            "summarize": {"file": "summary.md"}
        }
        msg = WorkflowComplete(results, duration=125.5)

        assert msg.results == results
        assert msg.duration == 125.5


class TestWorkflowError:
    """Test WorkflowError message."""

    def test_workflow_error_basic(self):
        """Test basic WorkflowError creation."""
        msg = WorkflowError("Connection failed")

        assert msg.error == "Connection failed"
        assert msg.stage == ""
        assert msg.traceback == ""

    def test_workflow_error_full(self):
        """Test WorkflowError with all details."""
        msg = WorkflowError(
            error="API rate limit exceeded",
            stage="transcribe",
            traceback="Traceback (most recent call last):\n..."
        )

        assert msg.error == "API rate limit exceeded"
        assert msg.stage == "transcribe"
        assert "Traceback" in msg.traceback


class TestWorkflowCancelled:
    """Test WorkflowCancelled message."""

    def test_workflow_cancelled_basic(self):
        """Test basic WorkflowCancelled creation."""
        msg = WorkflowCancelled()

        assert msg.stage == ""

    def test_workflow_cancelled_with_stage(self):
        """Test WorkflowCancelled with stage."""
        msg = WorkflowCancelled(stage="summarize")

        assert msg.stage == "summarize"


class TestFileSelected:
    """Test FileSelected message."""

    def test_file_selected(self):
        """Test FileSelected creation."""
        path = Path("/data/meeting.m4a")
        msg = FileSelected(path, "audio")

        assert msg.path == path
        assert msg.file_type == "audio"


class TestConfigChanged:
    """Test ConfigChanged message."""

    def test_config_changed_string(self):
        """Test ConfigChanged with string value."""
        msg = ConfigChanged("provider", "anthropic")

        assert msg.key == "provider"
        assert msg.value == "anthropic"

    def test_config_changed_bool(self):
        """Test ConfigChanged with boolean value."""
        msg = ConfigChanged("auto_detect", True)

        assert msg.key == "auto_detect"
        assert msg.value is True

    def test_config_changed_int(self):
        """Test ConfigChanged with integer value."""
        msg = ConfigChanged("chunk_seconds", 1800)

        assert msg.key == "chunk_seconds"
        assert msg.value == 1800


class TestSummaryLoaded:
    """Test SummaryLoaded message."""

    def test_summary_loaded(self):
        """Test SummaryLoaded creation."""
        content = "# Meeting Summary\n\nKey points..."
        path = Path("/output/summary.md")
        msg = SummaryLoaded(content, path)

        assert msg.content == content
        assert msg.file_path == path

    def test_summary_loaded_empty_content(self):
        """Test SummaryLoaded with empty content."""
        msg = SummaryLoaded("", Path("/output/empty.md"))

        assert msg.content == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
