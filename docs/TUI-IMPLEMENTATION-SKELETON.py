"""
Summeets TUI v2 - Reference Implementation Skeleton

This file provides a complete code skeleton for the modern TUI design.
It demonstrates the architecture, patterns, and anti-flicker strategies
documented in TUI-DESIGN.md.

NOTE: This is a reference skeleton - copy to cli/tui_v2/ and implement.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Iterable, Optional
from datetime import datetime

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Checkbox,
    Collapsible,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    ProgressBar,
    RichLog,
    Rule,
    Select,
    Static,
    TabbedContent,
    TabPane,
)
from textual.worker import get_current_worker


# =============================================================================
# CUSTOM MESSAGES (Thread-Safe UI Communication)
# =============================================================================

class WorkflowProgress(Message):
    """Progress update from background workflow execution."""

    def __init__(self, step: int, total: int, step_name: str, status: str) -> None:
        self.step = step
        self.total = total
        self.step_name = step_name
        self.status = status
        super().__init__()


class WorkflowComplete(Message):
    """Workflow completed successfully."""

    def __init__(self, results: dict) -> None:
        self.results = results
        super().__init__()


class WorkflowError(Message):
    """Workflow encountered an error."""

    def __init__(self, error: str, stage: str = "") -> None:
        self.error = error
        self.stage = stage
        super().__init__()


class FileSelected(Message):
    """User selected a file in the explorer."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__()


# =============================================================================
# STAGE INDICATOR WIDGET
# =============================================================================

