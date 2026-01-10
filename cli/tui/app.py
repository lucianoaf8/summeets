"""
Summeets TUI - Production Application

Modern, flicker-free TUI for video transcription and summarization.
Integrates with the actual workflow engine from src/.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DirectoryTree,
    Footer,
    Header,
    Markdown,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)
from textual.worker import get_current_worker

from .widgets import (
    ConfigPanel,
    FileExplorer,
    FileInfo,
    PipelineStatus,
    ProgressPanel,
)
from .messages import (
    LogMessage,
    OverallProgress,
    StageUpdate,
    WorkflowComplete,
    WorkflowError,
    WorkflowCancelled,
)


class SummeetsApp(App):
    """
    Production TUI for Summeets video transcription and summarization.

    Features:
    - File browser with format filtering
    - Visual pipeline status with stage indicators
    - Real-time progress and logging
    - Configuration panel with advanced options
    - Summary preview
    - Integration with actual workflow engine

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

    Header {
        background: #0f172a;
        color: #38bdf8;
    }

    Header > .header--title {
        text-style: bold;
        color: #38bdf8;
    }

    #main-container {
        height: 1fr;
    }

    #left-panel {
        width: 28%;
        background: #0f172a;
        border: solid #1e3a5f;
        margin: 0 0 0 1;
    }

    #center-panel {
        width: 44%;
        background: #0f172a;
        border: solid #1e3a5f;
        margin: 0 1;
    }

    #right-panel {
        width: 28%;
        background: #0f172a;
        border: solid #1e3a5f;
        margin: 0 1 0 0;
    }

    .panel-header {
        text-style: bold;
        color: #818cf8;
        padding: 1;
        background: #1e293b;
        text-align: center;
        border-bottom: solid #334155;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: #1e293b;
        color: #94a3b8;
        padding: 0 2;
    }

    #stage-log {
        height: 1fr;
        background: #0c1322;
        border: solid #1e3a5f;
        margin: 1;
        padding: 1;
        scrollbar-color: #38bdf8;
    }

    Footer {
        background: #0f172a;
    }

    TabbedContent {
        height: 1fr;
    }

    TabbedContent > ContentSwitcher {
        height: 1fr;
    }

    TabPane {
        padding: 0;
    }

    Tabs {
        background: #1e293b;
    }

    Tab {
        background: #0f172a;
        color: #64748b;
        padding: 0 2;
    }

    Tab:hover {
        background: #1e293b;
        color: #94a3b8;
    }

    Tab.-active {
        background: #0f172a;
        color: #38bdf8;
        text-style: bold;
    }

    #preview-pane {
        padding: 1;
    }

    #preview-pane Markdown {
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "run_workflow", "Run"),
        Binding("c", "focus_config", "Config"),
        Binding("escape", "cancel_workflow", "Cancel"),
        Binding("f5", "refresh_explorer", "Refresh"),
    ]

    TITLE = "SUMMEETS"
    SUB_TITLE = "Video Transcription & Summarization"

    # Reactive state
    selected_file: reactive[Path | None] = reactive(None)
    is_processing: reactive[bool] = reactive(False)
    current_stage: reactive[str] = reactive("")
    workflow_start_time: float = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-container"):
            # LEFT PANEL - File Browser
            with Vertical(id="left-panel"):
                yield Static("◆ FILE EXPLORER", classes="panel-header")
                yield FileExplorer(".", id="file-explorer")
                yield FileInfo(id="file-info")

            # CENTER PANEL - Pipeline & Logs
            with Vertical(id="center-panel"):
                yield PipelineStatus(id="pipeline")
                yield ProgressPanel(id="progress-panel")
                yield Static("◆ ACTIVITY LOG", classes="panel-header")
                yield RichLog(id="stage-log", highlight=True, markup=True, wrap=True)

            # RIGHT PANEL - Config & Preview
            with Vertical(id="right-panel"):
                with TabbedContent():
                    with TabPane("Config", id="config-tab"):
                        yield ConfigPanel(id="config")
                    with TabPane("Preview", id="preview-tab"):
                        with ScrollableContainer(id="preview-pane"):
                            yield Markdown("*No summary available yet*", id="preview-md")
                    with TabPane("Full Log", id="log-tab"):
                        yield RichLog(id="full-log", highlight=True, markup=True)

        yield Static("● Ready | No file selected", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize on app start."""
        self._log("✦ Summeets TUI initialized", "bold cyan")
        self._log("Select a file and press [R] to run workflow", "dim")
        self._log("Supported formats: Video (cyan) | Audio (green) | Transcript (yellow)", "dim")

    # ─────────────────────────────────────────────────────────────────────────
    # Event Handlers
    # ─────────────────────────────────────────────────────────────────────────

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection in explorer."""
        self.selected_file = event.path
        self.query_one("#file-info", FileInfo).selected_path = event.path
        file_type = FileExplorer.get_file_type(event.path)
        self._update_status()
        self._log(f"Selected: [cyan]{event.path.name}[/] ({file_type})")

    @on(Button.Pressed, "#btn-run")
    def on_run_pressed(self) -> None:
        """Handle Run button click."""
        self.action_run_workflow()

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel_pressed(self) -> None:
        """Handle Cancel button click."""
        self.action_cancel_workflow()

    def on_stage_update(self, msg: StageUpdate) -> None:
        """Handle stage status updates from worker."""
        pipeline = self.query_one("#pipeline", PipelineStatus)
        pipeline.update_stage(msg.stage_id, msg.status, msg.elapsed)
        self.current_stage = msg.stage_id

    def on_log_message(self, msg: LogMessage) -> None:
        """Handle log messages from worker."""
        self._log(msg.text, msg.style)

    def on_overall_progress(self, msg: OverallProgress) -> None:
        """Handle progress updates from worker."""
        panel = self.query_one("#progress-panel", ProgressPanel)
        panel.progress_value = msg.progress
        if msg.label:
            panel.stage_label = msg.label

    def on_workflow_complete(self, msg: WorkflowComplete) -> None:
        """Handle workflow completion."""
        self.is_processing = False
        self._toggle_buttons(False)

        duration = time.time() - self.workflow_start_time
        duration_str = f"{duration:.1f}s"

        # Update all stages to complete
        pipeline = self.query_one("#pipeline", PipelineStatus)
        for stage in ["extract_audio", "process_audio", "transcribe", "summarize"]:
            pipeline.update_stage(stage, "complete")

        # Update progress
        panel = self.query_one("#progress-panel", ProgressPanel)
        panel.progress_value = 100
        panel.stage_label = f"Complete! ({duration_str})"

        self._log(f"✓ Workflow completed in {duration_str}!", "bold green")

        # Load summary preview if available
        if "summarize" in msg.results:
            summary_file = msg.results["summarize"].get("summary_file")
            if summary_file:
                self._load_summary_preview(Path(summary_file))
                # Switch to preview tab
                tabs = self.query_one(TabbedContent)
                tabs.active = "preview-tab"

        self._update_status()

    def on_workflow_error(self, msg: WorkflowError) -> None:
        """Handle workflow errors."""
        self.is_processing = False
        self._toggle_buttons(False)

        # Mark current stage as error
        if msg.stage:
            pipeline = self.query_one("#pipeline", PipelineStatus)
            pipeline.update_stage(msg.stage, "error")

        panel = self.query_one("#progress-panel", ProgressPanel)
        panel.stage_label = f"Error: {msg.error[:50]}..."

        self._log(f"✗ Error in {msg.stage}: {msg.error}", "bold red")
        if msg.traceback:
            self._log(f"Traceback: {msg.traceback[:200]}...", "dim red")

        self._update_status()

    def on_workflow_cancelled(self, msg: WorkflowCancelled) -> None:
        """Handle workflow cancellation."""
        self.is_processing = False
        self._toggle_buttons(False)
        self._log(f"⚠ Workflow cancelled at stage: {msg.stage}", "yellow")
        self._update_status()

    # ─────────────────────────────────────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────────────────────────────────────

    def action_run_workflow(self) -> None:
        """Start workflow execution."""
        if self.is_processing:
            self._log("⚠ Workflow already in progress", "yellow")
            return

        if self.selected_file is None:
            self._log("⚠ Please select a file first", "yellow")
            return

        self.is_processing = True
        self.workflow_start_time = time.time()
        self._toggle_buttons(True)

        # Reset pipeline status
        pipeline = self.query_one("#pipeline", PipelineStatus)
        pipeline.reset()

        # Reset progress
        panel = self.query_one("#progress-panel", ProgressPanel)
        panel.progress_value = 0
        panel.stage_label = "Starting..."

        # Clear logs
        self.query_one("#stage-log", RichLog).clear()

        file_type = FileExplorer.get_file_type(self.selected_file)
        self._log("━" * 40, "dim")
        self._log(f"▶ Starting workflow for: {self.selected_file.name}", "bold cyan")
        self._log(f"  Type: {file_type} | Provider: {self._get_provider()}", "dim")

        # Start background worker
        self.execute_workflow()

    def action_cancel_workflow(self) -> None:
        """Cancel running workflow."""
        if not self.is_processing:
            return

        for w in self.workers:
            w.cancel()

        self.post_message(WorkflowCancelled(self.current_stage))

    def action_focus_config(self) -> None:
        """Focus on config panel."""
        try:
            from textual.widgets import Select
            self.query_one("#provider", Select).focus()
        except Exception:
            pass

    def action_refresh_explorer(self) -> None:
        """Refresh the file explorer."""
        try:
            explorer = self.query_one("#file-explorer", FileExplorer)
            explorer.reload()
            self._log("File explorer refreshed", "dim")
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # Background Worker
    # ─────────────────────────────────────────────────────────────────────────

    @work(thread=True, exclusive=True)
    def execute_workflow(self) -> None:
        """Execute workflow in background thread using actual workflow engine."""
        worker = get_current_worker()

        if self.selected_file is None:
            return

        try:
            # Import workflow components
            from src.workflow import WorkflowConfig, execute_workflow
            from src.utils.validation import detect_file_type

            config_values = self.query_one("#config", ConfigPanel).get_config()
            file_type = detect_file_type(self.selected_file)

            self.post_message(LogMessage(f"Detected file type: {file_type}", "dim"))

            # Build workflow config
            config = WorkflowConfig(
                input_file=self.selected_file,
                output_dir=Path("data/output"),
                extract_audio=(file_type == "video"),
                process_audio=(file_type in ["video", "audio"]),
                transcribe=(file_type in ["video", "audio"]),
                summarize=True,
                audio_format="m4a",
                audio_quality="high",
                normalize_audio=config_values["normalize"],
                increase_volume=config_values["increase_volume"],
                summary_template=config_values["template"],
                provider=config_values["provider"],
                model=config_values["model"],
                auto_detect_template=config_values["auto_detect"],
            )

            stage_start_times = {}

            def progress_callback(step: int, total: int, step_name: str, status: str) -> None:
                """Thread-safe progress callback."""
                if worker.is_cancelled:
                    return

                # Track stage timing
                if step_name not in stage_start_times:
                    stage_start_times[step_name] = time.time()
                    self.post_message(StageUpdate(step_name, "active"))
                    self.post_message(LogMessage(f"▸ {status}", "cyan"))
                else:
                    # Calculate elapsed
                    elapsed = time.time() - stage_start_times[step_name]
                    elapsed_str = f"{elapsed:.1f}s"
                    self.post_message(StageUpdate(step_name, "active", elapsed_str))

                # Update overall progress
                progress = (step / total) * 100
                self.post_message(OverallProgress(progress, f"{step_name}: {status}"))

            # Execute the actual workflow
            results = execute_workflow(config, progress_callback)

            if not worker.is_cancelled:
                self.post_message(WorkflowComplete(results))

        except Exception as e:
            if not worker.is_cancelled:
                import traceback
                tb = traceback.format_exc()
                self.post_message(WorkflowError(str(e), self.current_stage, tb))

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _log(self, text: str, style: str = "") -> None:
        """Log message to both stage log and full log."""
        ts = datetime.now().strftime("%H:%M:%S")
        msg = Text()
        msg.append(f"[{ts}] ", style="dim")
        if "[" in text and "/" in text:
            msg.append_text(Text.from_markup(text))
        else:
            msg.append(text, style=style)

        try:
            self.query_one("#stage-log", RichLog).write(msg)
            self.query_one("#full-log", RichLog).write(msg)
        except Exception:
            pass

    def _toggle_buttons(self, processing: bool) -> None:
        """Toggle button states during processing."""
        try:
            self.query_one("#config", ConfigPanel).set_processing(processing)
        except Exception:
            pass

    def _get_provider(self) -> str:
        """Get current provider/model string."""
        try:
            config = self.query_one("#config", ConfigPanel).get_config()
            return f"{config['provider']}/{config['model']}"
        except Exception:
            return "openai/gpt-4o-mini"

    def _update_status(self) -> None:
        """Update status bar with current state."""
        try:
            bar = self.query_one("#status-bar", Static)
            parts = []

            if self.is_processing:
                parts.append("[#38bdf8]● Processing[/]")
            else:
                parts.append("[#22c55e]● Ready[/]")

            if self.selected_file:
                file_type = FileExplorer.get_file_type(self.selected_file)
                parts.append(f"[white]{self.selected_file.name}[/] ({file_type})")
            else:
                parts.append("[dim]No file selected[/]")

            parts.append(f"[dim]{self._get_provider()}[/]")

            bar.update(Text.from_markup(" │ ".join(parts)))
        except Exception:
            pass

    def _load_summary_preview(self, summary_path: Path) -> None:
        """Load summary into preview pane."""
        try:
            if summary_path.exists():
                content = summary_path.read_text(encoding="utf-8")
                self.query_one("#preview-md", Markdown).update(content)
                self._log(f"Summary loaded: {summary_path.name}", "green")
        except Exception as e:
            self._log(f"Failed to load summary: {e}", "red")


# =============================================================================
# ENTRY POINT
# =============================================================================

def run() -> None:
    """Launch the Summeets TUI."""
    app = SummeetsApp()
    app.run()


if __name__ == "__main__":
    run()
