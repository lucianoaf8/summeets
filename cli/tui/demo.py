"""
Summeets TUI Demo - Visual Design Showcase

This demo displays the full TUI layout with simulated workflow execution.
Run with: python demo.py

Features demonstrated:
- Futuristic dark theme with cyan/violet accents
- 3-panel layout (File Browser | Pipeline | Config/Preview)
- Animated pipeline stage transitions
- Real-time progress updates (no flickering)
- File type color coding
- Responsive status bar
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Iterable

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
# CUSTOM MESSAGES
# =============================================================================

class StageUpdate(Message):
    """Update a pipeline stage status."""
    def __init__(self, stage_id: str, status: str, progress: float = 0) -> None:
        self.stage_id = stage_id
        self.status = status
        self.progress = progress
        super().__init__()


class LogMessage(Message):
    """Add a log entry."""
    def __init__(self, text: str, style: str = "") -> None:
        self.text = text
        self.style = style
        super().__init__()


class OverallProgress(Message):
    """Update overall progress."""
    def __init__(self, progress: float, label: str = "") -> None:
        self.progress = progress
        self.label = label
        super().__init__()


class WorkflowDone(Message):
    """Workflow completed."""
    def __init__(self, success: bool = True) -> None:
        self.success = success
        super().__init__()


# =============================================================================
# STAGE INDICATOR WIDGET
# =============================================================================

class StageIndicator(Static):
    """
    Pipeline stage indicator with animated status transitions.
    Uses CSS classes for state - prevents flickering.
    """

    DEFAULT_CSS = """
    StageIndicator {
        width: auto;
        min-width: 16;
        height: 5;
        padding: 1;
        border: solid #374151;
        background: #111827;
        content-align: center middle;
    }

    StageIndicator.stage--pending {
        opacity: 0.4;
        border: dashed #374151;
    }

    StageIndicator.stage--active {
        border: heavy #38bdf8;
        background: #1e3a5f;
    }

    StageIndicator.stage--active .stage-icon {
        color: #38bdf8;
        text-style: bold blink;
    }

    StageIndicator.stage--complete {
        border: solid #22c55e;
        background: #14532d40;
    }

    StageIndicator.stage--complete .stage-icon {
        color: #22c55e;
    }

    StageIndicator.stage--error {
        border: solid #ef4444;
        background: #7f1d1d40;
    }

    StageIndicator.stage--error .stage-icon {
        color: #ef4444;
    }

    StageIndicator .stage-name {
        text-style: bold;
        color: #e2e8f0;
        text-align: center;
        width: 100%;
    }

    StageIndicator .stage-icon {
        color: #64748b;
        text-align: center;
        width: 100%;
    }

    StageIndicator .stage-time {
        color: #64748b;
        text-align: center;
        width: 100%;
        text-style: italic;
    }
    """

    status: reactive[str] = reactive("pending")
    elapsed: reactive[str] = reactive("")

    def __init__(self, name: str, icon: str = "○", **kwargs) -> None:
        super().__init__(**kwargs)
        self.stage_name = name
        self.icon = icon
        self.add_class("stage--pending")

    def compose(self) -> ComposeResult:
        yield Static(self.stage_name, classes="stage-name")
        yield Static(self._get_status_display(), classes="stage-icon", id="icon")
        yield Static("", classes="stage-time", id="time")

    def _get_status_display(self) -> str:
        icons = {
            "pending": "○  ─ ─",
            "active": "◉  ▶▶▶",
            "complete": "●  ✓ ✓",
            "error": "◉  ✗ ✗",
        }
        return icons.get(self.status, "○  ─ ─")

    def watch_status(self, old: str, new: str) -> None:
        self.remove_class(f"stage--{old}")
        self.add_class(f"stage--{new}")
        # Only update if widget is mounted (compose has run)
        try:
            icon = self.query_one("#icon", Static)
            icon.update(self._get_status_display())
        except Exception:
            pass  # Widget not yet composed

    def watch_elapsed(self, elapsed: str) -> None:
        try:
            self.query_one("#time", Static).update(elapsed)
        except Exception:
            pass  # Widget not yet composed


# =============================================================================
# PIPELINE STATUS CONTAINER
# =============================================================================

class PipelineStatus(Container):
    """Visual pipeline with stage flow indicators."""

    DEFAULT_CSS = """
    PipelineStatus {
        height: auto;
        padding: 1 2;
        background: #0c1322;
        border: solid #1e3a5f;
        margin: 1;
    }

    PipelineStatus .pipeline-title {
        text-style: bold;
        color: #38bdf8;
        text-align: center;
        width: 100%;
        padding-bottom: 1;
    }

    PipelineStatus .pipeline-flow {
        height: auto;
        align: center middle;
    }

    PipelineStatus .connector {
        color: #374151;
        padding: 0 1;
        height: 5;
        content-align: center middle;
    }

    PipelineStatus .connector-active {
        color: #38bdf8;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("━━━  PROCESSING PIPELINE  ━━━", classes="pipeline-title")
        with Horizontal(classes="pipeline-flow"):
            yield StageIndicator("Extract", "🎬", id="stage-extract")
            yield Static("━━▶", classes="connector", id="conn-1")
            yield StageIndicator("Process", "🔊", id="stage-process")
            yield Static("━━▶", classes="connector", id="conn-2")
            yield StageIndicator("Transcribe", "📝", id="stage-transcribe")
            yield Static("━━▶", classes="connector", id="conn-3")
            yield StageIndicator("Summarize", "📋", id="stage-summarize")

    def update_stage(self, stage_id: str, status: str, elapsed: str = "") -> None:
        stage_map = {
            "extract": "#stage-extract",
            "process": "#stage-process",
            "transcribe": "#stage-transcribe",
            "summarize": "#stage-summarize",
        }
        if stage_id in stage_map:
            indicator = self.query_one(stage_map[stage_id], StageIndicator)
            indicator.status = status
            if elapsed:
                indicator.elapsed = elapsed

    def reset(self) -> None:
        for indicator in self.query(StageIndicator):
            indicator.status = "pending"
            indicator.elapsed = ""


# =============================================================================
# FILE EXPLORER
# =============================================================================

class FileExplorer(DirectoryTree):
    """Color-coded file browser for supported formats."""

    VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}
    AUDIO_EXT = {".m4a", ".flac", ".wav", ".mp3", ".ogg"}
    TRANSCRIPT_EXT = {".json", ".txt", ".srt"}

    DEFAULT_CSS = """
    FileExplorer {
        height: 1fr;
        scrollbar-color: #38bdf8;
        scrollbar-background: #1e293b;
        background: #0f172a;
    }
    """

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        supported = self.VIDEO_EXT | self.AUDIO_EXT | self.TRANSCRIPT_EXT
        return [p for p in paths if p.is_dir() or p.suffix.lower() in supported]

    def render_label(self, node, base_style, style) -> Text:
        label = super().render_label(node, base_style, style)
        if node.data and hasattr(node.data, 'path') and node.data.path.is_file():
            ext = node.data.path.suffix.lower()
            if ext in self.VIDEO_EXT:
                label.stylize("bold #38bdf8")  # Cyan for video
            elif ext in self.AUDIO_EXT:
                label.stylize("bold #22c55e")  # Green for audio
            elif ext in self.TRANSCRIPT_EXT:
                label.stylize("bold #fbbf24")  # Yellow for transcript
        return label


