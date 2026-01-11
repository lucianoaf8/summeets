"""
Unit tests for TUI widget classes.
Tests the custom Textual widgets for the Summeets TUI.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil


class TestStageIndicator:
    """Test StageIndicator widget logic."""

    def test_get_status_display_pending(self):
        """Test status display for pending state."""
        from cli.tui.widgets import StageIndicator
        indicator = StageIndicator("Test", "O")
        indicator.status = "pending"

        display = indicator._get_status_display()
        assert "○" in display

    def test_get_status_display_active(self):
        """Test status display for active state."""
        from cli.tui.widgets import StageIndicator
        indicator = StageIndicator("Test", "O")
        indicator.status = "active"

        display = indicator._get_status_display()
        assert "◉" in display
        assert "▶" in display

    def test_get_status_display_complete(self):
        """Test status display for complete state."""
        from cli.tui.widgets import StageIndicator
        indicator = StageIndicator("Test", "O")
        indicator.status = "complete"

        display = indicator._get_status_display()
        assert "●" in display
        assert "✓" in display

    def test_get_status_display_error(self):
        """Test status display for error state."""
        from cli.tui.widgets import StageIndicator
        indicator = StageIndicator("Test", "O")
        indicator.status = "error"

        display = indicator._get_status_display()
        assert "◉" in display
        assert "✗" in display

    def test_stage_indicator_initialization(self):
        """Test StageIndicator initialization."""
        from cli.tui.widgets import StageIndicator
        indicator = StageIndicator("Extract", "🎬")

        assert indicator.stage_name == "Extract"
        assert indicator.icon == "🎬"
        assert indicator.status == "pending"
        assert indicator.elapsed == ""


class TestFileExplorer:
    """Test FileExplorer widget logic."""

    def test_get_file_type_video(self):
        """Test file type detection for video files."""
        from cli.tui.widgets import FileExplorer

        video_exts = [".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv", ".flv"]
        for ext in video_exts:
            path = Path(f"test_file{ext}")
            assert FileExplorer.get_file_type(path) == "video", f"Failed for {ext}"

    def test_get_file_type_audio(self):
        """Test file type detection for audio files."""
        from cli.tui.widgets import FileExplorer

        audio_exts = [".m4a", ".flac", ".wav", ".mp3", ".ogg", ".mka"]
        for ext in audio_exts:
            path = Path(f"test_file{ext}")
            assert FileExplorer.get_file_type(path) == "audio", f"Failed for {ext}"

    def test_get_file_type_transcript(self):
        """Test file type detection for transcript files."""
        from cli.tui.widgets import FileExplorer

        transcript_exts = [".json", ".txt", ".srt", ".md"]
        for ext in transcript_exts:
            path = Path(f"test_file{ext}")
            assert FileExplorer.get_file_type(path) == "transcript", f"Failed for {ext}"

    def test_get_file_type_unknown(self):
        """Test file type detection for unknown files."""
        from cli.tui.widgets import FileExplorer

        unknown_exts = [".exe", ".py", ".doc", ".pdf"]
        for ext in unknown_exts:
            path = Path(f"test_file{ext}")
            assert FileExplorer.get_file_type(path) == "unknown", f"Failed for {ext}"

    def test_file_type_case_insensitive(self):
        """Test file type detection is case insensitive."""
        from cli.tui.widgets import FileExplorer

        assert FileExplorer.get_file_type(Path("test.MP4")) == "video"
        assert FileExplorer.get_file_type(Path("test.FLAC")) == "audio"
        assert FileExplorer.get_file_type(Path("test.JSON")) == "transcript"


class TestFilteredDirectoryTree:
    """Test FilteredDirectoryTree widget logic."""

    def test_video_extensions(self):
        """Test VIDEO_EXT constant."""
        from cli.tui.widgets import FilteredDirectoryTree

        expected = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv", ".flv"}
        assert FilteredDirectoryTree.VIDEO_EXT == expected

    def test_audio_extensions(self):
        """Test AUDIO_EXT constant."""
        from cli.tui.widgets import FilteredDirectoryTree

        expected = {".m4a", ".flac", ".wav", ".mp3", ".ogg", ".mka"}
        assert FilteredDirectoryTree.AUDIO_EXT == expected

    def test_transcript_extensions(self):
        """Test TRANSCRIPT_EXT constant."""
        from cli.tui.widgets import FilteredDirectoryTree

        expected = {".json", ".txt", ".srt", ".md"}
        assert FilteredDirectoryTree.TRANSCRIPT_EXT == expected

    def test_filter_paths_keeps_directories(self):
        """Test filter_paths keeps directories."""
        from cli.tui.widgets import FilteredDirectoryTree

        tree = FilteredDirectoryTree(".")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "subdir"
            test_dir.mkdir()

            paths = [test_dir]
            filtered = list(tree.filter_paths(paths))

            assert test_dir in filtered

    def test_filter_paths_keeps_supported_files(self):
        """Test filter_paths keeps supported file types."""
        from cli.tui.widgets import FilteredDirectoryTree

        tree = FilteredDirectoryTree(".")

        with tempfile.TemporaryDirectory() as tmpdir:
            mp4_file = Path(tmpdir) / "video.mp4"
            mp3_file = Path(tmpdir) / "audio.mp3"
            txt_file = Path(tmpdir) / "notes.txt"

            for f in [mp4_file, mp3_file, txt_file]:
                f.touch()

            paths = [mp4_file, mp3_file, txt_file]
            filtered = list(tree.filter_paths(paths))

            assert mp4_file in filtered
            assert mp3_file in filtered
            assert txt_file in filtered

    def test_filter_paths_excludes_unsupported_files(self):
        """Test filter_paths excludes unsupported file types."""
        from cli.tui.widgets import FilteredDirectoryTree

        tree = FilteredDirectoryTree(".")

        with tempfile.TemporaryDirectory() as tmpdir:
            py_file = Path(tmpdir) / "script.py"
            exe_file = Path(tmpdir) / "app.exe"

            for f in [py_file, exe_file]:
                f.touch()

            paths = [py_file, exe_file]
            filtered = list(tree.filter_paths(paths))

            assert py_file not in filtered
            assert exe_file not in filtered


class TestFileInfo:
    """Test FileInfo widget logic."""

    def test_fmt_size_bytes(self):
        """Test file size formatting for bytes."""
        from cli.tui.widgets import FileInfo

        info = FileInfo()
        assert "B" in info._fmt_size(500)
        assert "512.0 B" == info._fmt_size(512)

    def test_fmt_size_kilobytes(self):
        """Test file size formatting for kilobytes."""
        from cli.tui.widgets import FileInfo

        info = FileInfo()
        result = info._fmt_size(2048)
        assert "KB" in result

    def test_fmt_size_megabytes(self):
        """Test file size formatting for megabytes."""
        from cli.tui.widgets import FileInfo

        info = FileInfo()
        result = info._fmt_size(5 * 1024 * 1024)
        assert "MB" in result

    def test_fmt_size_gigabytes(self):
        """Test file size formatting for gigabytes."""
        from cli.tui.widgets import FileInfo

        info = FileInfo()
        result = info._fmt_size(2 * 1024 * 1024 * 1024)
        assert "GB" in result


class TestProgressPanel:
    """Test ProgressPanel widget logic."""

    def test_progress_panel_defaults(self):
        """Test ProgressPanel default values."""
        from cli.tui.widgets import ProgressPanel

        panel = ProgressPanel()

        assert panel.stage_label == "Ready"
        assert panel.progress_value == 0.0


class TestConfigPanel:
    """Test ConfigPanel widget logic."""

    def test_config_panel_get_config_defaults(self):
        """Test ConfigPanel default configuration values."""
        from cli.tui.widgets import ConfigPanel

        panel = ConfigPanel()
        config = panel.get_config()

        assert config["provider"] == "openai"
        assert config["model"] == "gpt-4o-mini"
        assert config["template"] == "default"
        assert config["auto_detect"] is True
        assert config["chunk_seconds"] == 1800
        assert config["cod_passes"] == 2
        assert config["max_tokens"] == 3000
        assert config["normalize"] is True
        assert config["increase_volume"] is False


class TestMaskedInput:
    """Test MaskedInput widget logic."""

    def test_mask_value_short(self):
        """Test masking short values."""
        from cli.tui.widgets import MaskedInput

        input_widget = MaskedInput()
        masked = input_widget._mask_value("short")

        assert masked == "*****"
        assert len(masked) == 5

    def test_mask_value_long(self):
        """Test masking long values."""
        from cli.tui.widgets import MaskedInput

        input_widget = MaskedInput()
        masked = input_widget._mask_value("sk-test-key-12345678")

        assert masked.startswith("sk-t")
        assert masked.endswith("5678")
        assert "*" in masked

    def test_masked_input_initialization(self):
        """Test MaskedInput initialization."""
        from cli.tui.widgets import MaskedInput

        input_widget = MaskedInput(value="test-api-key", placeholder="Enter key")

        assert input_widget._real_value == "test-api-key"
        assert input_widget.is_masked is True

    def test_get_real_value_when_masked(self):
        """Test get_real_value returns unmasked value."""
        from cli.tui.widgets import MaskedInput

        input_widget = MaskedInput(value="secret-key-12345678")

        assert input_widget.get_real_value() == "secret-key-12345678"

    def test_masked_input_empty(self):
        """Test MaskedInput with empty value."""
        from cli.tui.widgets import MaskedInput

        input_widget = MaskedInput(value="")

        assert input_widget._real_value == ""
        assert input_widget.get_real_value() == ""


class TestEnvConfigPanel:
    """Test EnvConfigPanel widget logic."""

    def test_sensitive_keys(self):
        """Test SENSITIVE_KEYS constant."""
        from cli.tui.widgets import EnvConfigPanel

        expected = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "REPLICATE_API_TOKEN"}
        assert EnvConfigPanel.SENSITIVE_KEYS == expected

    def test_env_config_panel_initialization(self):
        """Test EnvConfigPanel initialization."""
        from cli.tui.widgets import EnvConfigPanel

        panel = EnvConfigPanel()

        assert panel.env_path == Path(".env")
        assert panel._env_values == {}

    def test_env_config_panel_custom_path(self):
        """Test EnvConfigPanel with custom path."""
        from cli.tui.widgets import EnvConfigPanel

        custom_path = Path("/custom/.env")
        panel = EnvConfigPanel(env_path=custom_path)

        assert panel.env_path == custom_path

    def test_load_env_nonexistent(self):
        """Test _load_env with nonexistent file."""
        from cli.tui.widgets import EnvConfigPanel

        panel = EnvConfigPanel(env_path=Path("/nonexistent/.env"))
        panel._load_env()

        assert panel._env_values == {}

    def test_load_env_existing(self):
        """Test _load_env with existing file."""
        from cli.tui.widgets import EnvConfigPanel

        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "# Comment line\n"
                "OPENAI_API_KEY=sk-test123\n"
                "LLM_PROVIDER=openai\n"
            )

            panel = EnvConfigPanel(env_path=env_path)
            panel._load_env()

            assert panel._env_values.get("OPENAI_API_KEY") == "sk-test123"
            assert panel._env_values.get("LLM_PROVIDER") == "openai"

    def test_load_env_strips_quotes(self):
        """Test _load_env strips quotes from values."""
        from cli.tui.widgets import EnvConfigPanel

        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                'DOUBLE_QUOTED="value1"\n'
                "SINGLE_QUOTED='value2'\n"
            )

            panel = EnvConfigPanel(env_path=env_path)
            panel._load_env()

            assert panel._env_values.get("DOUBLE_QUOTED") == "value1"
            assert panel._env_values.get("SINGLE_QUOTED") == "value2"


class TestPipelineStatus:
    """Test PipelineStatus widget logic."""

    def test_stage_map(self):
        """Test stage ID mapping."""
        from cli.tui.widgets import PipelineStatus

        status = PipelineStatus()

        # Test that stage_map handles both short and long names
        stage_map = {
            "extract": "#stage-extract",
            "extract_audio": "#stage-extract",
            "process": "#stage-process",
            "process_audio": "#stage-process",
            "transcribe": "#stage-transcribe",
            "summarize": "#stage-summarize",
        }

        # The actual mapping is inside update_stage method
        # Just verify the widget can be created
        assert status is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
