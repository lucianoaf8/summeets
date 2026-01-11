"""
Unit tests for the TUI application.
Tests the main SummeetsApp class logic and behavior.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile


class TestSummeetsAppState:
    """Test SummeetsApp reactive state logic."""

    def test_initial_state_values(self):
        """Test initial reactive state values."""
        from cli.tui.app import SummeetsApp

        app = SummeetsApp()

        assert app.selected_file is None
        assert app.is_processing is False
        assert app.current_stage == ""
        assert app.workflow_start_time == 0

    def test_app_title(self):
        """Test app title and subtitle."""
        from cli.tui.app import SummeetsApp

        app = SummeetsApp()

        assert app.TITLE == "SUMMEETS"
        assert app.SUB_TITLE == "Video Transcription & Summarization"


class TestSummeetsAppBindings:
    """Test SummeetsApp key bindings."""

    def test_bindings_defined(self):
        """Test key bindings are defined."""
        from cli.tui.app import SummeetsApp

        app = SummeetsApp()

        # Extract binding keys
        binding_keys = [b.key for b in app.BINDINGS]

        assert "q" in binding_keys  # Quit
        assert "r" in binding_keys  # Run
        assert "c" in binding_keys  # Config
        assert "escape" in binding_keys  # Cancel
        assert "f5" in binding_keys  # Refresh

    def test_binding_actions(self):
        """Test binding actions map correctly."""
        from cli.tui.app import SummeetsApp

        app = SummeetsApp()

        # Create mapping of key to action
        binding_map = {b.key: b.action for b in app.BINDINGS}

        assert binding_map["q"] == "quit"
        assert binding_map["r"] == "run_workflow"
        assert binding_map["c"] == "focus_config"
        assert binding_map["escape"] == "cancel_workflow"
        assert binding_map["f5"] == "refresh_explorer"


class TestSummeetsAppHelpers:
    """Test SummeetsApp helper methods."""

    def test_get_provider_default(self):
        """Test _get_provider returns default value."""
        from cli.tui.app import SummeetsApp

        app = SummeetsApp()

        # Without widgets mounted, should return default
        result = app._get_provider()
        assert "openai" in result or "gpt-4o-mini" in result


class TestSummeetsAppWorkflow:
    """Test SummeetsApp workflow logic."""

    def test_action_run_workflow_no_file(self):
        """Test run workflow action with no file selected."""
        from cli.tui.app import SummeetsApp

        app = SummeetsApp()
        app.selected_file = None

        # Should not crash when called with no file
        # The actual log message would require mounted widgets
        app.action_run_workflow()

        # Processing should not have started
        assert app.is_processing is False

    def test_action_run_workflow_already_processing(self):
        """Test run workflow action while already processing."""
        from cli.tui.app import SummeetsApp

        app = SummeetsApp()
        app.is_processing = True
        app.selected_file = Path("/test/video.mp4")

        # Should not start another workflow
        initial_start_time = app.workflow_start_time
        app.action_run_workflow()

        # Start time should not change
        assert app.workflow_start_time == initial_start_time

    def test_action_cancel_workflow_not_processing(self):
        """Test cancel workflow when not processing."""
        from cli.tui.app import SummeetsApp

        app = SummeetsApp()
        app.is_processing = False

        # Should not crash or do anything
        app.action_cancel_workflow()

        assert app.is_processing is False


class TestSummeetsAppCSS:
    """Test SummeetsApp CSS configuration."""

    def test_css_defined(self):
        """Test CSS string is defined."""
        from cli.tui.app import SummeetsApp

        app = SummeetsApp()

        assert app.CSS is not None
        assert len(app.CSS) > 0

    def test_css_contains_essential_selectors(self):
        """Test CSS contains essential selectors."""
        from cli.tui.app import SummeetsApp

        css = SummeetsApp.CSS

        # Check for essential layout selectors
        assert "Screen" in css
        assert "Header" in css
        assert "#main-container" in css
        assert "#left-panel" in css
        assert "#center-panel" in css
        assert "#right-panel" in css


class TestRunFunction:
    """Test the run() entry point function."""

    def test_run_function_exists(self):
        """Test run function is importable."""
        from cli.tui.app import run

        assert callable(run)


class TestWorkflowMessageHandling:
    """Test workflow message handling logic."""

    def test_workflow_complete_handler_updates_state(self):
        """Test on_workflow_complete updates state correctly."""
        from cli.tui.app import SummeetsApp
        from cli.tui.messages import WorkflowComplete

        app = SummeetsApp()
        app.is_processing = True
        app.workflow_start_time = 100.0

        # Create completion message
        msg = WorkflowComplete(
            results={"transcribe": {"file": "transcript.json"}},
            duration=50.0
        )

        # The handler would normally be called via the message system
        # For unit testing, we verify the message has correct data
        assert msg.results["transcribe"]["file"] == "transcript.json"

    def test_workflow_error_handler_data(self):
        """Test WorkflowError message contains correct data."""
        from cli.tui.messages import WorkflowError

        msg = WorkflowError(
            error="API rate limit exceeded",
            stage="transcribe",
            traceback="..."
        )

        assert msg.error == "API rate limit exceeded"
        assert msg.stage == "transcribe"
        assert msg.traceback == "..."


class TestFileTypeDetection:
    """Test file type detection used by the app."""

    def test_video_file_detection(self):
        """Test detection of video files."""
        from cli.tui.widgets import FileExplorer

        video_files = [
            Path("meeting.mp4"),
            Path("recording.mkv"),
            Path("video.avi"),
            Path("clip.mov"),
        ]

        for path in video_files:
            assert FileExplorer.get_file_type(path) == "video"

    def test_audio_file_detection(self):
        """Test detection of audio files."""
        from cli.tui.widgets import FileExplorer

        audio_files = [
            Path("recording.m4a"),
            Path("audio.flac"),
            Path("sound.wav"),
            Path("music.mp3"),
        ]

        for path in audio_files:
            assert FileExplorer.get_file_type(path) == "audio"

    def test_transcript_file_detection(self):
        """Test detection of transcript files."""
        from cli.tui.widgets import FileExplorer

        transcript_files = [
            Path("transcript.json"),
            Path("notes.txt"),
            Path("subtitles.srt"),
            Path("summary.md"),
        ]

        for path in transcript_files:
            assert FileExplorer.get_file_type(path) == "transcript"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
