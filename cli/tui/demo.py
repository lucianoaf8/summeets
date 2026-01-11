"""
Summeets TUI Demo - Visual Design Showcase

This demo displays the full TUI layout with simulated workflow execution.
Run with: python -m cli.tui.demo

Features demonstrated:
- Futuristic dark theme with cyan/violet accents
- 2-panel layout (Config/Logs | Execution/Pipeline)
- Flow type selection (Video/Audio/Transcript)
- Animated pipeline stage transitions
- Real-time progress updates (no flickering)
- Simulated file selection and workflow
"""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

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
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    ProgressBar,
    RichLog,
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
    def __init__(self, stage_id: str, status: str, elapsed: str = "") -> None:
        self.stage_id = stage_id
        self.status = status
        self.elapsed = elapsed
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
    """Pipeline stage indicator with animated status transitions."""

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

    StageIndicator.stage--complete {
        border: solid #22c55e;
        background: #14532d40;
    }

    StageIndicator.stage--error {
        border: solid #ef4444;
        background: #7f1d1d40;
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

    def __init__(self, name: str, icon: str = "O", **kwargs) -> None:
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
            "pending": "o  - -",
            "active": "O  >>>",
            "complete": "*  OK!",
            "error": "X  ERR",
        }
        return icons.get(self.status, "o  - -")

    def watch_status(self, old: str, new: str) -> None:
        self.remove_class(f"stage--{old}")
        self.add_class(f"stage--{new}")
        try:
            self.query_one("#icon", Static).update(self._get_status_display())
        except Exception:
            pass

    def watch_elapsed(self, elapsed: str) -> None:
        try:
            self.query_one("#time", Static).update(elapsed)
        except Exception:
            pass