# =============================================================================
# FILE INFO PANEL
# =============================================================================

class FileInfo(Static):
    """Display selected file metadata."""

    DEFAULT_CSS = """
    FileInfo {
        height: auto;
        min-height: 8;
        padding: 1;
        background: #1e293b;
        border: solid #334155;
        margin: 1;
    }

    FileInfo .info-title {
        text-style: bold;
        color: #818cf8;
        margin-bottom: 1;
    }

    FileInfo .info-row {
        height: auto;
    }

    FileInfo .info-label {
        color: #64748b;
        width: 10;
    }

    FileInfo .info-value {
        color: #e2e8f0;
    }
    """

    selected_path: reactive[Path | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Static("◆ FILE INFO", classes="info-title")
        yield Static("Select a file to view details", id="info-content")

    def watch_selected_path(self, path: Path | None) -> None:
        content = self.query_one("#info-content", Static)
        if path is None:
            content.update("Select a file to view details")
            return

        try:
            size = path.stat().st_size
            size_str = self._fmt_size(size)
            ext = path.suffix.lower()

            if ext in FileExplorer.VIDEO_EXT:
                type_str = f"[cyan]Video[/] ({ext[1:].upper()})"
                icon = "🎬"
            elif ext in FileExplorer.AUDIO_EXT:
                type_str = f"[green]Audio[/] ({ext[1:].upper()})"
                icon = "🔊"
            else:
                type_str = f"[yellow]Transcript[/] ({ext[1:].upper()})"
                icon = "📝"

            info = Text()
            info.append(f"{icon} {path.name}\n\n", style="bold white")
            info.append("Size:     ", style="#64748b")
            info.append(f"{size_str}\n", style="white")
            info.append("Type:     ", style="#64748b")
            info.append_text(Text.from_markup(type_str))
            info.append("\n")
            info.append("Path:     ", style="#64748b")
            info.append(f"{path.parent}", style="#94a3b8")

            content.update(info)
        except Exception as e:
            content.update(f"[red]Error:[/] {e}")

    def _fmt_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# =============================================================================
# CONFIG PANEL
# =============================================================================

class ConfigPanel(Container):
    """Configuration controls with collapsible advanced options."""

    DEFAULT_CSS = """
    ConfigPanel {
        height: auto;
        padding: 1;
    }

    ConfigPanel .section-title {
        text-style: bold;
        color: #818cf8;
        margin-bottom: 1;
    }

    ConfigPanel Label {
        color: #94a3b8;
        margin-top: 1;
    }

    ConfigPanel Select {
        margin-bottom: 1;
    }

    ConfigPanel Input {
        margin-bottom: 1;
    }

    ConfigPanel Button {
        width: 100%;
        margin-top: 1;
    }

    ConfigPanel .btn-run {
        background: #38bdf8;
        color: #0a0e1a;
        text-style: bold;
    }

    ConfigPanel .btn-run:hover {
        background: #818cf8;
    }

    ConfigPanel .btn-cancel {
        background: #374151;
        color: #94a3b8;
    }

    ConfigPanel .btn-cancel:hover {
        background: #ef4444;
        color: white;
    }

    ConfigPanel Collapsible {
        margin-top: 1;
        background: #0f172a;
        border: solid #334155;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("◆ CONFIGURATION", classes="section-title")

        yield Label("LLM Provider")
        yield Select(
            options=[("OpenAI", "openai"), ("Anthropic", "anthropic")],
            value="openai",
            id="provider"
        )

        yield Label("Model")
        yield Input(value="gpt-4o-mini", id="model")

        yield Label("Template")
        yield Select(
            options=[
                ("Default", "default"),
                ("SOP", "sop"),
                ("Decision Log", "decision"),
                ("Brainstorm", "brainstorm"),
                ("Requirements", "requirements"),
            ],
            value="default",
            id="template"
        )

        yield Checkbox("Auto-detect template", value=True, id="auto-detect")

        with Collapsible(title="Advanced Options", collapsed=True):
            yield Label("Chunk Size (seconds)")
            yield Input(value="1800", id="chunk-size")

            yield Label("CoD Passes")
            yield Input(value="2", id="cod-passes")

            yield Label("Max Output Tokens")
            yield Input(value="3000", id="max-tokens")

            yield Rule()

            yield Checkbox("Normalize audio", value=True, id="normalize")
            yield Checkbox("High quality extraction", value=True, id="hq")

        yield Button("▶  Run Workflow", id="btn-run", classes="btn-run")
        yield Button("■  Cancel", id="btn-cancel", classes="btn-cancel", disabled=True)


# =============================================================================
# PROGRESS PANEL
# =============================================================================

class ProgressPanel(Container):
    """Current stage progress and ETA display."""

    DEFAULT_CSS = """
    ProgressPanel {
        height: auto;
        padding: 1;
        margin: 1;
        background: #1e293b;
        border: solid #334155;
    }

    ProgressPanel .progress-title {
        text-style: bold;
        color: #38bdf8;
        margin-bottom: 1;
    }

    ProgressPanel .progress-stage {
        color: #e2e8f0;
        margin-bottom: 1;
    }

    ProgressPanel ProgressBar {
        padding: 1 0;
    }

    ProgressPanel ProgressBar > .bar--bar {
        color: #38bdf8;
    }

    ProgressPanel ProgressBar > .bar--complete {
        color: #22c55e;
    }

    ProgressPanel .progress-eta {
        color: #64748b;
        text-align: right;
    }
    """

    stage_label: reactive[str] = reactive("Ready")
    progress_value: reactive[float] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Static("◆ CURRENT PROGRESS", classes="progress-title")
        yield Static("Ready to process", classes="progress-stage", id="stage-text")
        yield ProgressBar(total=100, show_eta=True, id="progress-bar")
        yield Static("", classes="progress-eta", id="eta-text")

    def watch_stage_label(self, label: str) -> None:
        self.query_one("#stage-text", Static).update(label)

    def watch_progress_value(self, value: float) -> None:
        self.query_one("#progress-bar", ProgressBar).update(progress=value)


# =============================================================================
# MAIN APPLICATION
# =============================================================================

class SummeetsDemo(App):
    """
    Summeets TUI Demo - Showcases the visual design and layout.

    Demonstrates:
    - Futuristic dark theme
    - Anti-flicker reactive updates
    - Three-panel responsive layout
    - Simulated workflow execution
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

    #status-bar .status-ready {
        color: #22c55e;
    }

    #status-bar .status-processing {
        color: #38bdf8;
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
        Binding("r", "run_demo", "Run Demo"),
        Binding("escape", "cancel", "Cancel"),
        Binding("d", "toggle_dark", "Theme"),
    ]

    TITLE = "SUMMEETS"
    SUB_TITLE = "Video Transcription & Summarization"

    selected_file: reactive[Path | None] = reactive(None)
    is_processing: reactive[bool] = reactive(False)

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
                            yield Markdown(SAMPLE_SUMMARY, id="preview-md")
                    with TabPane("Full Log", id="log-tab"):
                        yield RichLog(id="full-log", highlight=True, markup=True)

        yield Static("● Ready | No file selected", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._log("✦ Summeets TUI initialized", "bold cyan")
        self._log("Select a file and press [R] to run demo workflow", "dim")

    # ─────────────────────────────────────────────────────────────────────────
    # Event Handlers
    # ─────────────────────────────────────────────────────────────────────────

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.selected_file = event.path
        self.query_one("#file-info", FileInfo).selected_path = event.path
        self._update_status()
        self._log(f"Selected: [cyan]{event.path.name}[/]")

    @on(Button.Pressed, "#btn-run")
    def on_run_pressed(self) -> None:
        self.action_run_demo()

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel_pressed(self) -> None:
        self.action_cancel()

    def on_stage_update(self, msg: StageUpdate) -> None:
        pipeline = self.query_one("#pipeline", PipelineStatus)
        pipeline.update_stage(msg.stage_id, msg.status)

    def on_log_message(self, msg: LogMessage) -> None:
        self._log(msg.text, msg.style)

    def on_overall_progress(self, msg: OverallProgress) -> None:
        panel = self.query_one("#progress-panel", ProgressPanel)
        panel.progress_value = msg.progress
        if msg.label:
            panel.stage_label = msg.label

    def on_workflow_done(self, msg: WorkflowDone) -> None:
        self.is_processing = False
        self._toggle_buttons(False)

        if msg.success:
            self._log("✓ Workflow completed successfully!", "bold green")
            # Switch to preview tab
            tabs = self.query_one(TabbedContent)
            tabs.active = "preview-tab"
        else:
            self._log("✗ Workflow failed", "bold red")

        self._update_status()

    # ─────────────────────────────────────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────────────────────────────────────

    def action_run_demo(self) -> None:
        if self.is_processing:
            return

        self.is_processing = True
        self._toggle_buttons(True)

        # Reset pipeline
        self.query_one("#pipeline", PipelineStatus).reset()
        panel = self.query_one("#progress-panel", ProgressPanel)
        panel.progress_value = 0
        panel.stage_label = "Starting..."

        self._log("━" * 40, "dim")
        self._log("▶ Starting demo workflow simulation", "bold cyan")

        # Start simulation
        self.simulate_workflow()

    def action_cancel(self) -> None:
        for w in self.workers:
            w.cancel()
        self.is_processing = False
        self._toggle_buttons(False)
        self._log("⚠ Workflow cancelled", "yellow")
        self._update_status()

    # ─────────────────────────────────────────────────────────────────────────
    # Background Worker - Simulated Workflow
    # ─────────────────────────────────────────────────────────────────────────

    @work(thread=True, exclusive=True)
    async def simulate_workflow(self) -> None:
        """Simulate the 4-stage workflow with progress updates."""
        import time

        worker = get_current_worker()
        stages = [
            ("extract", "Extracting audio from video", 3),
            ("process", "Processing & normalizing audio", 2),
            ("transcribe", "Transcribing with speaker diarization", 5),
            ("summarize", "Generating summary with CoD", 4),
        ]

        total_steps = sum(s[2] for s in stages)
        current_step = 0

        for stage_id, description, duration in stages:
            if worker.is_cancelled:
                return

            # Start stage
            self.post_message(StageUpdate(stage_id, "active"))
            self.post_message(LogMessage(f"▸ {description}...", "cyan"))

            # Simulate progress
            for i in range(duration * 10):
                if worker.is_cancelled:
                    return

                progress = (current_step + (i / (duration * 10))) / total_steps * 100
                self.post_message(OverallProgress(progress, f"{description} ({i * 10 // duration}%)"))

                if i % 10 == 5:
                    self.post_message(LogMessage(f"  Processing segment {i + 1}...", "dim"))

                time.sleep(0.1)

            # Complete stage
            current_step += 1
            self.post_message(StageUpdate(stage_id, "complete", f"{duration}s"))
            self.post_message(LogMessage(f"  ✓ Completed in {duration}s", "green"))

        # Done
        self.post_message(OverallProgress(100, "Complete!"))
        self.post_message(WorkflowDone(True))

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _log(self, text: str, style: str = "") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        msg = Text()
        msg.append(f"[{ts}] ", style="dim")
        msg.append_text(Text.from_markup(text) if "[" in text else Text(text, style=style))

        self.query_one("#stage-log", RichLog).write(msg)
        self.query_one("#full-log", RichLog).write(msg)

    def _toggle_buttons(self, processing: bool) -> None:
        self.query_one("#btn-run", Button).disabled = processing
        self.query_one("#btn-cancel", Button).disabled = not processing

    def _update_status(self) -> None:
        bar = self.query_one("#status-bar", Static)
        parts = []

        if self.is_processing:
            parts.append("[#38bdf8]● Processing[/]")
        else:
            parts.append("[#22c55e]● Ready[/]")

        if self.selected_file:
            parts.append(f"[white]{self.selected_file.name}[/]")
        else:
            parts.append("[dim]No file selected[/]")

        parts.append("[dim]OpenAI/gpt-4o-mini[/]")

        bar.update(Text.from_markup(" │ ".join(parts)))


# =============================================================================
# SAMPLE DATA
# =============================================================================

SAMPLE_SUMMARY = """
# Meeting Summary

## Overview
This 45-minute team standup covered Q1 progress, upcoming milestones,
and resource allocation for the new product launch.

---

## Key Discussion Points

### 1. Q1 Progress Review
- **Revenue**: 15% above target ($1.2M vs $1.04M projected)
- **User Growth**: 23% MoM, exceeding 50K active users
- **Churn**: Reduced to 2.1% (down from 3.8%)

### 2. Product Launch Timeline
| Milestone | Date | Owner |
|-----------|------|-------|
| Beta Release | Jan 15 | @sarah |
| Marketing Push | Jan 22 | @marketing |
| GA Launch | Feb 1 | @product |

### 3. Technical Blockers
- API rate limiting needs resolution before launch
- Database migration scheduled for weekend maintenance

---

## Action Items
- [ ] **@john**: Finalize API scaling plan by Friday
- [ ] **@sarah**: Complete beta testing checklist
- [ ] **@team**: Review launch documentation

---

## Decisions Made
1. ✅ Approved $50K additional cloud budget
2. ✅ Delayed feature X to Q2 (deprioritized)
3. ✅ Hired contractor for security audit

---

*Generated by Summeets • Processing time: 14.3s*
"""


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    app = SummeetsDemo()
    app.run()