class StageIndicator(Static):
    """
    Visual indicator for a single pipeline stage.

    Displays stage name, status icon, and optional progress.
    Uses CSS classes for state-based styling (no flicker).
    """

    DEFAULT_CSS = """
    StageIndicator {
        width: auto;
        min-width: 14;
        height: auto;
        padding: 0 1;
        border: solid #374151;
        background: #111827;
    }

    StageIndicator.stage--pending {
        opacity: 0.5;
    }

    StageIndicator.stage--active {
        border: solid #38bdf8;
        background: #1f2937;
    }

    StageIndicator.stage--complete {
        border: solid #22c55e;
    }

    StageIndicator.stage--error {
        border: solid #ef4444;
        background: #1f2937;
    }

    StageIndicator .stage-name {
        text-style: bold;
        color: #e2e8f0;
    }

    StageIndicator .stage-status {
        color: #94a3b8;
    }
    """

    # Reactive attributes - changes trigger automatic refresh
    status: reactive[str] = reactive("pending")
    progress: reactive[float] = reactive(0.0)

    def __init__(self, stage_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.stage_name = stage_name
        self.add_class("stage--pending")

    def compose(self) -> ComposeResult:
        yield Static(self.stage_name, classes="stage-name")
        yield Static(self._get_status_icon(), classes="stage-status", id="status-icon")

    def _get_status_icon(self) -> str:
        """Return status icon based on current state."""
        icons = {
            "pending": "[ -- ]",
            "active": "[ .. ]",
            "complete": "[ OK ]",
            "error": "[ERR ]",
        }
        return icons.get(self.status, "[ -- ]")

    def watch_status(self, old_status: str, new_status: str) -> None:
        """React to status changes - update CSS class and icon."""
        # Remove old class, add new one (single operation, no flicker)
        self.remove_class(f"stage--{old_status}")
        self.add_class(f"stage--{new_status}")

        # Update status icon
        icon_widget = self.query_one("#status-icon", Static)
        icon_widget.update(self._get_status_icon())


# =============================================================================
# PIPELINE STATUS CONTAINER
# =============================================================================

class PipelineStatus(Container):
    """
    Visual representation of the complete processing pipeline.

    Shows all stages with connectors and highlights the active stage.
    """

    DEFAULT_CSS = """
    PipelineStatus {
        height: auto;
        padding: 1;
        background: #0b1220;
        border: solid #374151;
    }

    PipelineStatus .pipeline-header {
        text-style: bold;
        color: #38bdf8;
        margin-bottom: 1;
    }

    PipelineStatus .pipeline-flow {
        height: auto;
        align: center middle;
    }

    PipelineStatus .stage-connector {
        color: #64748b;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("PIPELINE STATUS", classes="pipeline-header")
        with Horizontal(classes="pipeline-flow"):
            yield StageIndicator("Extract", id="stage-extract")
            yield Static("->", classes="stage-connector")
            yield StageIndicator("Process", id="stage-process")
            yield Static("->", classes="stage-connector")
            yield StageIndicator("Transcribe", id="stage-transcribe")
            yield Static("->", classes="stage-connector")
            yield StageIndicator("Summarize", id="stage-summarize")

    def set_stage_status(self, stage_id: str, status: str) -> None:
        """Update a specific stage's status."""
        stage_map = {
            "extract_audio": "#stage-extract",
            "process_audio": "#stage-process",
            "transcribe": "#stage-transcribe",
            "summarize": "#stage-summarize",
        }
        if stage_id in stage_map:
            try:
                indicator = self.query_one(stage_map[stage_id], StageIndicator)
                indicator.status = status
            except Exception:
                pass

    def reset_all(self) -> None:
        """Reset all stages to pending state."""
        for indicator in self.query(StageIndicator):
            indicator.status = "pending"


# =============================================================================
# FILE EXPLORER (Enhanced DirectoryTree)
# =============================================================================

class FileExplorer(DirectoryTree):
    """
    File browser filtered for supported media and transcript formats.

    Color-codes files by type for easy identification.
    """

    SUPPORTED_VIDEO = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}
    SUPPORTED_AUDIO = {".m4a", ".flac", ".wav", ".mka", ".ogg", ".mp3"}
    SUPPORTED_TRANSCRIPT = {".json", ".txt", ".srt"}

    DEFAULT_CSS = """
    FileExplorer {
        height: 1fr;
        scrollbar-color: #38bdf8;
        scrollbar-color-hover: #818cf8;
    }
    """

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Filter to show only supported file types."""
        all_supported = self.SUPPORTED_VIDEO | self.SUPPORTED_AUDIO | self.SUPPORTED_TRANSCRIPT
        return [
            path for path in paths
            if path.is_dir() or path.suffix.lower() in all_supported
        ]

    def render_label(self, node, base_style, style) -> Text:
        """Color-code files by type."""
        label = super().render_label(node, base_style, style)

        if node.data and hasattr(node.data, 'path') and node.data.path.is_file():
            ext = node.data.path.suffix.lower()
            if ext in self.SUPPORTED_VIDEO:
                label.stylize("bold cyan")
            elif ext in self.SUPPORTED_AUDIO:
                label.stylize("bold green")
            elif ext in self.SUPPORTED_TRANSCRIPT:
                label.stylize("bold yellow")

        return label


# =============================================================================
# FILE INFO PANEL
# =============================================================================

class FileInfo(Static):
    """
    Displays metadata about the selected file.

    Shows file size, duration (if media), and type.
    """

    DEFAULT_CSS = """
    FileInfo {
        height: auto;
        padding: 1;
        background: #111827;
        border: solid #374151;
    }

    FileInfo .info-header {
        text-style: bold;
        color: #38bdf8;
        margin-bottom: 1;
    }

    FileInfo .info-label {
        color: #94a3b8;
    }

    FileInfo .info-value {
        color: #e2e8f0;
    }
    """

    selected_file: reactive[Path | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Static("FILE INFO", classes="info-header")
        yield Static("No file selected", id="file-details")

    def watch_selected_file(self, path: Path | None) -> None:
        """Update display when file selection changes."""
        details = self.query_one("#file-details", Static)

        if path is None:
            details.update("No file selected")
            return

        try:
            size = path.stat().st_size
            size_str = self._format_size(size)
            file_type = self._get_file_type(path)

            info_text = Text()
            info_text.append(f"{path.name}\n", style="bold")
            info_text.append("Size: ", style="#94a3b8")
            info_text.append(f"{size_str}\n", style="#e2e8f0")
            info_text.append("Type: ", style="#94a3b8")
            info_text.append(f"{file_type}", style="#e2e8f0")

            details.update(info_text)
        except Exception as e:
            details.update(f"Error: {e}")

    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def _get_file_type(self, path: Path) -> str:
        """Determine file type from extension."""
        ext = path.suffix.lower()
        if ext in FileExplorer.SUPPORTED_VIDEO:
            return f"Video ({ext.upper()[1:]})"
        elif ext in FileExplorer.SUPPORTED_AUDIO:
            return f"Audio ({ext.upper()[1:]})"
        elif ext in FileExplorer.SUPPORTED_TRANSCRIPT:
            return f"Transcript ({ext.upper()[1:]})"
        return "Unknown"


# =============================================================================
# CONFIGURATION PANEL
# =============================================================================

class ConfigPanel(Container):
    """
    Configuration panel with provider, model, template selection.

    Includes collapsible advanced options.
    """

    DEFAULT_CSS = """
    ConfigPanel {
        height: auto;
        padding: 1;
    }

    ConfigPanel .config-label {
        color: #94a3b8;
        margin-top: 1;
    }

    ConfigPanel Input {
        margin-bottom: 1;
    }

    ConfigPanel Select {
        margin-bottom: 1;
    }

    ConfigPanel Button {
        width: 100%;
        margin-top: 1;
    }

    ConfigPanel Button.primary {
        background: #38bdf8;
        color: #0a0e1a;
    }

    ConfigPanel Button.danger {
        background: #ef4444;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Provider:", classes="config-label")
        yield Select(
            options=[("OpenAI", "openai"), ("Anthropic", "anthropic")],
            value="openai",
            id="select-provider"
        )

        yield Label("Model:", classes="config-label")
        yield Input(value="gpt-4o-mini", id="input-model")

        yield Label("Template:", classes="config-label")
        yield Select(
            options=[
                ("Default", "default"),
                ("SOP", "sop"),
                ("Decision", "decision"),
                ("Brainstorm", "brainstorm"),
                ("Requirements", "requirements"),
            ],
            value="default",
            id="select-template"
        )

        yield Checkbox("Auto-detect template", value=True, id="check-autodetect")

        with Collapsible(title="Advanced Options", collapsed=True):
            yield Label("Chunk Size (seconds):", classes="config-label")
            yield Input(value="1800", id="input-chunk-size")

            yield Label("CoD Passes:", classes="config-label")
            yield Input(value="2", id="input-cod-passes")

            yield Label("Max Tokens:", classes="config-label")
            yield Input(value="3000", id="input-max-tokens")

            yield Checkbox("Normalize audio", value=True, id="check-normalize")

        yield Button("Run Workflow", variant="primary", id="btn-run")
        yield Button("Cancel", variant="error", id="btn-cancel", disabled=True)

    def get_config(self) -> dict:
        """Extract current configuration values."""
        return {
            "provider": self.query_one("#select-provider", Select).value,
            "model": self.query_one("#input-model", Input).value,
            "template": self.query_one("#select-template", Select).value,
            "auto_detect": self.query_one("#check-autodetect", Checkbox).value,
            "chunk_seconds": int(self.query_one("#input-chunk-size", Input).value or 1800),
            "cod_passes": int(self.query_one("#input-cod-passes", Input).value or 2),
            "max_tokens": int(self.query_one("#input-max-tokens", Input).value or 3000),
            "normalize": self.query_one("#check-normalize", Checkbox).value,
        }

    def set_processing(self, is_processing: bool) -> None:
        """Toggle button states during processing."""
        self.query_one("#btn-run", Button).disabled = is_processing
        self.query_one("#btn-cancel", Button).disabled = not is_processing


# =============================================================================
# MAIN APPLICATION
# =============================================================================

class SummeetsApp(App):
    """
    Modern TUI for Summeets video transcription and summarization.

    Features:
    - File browser with format filtering
    - Visual pipeline status with stage indicators
    - Real-time progress and logging
    - Configuration panel with advanced options
    - Summary preview

    Anti-flicker strategies:
    - Reactive attributes for automatic batched updates
    - Worker-based background processing
    - Message-based thread-safe UI updates
    - CSS class toggling instead of full redraws
    """

    CSS = """
    Screen {
        background: #0a0e1a;
        color: #e2e8f0;
    }

    #main-container {
        height: 1fr;
    }

    #left-panel {
        width: 30%;
        background: #111827;
        border: solid #374151;
    }

    #center-panel {
        width: 45%;
        background: #111827;
        border: solid #374151;
    }

    #right-panel {
        width: 25%;
        background: #111827;
        border: solid #374151;
    }

    .panel-header {
        text-style: bold;
        color: #38bdf8;
        padding: 1;
        background: #0b1220;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: #1f2937;
        padding: 0 2;
        color: #94a3b8;
    }

    #stage-log {
        height: 1fr;
        background: #0b1220;
        border: solid #374151;
        padding: 1;
    }

    #current-stage {
        height: auto;
        padding: 1;
        background: #1f2937;
    }

    #current-stage .stage-label {
        text-style: bold;
        color: #38bdf8;
    }

    #current-stage ProgressBar {
        margin-top: 1;
    }

    ProgressBar > .bar--bar {
        color: #38bdf8;
    }

    ProgressBar > .bar--complete {
        color: #22c55e;
    }

    TabPane {
        padding: 0;
    }

    #preview-content {
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "run_workflow", "Run"),
        Binding("c", "focus_config", "Config"),
        Binding("escape", "cancel_workflow", "Cancel"),
    ]

    # Reactive state - changes automatically update UI
    selected_file: reactive[Path | None] = reactive(None)
    current_stage: reactive[str] = reactive("")
    overall_progress: reactive[float] = reactive(0.0)
    is_processing: reactive[bool] = reactive(False)
    summary_content: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-container"):
            # Left Panel: File Browser
            with Vertical(id="left-panel"):
                yield Static("FILE EXPLORER", classes="panel-header")
                yield FileExplorer(".", id="file-explorer")
                yield FileInfo(id="file-info")

            # Center Panel: Pipeline Status and Logs
            with Vertical(id="center-panel"):
                yield PipelineStatus(id="pipeline-status")

                with Container(id="current-stage"):
                    yield Static("Ready to process", classes="stage-label", id="stage-label")
                    yield ProgressBar(total=100, show_eta=True, id="main-progress")

                yield Static("STAGE LOG", classes="panel-header")
                yield RichLog(id="stage-log", highlight=True, markup=True, wrap=True)

            # Right Panel: Config and Preview (Tabbed)
            with Vertical(id="right-panel"):
                with TabbedContent():
                    with TabPane("Config", id="tab-config"):
                        yield ConfigPanel(id="config-panel")
                    with TabPane("Preview", id="tab-preview"):
                        yield ScrollableContainer(
                            Markdown("*No summary available*", id="preview-content")
                        )
                    with TabPane("Log", id="tab-log"):
                        yield RichLog(id="full-log", highlight=True, markup=True, wrap=True)

        yield Static("Ready | No file selected", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize on app start."""
        self.title = "SUMMEETS"
        self.sub_title = "Video Transcription & Summarization"
        self._log("Application started", style="green")

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection in explorer."""
        self.selected_file = event.path
        self.query_one("#file-info", FileInfo).selected_file = event.path
        self._update_status_bar()
        self._log(f"Selected: {event.path.name}", style="cyan")

    @on(Button.Pressed, "#btn-run")
    def handle_run_click(self) -> None:
        """Handle Run button click."""
        self.action_run_workflow()

    @on(Button.Pressed, "#btn-cancel")
    def handle_cancel_click(self) -> None:
        """Handle Cancel button click."""
        self.action_cancel_workflow()

    def on_workflow_progress(self, message: WorkflowProgress) -> None:
        """Handle progress updates from background worker (main thread - safe)."""
        self.current_stage = message.step_name
        self.overall_progress = (message.step / message.total) * 100

        # Update pipeline status (CSS class change - no flicker)
        pipeline = self.query_one("#pipeline-status", PipelineStatus)
        pipeline.set_stage_status(message.step_name, "active")

        # Update progress bar
        progress_bar = self.query_one("#main-progress", ProgressBar)
        progress_bar.update(progress=message.step, total=message.total)

        # Update stage label
        stage_label = self.query_one("#stage-label", Static)
        stage_label.update(f"{message.step_name}: {message.status}")

        # Log to stage log
        self._log(f"[{message.step}/{message.total}] {message.status}")

    def on_workflow_complete(self, message: WorkflowComplete) -> None:
        """Handle workflow completion."""
        self.is_processing = False

        # Update all stages to complete
        pipeline = self.query_one("#pipeline-status", PipelineStatus)
        for stage in ["extract_audio", "process_audio", "transcribe", "summarize"]:
            pipeline.set_stage_status(stage, "complete")

        # Update progress
        progress_bar = self.query_one("#main-progress", ProgressBar)
        progress_bar.update(progress=100, total=100)

        stage_label = self.query_one("#stage-label", Static)
        stage_label.update("Complete!")

        self._log("Workflow completed successfully!", style="bold green")

        # Load summary preview if available
        if "summarize" in message.results:
            summary_file = message.results["summarize"].get("summary_file")
            if summary_file:
                self._load_summary_preview(Path(summary_file))

        self.query_one("#config-panel", ConfigPanel).set_processing(False)
        self._update_status_bar()

    def on_workflow_error(self, message: WorkflowError) -> None:
        """Handle workflow errors."""
        self.is_processing = False

        # Mark current stage as error
        if message.stage:
            pipeline = self.query_one("#pipeline-status", PipelineStatus)
            pipeline.set_stage_status(message.stage, "error")

        stage_label = self.query_one("#stage-label", Static)
        stage_label.update(f"Error: {message.error[:50]}...")

        self._log(f"Error: {message.error}", style="bold red")

        self.query_one("#config-panel", ConfigPanel).set_processing(False)
        self._update_status_bar()

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_run_workflow(self) -> None:
        """Start workflow execution."""
        if self.is_processing:
            self._log("Workflow already in progress", style="yellow")
            return

        if self.selected_file is None:
            self._log("Please select a file first", style="yellow")
            return

        self.is_processing = True
        self.query_one("#config-panel", ConfigPanel).set_processing(True)

        # Reset pipeline status
        pipeline = self.query_one("#pipeline-status", PipelineStatus)
        pipeline.reset_all()

        # Clear logs
        self.query_one("#stage-log", RichLog).clear()

        self._log(f"Starting workflow for: {self.selected_file.name}", style="green")

        # Start background worker
        self.run_workflow()

    def action_cancel_workflow(self) -> None:
        """Cancel running workflow."""
        if not self.is_processing:
            return

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        self.is_processing = False
        self.query_one("#config-panel", ConfigPanel).set_processing(False)
        self._log("Workflow cancelled", style="yellow")
        self._update_status_bar()

    def action_focus_config(self) -> None:
        """Focus on config panel."""
        self.query_one("#select-provider", Select).focus()

    # -------------------------------------------------------------------------
    # Background Worker
    # -------------------------------------------------------------------------

    @work(thread=True, exclusive=True)
    def run_workflow(self) -> None:
        """
        Execute workflow in background thread.

        Uses message posting for thread-safe UI updates.
        Checks is_cancelled before each UI update.
        """
        worker = get_current_worker()

        if self.selected_file is None:
            return

        # Import here to avoid circular imports
        from core.workflow import WorkflowConfig, execute_workflow
        from core.utils.validation import detect_file_type

        config_values = self.query_one("#config-panel", ConfigPanel).get_config()
        file_type = detect_file_type(self.selected_file)

        # Build workflow config
        config = WorkflowConfig(
            input_file=self.selected_file,
            output_dir=Path("out"),
            extract_audio=(file_type == "video"),
            process_audio=(file_type in ["video", "audio"]),
            transcribe=(file_type in ["video", "audio"]),
            summarize=True,
            audio_format="m4a",
            audio_quality="high",
            normalize_audio=config_values["normalize"],
            summary_template=config_values["template"],
            provider=config_values["provider"],
            model=config_values["model"],
            auto_detect_template=config_values["auto_detect"],
        )

        def progress_callback(step: int, total: int, step_name: str, status: str) -> None:
            """Thread-safe progress callback using message posting."""
            if not worker.is_cancelled:
                self.post_message(WorkflowProgress(step, total, step_name, status))

        try:
            results = execute_workflow(config, progress_callback)
            if not worker.is_cancelled:
                self.post_message(WorkflowComplete(results))
        except Exception as e:
            if not worker.is_cancelled:
                self.post_message(WorkflowError(str(e), self.current_stage))

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _log(self, message: str, style: str = "cyan") -> None:
        """
        Log message to both stage log and full log.

        Uses RichLog.write() which is the proper non-flickering approach.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = Text()
        formatted.append(f"[{timestamp}] ", style="dim")
        formatted.append(message, style=style)

        self.query_one("#stage-log", RichLog).write(formatted)
        self.query_one("#full-log", RichLog).write(formatted)

    def _update_status_bar(self) -> None:
        """Update status bar with current state."""
        status_bar = self.query_one("#status-bar", Static)

        parts = []

        if self.is_processing:
            parts.append("Processing")
        else:
            parts.append("Ready")

        if self.selected_file:
            parts.append(self.selected_file.name)
        else:
            parts.append("No file selected")

        config = self.query_one("#config-panel", ConfigPanel).get_config()
        parts.append(f"{config['provider']}/{config['model']}")
        parts.append(f"Template: {config['template']}")

        status_bar.update(" | ".join(parts))

    def _load_summary_preview(self, summary_path: Path) -> None:
        """Load summary into preview pane."""
        try:
            if summary_path.suffix == ".md":
                content = summary_path.read_text(encoding="utf-8")
                self.query_one("#preview-content", Markdown).update(content)
                self._log(f"Summary loaded: {summary_path.name}", style="green")
        except Exception as e:
            self._log(f"Failed to load summary: {e}", style="red")


# =============================================================================
# ENTRY POINT
# =============================================================================

def run() -> None:
    """Launch the Summeets TUI."""
    app = SummeetsApp()
    app.run()


if __name__ == "__main__":
    run()