# =============================================================================
# PIPELINE STATUS
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
    """

    def compose(self) -> ComposeResult:
        yield Static("--- PROCESSING PIPELINE ---", classes="pipeline-title")
        with Horizontal(classes="pipeline-flow"):
            yield StageIndicator("Extract", id="stage-extract")
            yield Static("==>", classes="connector")
            yield StageIndicator("Process", id="stage-process")
            yield Static("==>", classes="connector")
            yield StageIndicator("Transcribe", id="stage-transcribe")
            yield Static("==>", classes="connector")
            yield StageIndicator("Summarize", id="stage-summarize")

    def update_stage(self, stage_id: str, status: str, elapsed: str = "") -> None:
        stage_map = {
            "extract": "#stage-extract",
            "process": "#stage-process",
            "transcribe": "#stage-transcribe",
            "summarize": "#stage-summarize",
        }
        if stage_id in stage_map:
            try:
                indicator = self.query_one(stage_map[stage_id], StageIndicator)
                indicator.status = status
                if elapsed:
                    indicator.elapsed = elapsed
            except Exception:
                pass

    def reset(self) -> None:
        for indicator in self.query(StageIndicator):
            indicator.status = "pending"
            indicator.elapsed = ""


# =============================================================================
# PROGRESS PANEL
# =============================================================================

class ProgressPanel(Container):
    """Current stage progress display."""

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
    progress_value: reactive[float] = reactive(0.0)

    def compose(self) -> ComposeResult:
        yield Static("* CURRENT PROGRESS", classes="progress-title")
        yield Static("Ready to process", classes="progress-stage", id="stage-text")
        yield ProgressBar(total=100, show_eta=False, id="progress-bar")
        yield Static("0%", classes="progress-eta", id="eta-text")

    def on_mount(self) -> None:
        try:
            self.query_one("#progress-bar", ProgressBar).update(progress=0)
        except Exception:
            pass

    def watch_stage_label(self, label: str) -> None:
        try:
            self.query_one("#stage-text", Static).update(label)
        except Exception:
            pass

    def watch_progress_value(self, value: float) -> None:
        try:
            self.query_one("#progress-bar", ProgressBar).update(progress=value)
            self.query_one("#eta-text", Static).update(f"{value:.0f}%")
        except Exception:
            pass

    def reset(self) -> None:
        self.progress_value = 0.0
        self.stage_label = "Ready to process"


# =============================================================================
# EXECUTION PANEL (Demo version)
# =============================================================================

class DemoExecutionPanel(Container):
    """Demo execution panel matching production layout."""

    DEFAULT_CSS = """
    DemoExecutionPanel {
        height: auto;
        padding: 1;
    }

    DemoExecutionPanel .section-title {
        text-style: bold;
        color: #38bdf8;
        margin-bottom: 1;
        text-align: center;
    }

    DemoExecutionPanel .flow-group {
        height: auto;
        padding: 1;
        background: #1e293b;
        border: solid #334155;
        margin-bottom: 1;
    }

    DemoExecutionPanel .flow-label {
        color: #94a3b8;
        margin-bottom: 1;
    }

    DemoExecutionPanel .flow-buttons {
        height: auto;
    }

    DemoExecutionPanel .flow-btn {
        width: 1fr;
        margin: 0 1 0 0;
    }

    DemoExecutionPanel .flow-btn.-active {
        background: #38bdf8;
        color: #0a0e1a;
        text-style: bold;
    }

    DemoExecutionPanel .file-group {
        height: auto;
        padding: 1;
        background: #1e293b;
        border: solid #334155;
        margin-bottom: 1;
    }

    DemoExecutionPanel .file-row {
        height: auto;
    }

    DemoExecutionPanel #demo-file-path {
        width: 1fr;
    }

    DemoExecutionPanel #btn-demo-browse {
        width: auto;
        min-width: 10;
        margin-left: 1;
        background: #374151;
    }

    DemoExecutionPanel .file-info {
        color: #64748b;
        height: auto;
        margin-top: 1;
    }

    DemoExecutionPanel .template-group {
        height: auto;
        padding: 1;
        background: #1e293b;
        border: solid #334155;
        margin-bottom: 1;
    }

    DemoExecutionPanel .template-group Checkbox {
        margin: 0;
        padding: 0;
        height: auto;
    }

    DemoExecutionPanel .config-group {
        height: auto;
        padding: 1;
        background: #1e293b;
        border: solid #334155;
        margin-bottom: 1;
    }

    DemoExecutionPanel Label {
        color: #94a3b8;
        margin-top: 1;
    }

    DemoExecutionPanel .action-group {
        height: auto;
        padding: 1;
    }

    DemoExecutionPanel #btn-run-demo {
        width: 100%;
        background: #38bdf8;
        color: #0a0e1a;
        text-style: bold;
    }

    DemoExecutionPanel #btn-run-demo:hover {
        background: #818cf8;
    }

    DemoExecutionPanel #btn-run-demo.btn-cancel-mode {
        background: #ef4444;
    }
    """

    selected_flow: reactive[str] = reactive("video")

    def compose(self) -> ComposeResult:
        yield Static("* WORKFLOW EXECUTION", classes="section-title")

        # Flow Type Selection
        with Vertical(classes="flow-group"):
            yield Static("Select Input Type:", classes="flow-label")
            with Horizontal(classes="flow-buttons"):
                yield Button("[V] Video", id="flow-video", classes="flow-btn -active")
                yield Button("[A] Audio", id="flow-audio", classes="flow-btn")
                yield Button("[T] Transcript", id="flow-transcript", classes="flow-btn")

        # File Selection (Demo)
        with Vertical(classes="file-group"):
            yield Static("Select File:", classes="flow-label")
            with Horizontal(classes="file-row"):
                yield Input(placeholder="Click Browse to select file...", id="demo-file-path")
                yield Button("[Browse]", id="btn-demo-browse")
            yield Static("No file selected", classes="file-info", id="demo-file-info")

        # Template Options
        with Vertical(classes="template-group"):
            yield Static("Templates:", classes="flow-label")
            yield Checkbox("Auto-detect template", value=True, id="demo-tpl-auto")
            yield Checkbox("Default", value=False, id="demo-tpl-default")
            yield Checkbox("SOP", value=False, id="demo-tpl-sop")
            yield Checkbox("Decision Log", value=False, id="demo-tpl-decision")

        # Config Settings
        with Vertical(classes="config-group"):
            yield Static("Settings:", classes="flow-label")

            yield Label("LLM Provider")
            yield Select(
                options=[("OpenAI", "openai"), ("Anthropic", "anthropic")],
                value="openai",
                id="demo-provider"
            )

            yield Label("Model")
            yield Input(value="gpt-4o-mini", id="demo-model")

            with Collapsible(title="Advanced Options", collapsed=True):
                yield Label("Chunk Size (seconds)")
                yield Input(value="1800", id="demo-chunk-size")
                yield Checkbox("Normalize audio", value=True, id="demo-normalize")

        # Action Button
        with Vertical(classes="action-group"):
            yield Button("[>] Run Workflow", id="btn-run-demo")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id and btn_id.startswith("flow-"):
            flow_type = btn_id.replace("flow-", "")
            self._set_active_flow(flow_type)

    def _set_active_flow(self, flow_type: str) -> None:
        self.selected_flow = flow_type
        for btn_id in ["flow-video", "flow-audio", "flow-transcript"]:
            try:
                btn = self.query_one(f"#{btn_id}", Button)
                if btn_id == f"flow-{flow_type}":
                    btn.add_class("-active")
                else:
                    btn.remove_class("-active")
            except Exception:
                pass

    def set_demo_file(self, name: str, size: str, file_type: str) -> None:
        """Set demo file display."""
        try:
            self.query_one("#demo-file-path", Input).value = f"data/input/{name}"
            self.query_one("#demo-file-info", Static).update(
                f"[OK] {name} ({size}, {file_type.upper()})"
            )
        except Exception:
            pass

    def set_processing(self, is_processing: bool) -> None:
        try:
            btn = self.query_one("#btn-run-demo", Button)
            if is_processing:
                btn.label = "[X] Cancel"
                btn.add_class("btn-cancel-mode")
            else:
                btn.label = "[>] Run Workflow"
                btn.remove_class("btn-cancel-mode")
        except Exception:
            pass


# =============================================================================
# CONFIG PANEL (Demo - API Keys only)
# =============================================================================

class DemoConfigPanel(Container):
    """Demo config panel for API keys and settings."""

    DEFAULT_CSS = """
    DemoConfigPanel {
        height: auto;
        padding: 1;
    }

    DemoConfigPanel .section-title {
        text-style: bold;
        color: #818cf8;
        margin-bottom: 1;
    }

    DemoConfigPanel Label {
        color: #fbbf24;
        margin-top: 1;
    }

    DemoConfigPanel Input {
        margin-bottom: 1;
    }

    DemoConfigPanel Button {
        width: 100%;
        margin-top: 1;
        background: #22c55e;
        color: #0a0e1a;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("* CONFIGURATION", classes="section-title")

        with Collapsible(title="API Keys", collapsed=False):
            yield Label("OpenAI API Key")
            yield Input(value="sk-****...****demo", id="demo-openai-key")

            yield Label("Anthropic API Key")
            yield Input(value="sk-ant-****...****demo", id="demo-anthropic-key")

            yield Label("Replicate Token")
            yield Input(value="r8_****...****demo", id="demo-replicate-token")

        yield Button("[Save] Save Config", id="btn-demo-save")


# =============================================================================
# MAIN DEMO APPLICATION
# =============================================================================

class SummeetsDemo(App):
    """
    Summeets TUI Demo - Showcases the new two-panel layout.

    Layout:
    - Left Panel: Config/Logs (Full Log default)
    - Right Panel: Execution panel + Pipeline
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

    #main-container {
        height: 1fr;
    }

    #left-panel {
        width: 45%;
        background: #0f172a;
        border: solid #1e3a5f;
        margin: 0 0 0 1;
    }

    #right-panel {
        width: 55%;
        background: #0f172a;
        border: solid #1e3a5f;
        margin: 0 1 0 0;
        overflow-y: auto;
    }

    #exec-scroll {
        height: auto;
        scrollbar-color: #38bdf8;
    }

    #pipeline-area {
        height: auto;
        padding: 0;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: #1e293b;
        color: #94a3b8;
        padding: 0 2;
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

    Tab.-active {
        background: #0f172a;
        color: #38bdf8;
        text-style: bold;
    }

    #log-tab-container {
        height: 1fr;
    }

    #log-header {
        height: auto;
        background: #1e293b;
        padding: 0 1;
    }

    #btn-copy-log {
        dock: right;
        width: auto;
        min-width: 10;
        background: #374151;
    }

    #config-scroll {
        height: 1fr;
        scrollbar-color: #38bdf8;
    }

    #preview-pane {
        padding: 1;
    }

    Checkbox > .toggle--button {
        color: #64748b;
    }

    Checkbox.-on > .toggle--button {
        color: #38bdf8;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "run_demo", "Run Demo"),
        Binding("escape", "cancel", "Cancel"),
    ]

    TITLE = "SUMMEETS DEMO"
    SUB_TITLE = "Video Transcription & Summarization"

    is_processing: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-container"):
            # LEFT PANEL - Config & Logs (Full Log default)
            with Vertical(id="left-panel"):
                with TabbedContent(initial="log-tab"):
                    with TabPane("Full Log", id="log-tab"):
                        with Vertical(id="log-tab-container"):
                            with Horizontal(id="log-header"):
                                yield Static("* FULL LOG")
                                yield Button("[Copy]", id="btn-copy-log")
                            yield RichLog(id="full-log", highlight=True, markup=True)
                    with TabPane("Activity", id="activity-tab"):
                        yield RichLog(id="stage-log", highlight=True, markup=True, wrap=True)
                    with TabPane("Config", id="config-tab"):
                        with ScrollableContainer(id="config-scroll"):
                            yield DemoConfigPanel(id="demo-config")
                    with TabPane("Preview", id="preview-tab"):
                        with ScrollableContainer(id="preview-pane"):
                            yield Markdown(SAMPLE_SUMMARY, id="preview-md")

            # RIGHT PANEL - Execution + Pipeline
            with Vertical(id="right-panel"):
                with ScrollableContainer(id="exec-scroll"):
                    yield DemoExecutionPanel(id="demo-execution")
                    with Vertical(id="pipeline-area"):
                        yield PipelineStatus(id="pipeline")
                        yield ProgressPanel(id="progress-panel")

        yield Static("[*] Ready | DEMO MODE | Press [R] to run simulation", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._log("[*] Summeets TUI Demo initialized", "bold cyan")
        self._log("This is a DEMO with simulated workflow", "dim")
        self._log("Press [R] or click Run Workflow to start", "dim")

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    @on(Button.Pressed, "#btn-run-demo")
    def on_run_pressed(self) -> None:
        if self.is_processing:
            self.action_cancel()
        else:
            self.action_run_demo()

    @on(Button.Pressed, "#btn-demo-browse")
    def on_browse_pressed(self) -> None:
        # Simulate file selection
        exec_panel = self.query_one("#demo-execution", DemoExecutionPanel)
        flow = exec_panel.selected_flow

        demo_files = {
            "video": ("meeting_2024-01-15.mp4", "245 MB", "mp4"),
            "audio": ("interview_recording.m4a", "48 MB", "m4a"),
            "transcript": ("transcript_final.json", "128 KB", "json"),
        }

        name, size, ext = demo_files.get(flow, demo_files["video"])
        exec_panel.set_demo_file(name, size, ext)
        self._log(f"Selected: [cyan]{name}[/]")
        self._update_status(f"{name} ({flow})")

    @on(Button.Pressed, "#btn-copy-log")
    def on_copy_log(self) -> None:
        self._log("[OK] Log copied to clipboard (demo)", "green")

    @on(Button.Pressed, "#btn-demo-save")
    def on_save_config(self) -> None:
        self._log("[OK] Config saved (demo)", "green")

    def on_stage_update(self, msg: StageUpdate) -> None:
        pipeline = self.query_one("#pipeline", PipelineStatus)
        pipeline.update_stage(msg.stage_id, msg.status, msg.elapsed)

    def on_log_message(self, msg: LogMessage) -> None:
        self._log(msg.text, msg.style)

    def on_overall_progress(self, msg: OverallProgress) -> None:
        panel = self.query_one("#progress-panel", ProgressPanel)
        panel.progress_value = msg.progress
        if msg.label:
            panel.stage_label = msg.label

    def on_workflow_done(self, msg: WorkflowDone) -> None:
        self.is_processing = False
        self.query_one("#demo-execution", DemoExecutionPanel).set_processing(False)

        if msg.success:
            self._log("[OK] Workflow completed successfully!", "bold green")
            tabs = self.query_one(TabbedContent)
            tabs.active = "preview-tab"
        else:
            self._log("[X] Workflow failed", "bold red")

        self._update_status("Complete!")

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_run_demo(self) -> None:
        if self.is_processing:
            return

        self.is_processing = True
        self.query_one("#demo-execution", DemoExecutionPanel).set_processing(True)

        # Reset pipeline
        self.query_one("#pipeline", PipelineStatus).reset()
        panel = self.query_one("#progress-panel", ProgressPanel)
        panel.reset()
        panel.stage_label = "Starting..."

        exec_panel = self.query_one("#demo-execution", DemoExecutionPanel)
        flow = exec_panel.selected_flow

        self._log("-" * 40, "dim")
        self._log(f"[>] Starting demo workflow ({flow} flow)", "bold cyan")

        self.simulate_workflow()

    def action_cancel(self) -> None:
        for w in self.workers:
            w.cancel()
        self.is_processing = False
        self.query_one("#demo-execution", DemoExecutionPanel).set_processing(False)
        self._log("[!] Workflow cancelled", "yellow")
        self._update_status("Cancelled")

    # -------------------------------------------------------------------------
    # Background Worker - Simulated Workflow
    # -------------------------------------------------------------------------

    @work(thread=True, exclusive=True)
    def simulate_workflow(self) -> None:
        """Simulate the 4-stage workflow with progress updates."""
        worker = get_current_worker()

        stages = [
            ("extract", "Extracting audio from video", 2),
            ("process", "Processing & normalizing audio", 1.5),
            ("transcribe", "Transcribing with speaker diarization", 3),
            ("summarize", "Generating summary with CoD", 2.5),
        ]

        total_duration = sum(s[2] for s in stages)
        elapsed_total = 0

        for stage_id, description, duration in stages:
            if worker.is_cancelled:
                return

            self.post_message(StageUpdate(stage_id, "active"))
            self.post_message(LogMessage(f"[>] {description}...", "cyan"))

            steps = int(duration * 10)
            for i in range(steps):
                if worker.is_cancelled:
                    return

                progress = ((elapsed_total + (i / 10)) / total_duration) * 100
                self.post_message(OverallProgress(progress, f"{description}"))

                if i % 10 == 5:
                    self.post_message(LogMessage(f"  Processing chunk {i + 1}...", "dim"))

                time.sleep(0.1)

            elapsed_total += duration
            self.post_message(StageUpdate(stage_id, "complete", f"{duration}s"))
            self.post_message(LogMessage(f"  [OK] Completed in {duration}s", "green"))

        self.post_message(OverallProgress(100, "Complete!"))
        self.post_message(WorkflowDone(True))

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _log(self, text: str, style: str = "") -> None:
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

    def _update_status(self, info: str = "") -> None:
        try:
            bar = self.query_one("#status-bar", Static)
            status = "[*] Processing" if self.is_processing else "[*] Ready"
            parts = [status, "DEMO MODE"]
            if info:
                parts.append(info)
            bar.update(" | ".join(parts))
        except Exception:
            pass


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
1. Approved $50K additional cloud budget
2. Delayed feature X to Q2 (deprioritized)
3. Hired contractor for security audit

---

*Generated by Summeets Demo*
"""


# =============================================================================
# ENTRY POINT
# =============================================================================

def run() -> None:
    """Launch the demo."""
    app = SummeetsDemo()
    app.run()


if __name__ == "__main__":
    run()
