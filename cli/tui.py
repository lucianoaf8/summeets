"""Textual-based TUI for running Summeets workflows."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    ProgressBar,
    Select,
    Static,
    RichLog,
)

from src.workflow import WorkflowConfig, execute_workflow
from src.utils.exceptions import ValidationError, SummeetsError


class ProgressMessage(Message):
    """Message used to communicate progress updates from background tasks."""

    def __init__(self, step: int, total: int, step_name: str, status: str) -> None:
        self.step = step
        self.total = total
        self.step_name = step_name
        self.status = status
        super().__init__()


class WorkflowTUI(App):
    """Interactive Textual TUI for running Summeets workflows."""

    CSS = """
    Screen {
        background: #0f172a;
        color: #e2e8f0;
    }

    #layout {
        height: 1fr;
    }

    #form {
        width: 1fr;
        background: #111827;
        padding: 2;
        border: solid #1f2937;
    }

    #log-panel {
        width: 1fr;
        background: #0b1220;
        padding: 1;
        border: solid #1f2937;
    }

    .label {
        color: #94a3b8;
        text-style: bold;
    }

    Input, Select, Checkbox {
        margin-bottom: 1;
    }

    Button {
        margin-top: 1;
        width: 100%;
    }

    #status {
        margin-top: 1;
        color: #38bdf8;
    }
    """

    BINDINGS = [("q", "quit", "Quit"), ("r", "run_workflow", "Run Workflow")]

    progress = reactive(0)
    total_steps = reactive(1)
    status_text = reactive("Waiting to start")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="layout"):
            with Horizontal():
                with Vertical(id="form"):
                    yield Static("Summeets Workflow", classes="label")
                    yield Input(placeholder="Video/Audio/Transcript path", id="input-path")
                    yield Input(placeholder="Output directory (default: out)", id="output-dir")
                    yield Select(
                        options=[("OpenAI", "openai"), ("Anthropic", "anthropic")],
                        value="openai",
                        id="provider",
                    )
                    yield Input(placeholder="Model (e.g., gpt-4o-mini)", value="gpt-4o-mini", id="model")
                    yield Select(
                        options=[
                            ("Default", "default"),
                            ("SOP", "sop"),
                            ("Decision", "decision"),
                            ("Brainstorm", "brainstorm"),
                            ("Requirements", "requirements"),
                        ],
                        value="default",
                        id="template",
                    )
                    yield Checkbox(label="Auto-detect template", value=True, id="auto-detect")
                    yield Button("Run Workflow", id="run-btn", variant="primary")
                    yield Static("", id="status")
                    yield ProgressBar(id="progress")
                with Vertical(id="log-panel"):
                    yield Static("Live Log", classes="label")
                    yield RichLog(id="log", highlight=True, markup=True, wrap=True)
        yield Footer()

    def _append_log(self, text: str, style: str = "cyan") -> None:
        log = self.query_one("#log", RichLog)
        log.write(Text(text, style=style))

    def _set_progress(self, step: int, total: int, status: str) -> None:
        self.progress = step
        self.total_steps = max(total, 1)
        self.status_text = status
        progress_bar = self.query_one(ProgressBar)
        progress_bar.total = self.total_steps
        progress_bar.progress = self.progress
        status_widget = self.query_one("#status", Static)
        status_widget.update(Text(status, style="bright_cyan"))

    def on_mount(self) -> None:
        self._set_progress(0, 1, "Waiting to start")

    def validate_inputs(self) -> WorkflowConfig:
        path = self.query_one("#input-path", Input).value.strip()
        output_dir_raw = self.query_one("#output-dir", Input).value.strip() or "out"
        provider = self.query_one("#provider", Select).value or "openai"
        model = self.query_one("#model", Input).value.strip() or "gpt-4o-mini"
        template = self.query_one("#template", Select).value or "default"
        auto_detect = self.query_one("#auto-detect", Checkbox).value

        if not path:
            raise ValidationError("Input path is required")

        config = WorkflowConfig(
            input_file=Path(path),
            output_dir=Path(output_dir_raw),
            extract_audio=True,
            process_audio=True,
            transcribe=True,
            summarize=True,
            audio_format="m4a",
            audio_quality="high",
            normalize_audio=True,
            output_formats=["m4a"],
            summary_template=template,
            provider=provider,
            model=model,
            auto_detect_template=auto_detect,
        )
        return config

    async def action_run_workflow(self) -> None:
        """Keyboard binding to run workflow."""
        await self._start_workflow()

    @on(Button.Pressed, "#run-btn")
    async def handle_run_click(self) -> None:
        await self._start_workflow()

    async def _start_workflow(self) -> None:
        try:
            config = self.validate_inputs()
        except (ValidationError, ValueError) as e:
            self._append_log(f"[red]Validation error: {e}[/red]", style="red")
            return

        self._append_log("Starting workflow...", style="green")
        self._set_progress(0, 4, "Initializing")

        async def runner() -> None:
            try:
                def progress_callback(step: int, total: int, step_name: str, status: str) -> None:
                    self.call_from_thread(self.post_message, ProgressMessage(step, total, step_name, status))

                result = await asyncio.to_thread(execute_workflow, config, progress_callback)
                self.call_from_thread(self._append_log, f"[green]Done[/green] {result}", "green")
            except (SummeetsError, ValidationError) as e:
                self.call_from_thread(self._append_log, f"[red]Workflow failed: {e}[/red]", "red")
            except Exception as exc:  # noqa: BLE001
                self.call_from_thread(self._append_log, f"[red]Unexpected error: {exc}[/red]", "red")
            finally:
                self.call_from_thread(self._set_progress, self.total_steps, self.total_steps, "Complete")

        await self.background_worker(runner)

    async def background_worker(self, coro) -> None:
        """Run a coroutine safely in the background."""
        await self.call_later(asyncio.create_task, coro())

    def on_progress_message(self, message: ProgressMessage) -> None:
        self._set_progress(message.step, message.total, f"{message.step_name}: {message.status}")
        self._append_log(f"[bright_black]{message.step}/{message.total}[/bright_black] {message.status}", style="cyan")


def run() -> None:
    """Launch the Textual TUI."""
    WorkflowTUI().run()
