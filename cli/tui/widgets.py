"""
Custom Textual widgets for the Summeets TUI.

All widgets use reactive attributes and CSS class toggling
to prevent flickering and ensure smooth updates.
"""

import os
from pathlib import Path
from typing import Iterable, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Checkbox,
    Collapsible,
    DirectoryTree,
    Input,
    Label,
    ProgressBar,
    Rule,
    Select,
    Static,
)

from .constants import (
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
    TRANSCRIPT_EXTENSIONS,
    ALL_SUPPORTED_EXTENSIONS,
    STATUS_ICONS,
    COLOR_VIDEO,
    COLOR_AUDIO,
    COLOR_TRANSCRIPT,
    load_env_file,
    mask_api_key,
    MASK_VISIBLE_CHARS,
)


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
        return STATUS_ICONS.get(self.status, STATUS_ICONS["pending"])

    def watch_status(self, old: str, new: str) -> None:
        self.remove_class(f"stage--{old}")
        self.add_class(f"stage--{new}")
        try:
            self.query_one("#icon", Static).update(self._get_status_display())
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
        """Update a specific stage's status."""
        stage_map = {
            "extract": "#stage-extract",
            "extract_audio": "#stage-extract",
            "process": "#stage-process",
            "process_audio": "#stage-process",
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
        """Reset all stages to pending state."""
        for indicator in self.query(StageIndicator):
            indicator.status = "pending"
            indicator.elapsed = ""


# =============================================================================
# FILE EXPLORER (Limited to data/ and docs/)
# =============================================================================

class FilteredDirectoryTree(DirectoryTree):
    """DirectoryTree filtered to show only supported media formats."""

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Filter to show only supported file types."""
        return [p for p in paths if p.is_dir() or p.suffix.lower() in ALL_SUPPORTED_EXTENSIONS]

    def render_label(self, node, base_style, style) -> Text:
        """Color-code files by type."""
        label = super().render_label(node, base_style, style)
        if node.data and hasattr(node.data, 'path') and node.data.path.is_file():
            ext = node.data.path.suffix.lower()
            if ext in VIDEO_EXTENSIONS:
                label.stylize(f"bold {COLOR_VIDEO}")
            elif ext in AUDIO_EXTENSIONS:
                label.stylize(f"bold {COLOR_AUDIO}")
            elif ext in TRANSCRIPT_EXTENSIONS:
                label.stylize(f"bold {COLOR_TRANSCRIPT}")
        return label


class FileExplorer(Container):
    """
    File explorer limited to data/ and docs/ directories only.
    Shows two directory trees side by side or stacked.
    """

    DEFAULT_CSS = """
    FileExplorer {
        height: 1fr;
        background: #0f172a;
    }

    FileExplorer .folder-section {
        height: 1fr;
        padding: 0;
    }

    FileExplorer .folder-label {
        color: #818cf8;
        text-style: bold;
        padding: 0 1;
        background: #1e293b;
    }

    FileExplorer FilteredDirectoryTree {
        height: 1fr;
        scrollbar-color: #38bdf8;
        scrollbar-background: #1e293b;
        background: #0f172a;
    }
    """

    def __init__(self, base_path: str = ".", **kwargs) -> None:
        super().__init__(**kwargs)
        self.base_path = Path(base_path).resolve()

    def compose(self) -> ComposeResult:
        # Data folder
        data_path = self.base_path / "data"
        if not data_path.exists():
            data_path.mkdir(parents=True, exist_ok=True)

        with Vertical(classes="folder-section"):
            yield Static("📁 data/", classes="folder-label")
            yield FilteredDirectoryTree(str(data_path), id="tree-data")

        # Docs folder
        docs_path = self.base_path / "docs"
        if not docs_path.exists():
            docs_path.mkdir(parents=True, exist_ok=True)

        with Vertical(classes="folder-section"):
            yield Static("📁 docs/", classes="folder-label")
            yield FilteredDirectoryTree(str(docs_path), id="tree-docs")

    def reload(self) -> None:
        """Reload both directory trees."""
        try:
            self.query_one("#tree-data", FilteredDirectoryTree).reload()
            self.query_one("#tree-docs", FilteredDirectoryTree).reload()
        except Exception:
            pass

    @classmethod
    def get_file_type(cls, path: Path) -> str:
        """Determine file type from extension."""
        ext = path.suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            return "video"
        elif ext in AUDIO_EXTENSIONS:
            return "audio"
        elif ext in TRANSCRIPT_EXTENSIONS:
            return "transcript"
        return "unknown"


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
    """

    selected_path: reactive[Path | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Static("◆ FILE INFO", classes="info-title")
        yield Static("Select a file to view details", id="info-content")

    def watch_selected_path(self, path: Path | None) -> None:
        """Update display when file selection changes."""
        try:
            content = self.query_one("#info-content", Static)
        except Exception:
            return

        if path is None:
            content.update("Select a file to view details")
            return

        try:
            size = path.stat().st_size
            size_str = self._fmt_size(size)
            file_type = FileExplorer.get_file_type(path)
            ext = path.suffix.lower()

            type_colors = {
                "video": ("cyan", "🎬"),
                "audio": ("green", "🔊"),
                "transcript": ("yellow", "📝"),
            }
            color, icon = type_colors.get(file_type, ("white", "📄"))

            info = Text()
            info.append(f"{icon} {path.name}\n\n", style="bold white")
            info.append("Size:     ", style="#64748b")
            info.append(f"{size_str}\n", style="white")
            info.append("Type:     ", style="#64748b")
            info.append(f"{file_type.title()} ({ext[1:].upper()})\n", style=color)
            info.append("Path:     ", style="#64748b")
            info.append(f"{path.parent}", style="#94a3b8")

            content.update(info)
        except Exception as e:
            content.update(f"[red]Error:[/] {e}")

    def _fmt_size(self, size: int) -> str:
        """Format file size for display."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


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
    progress_value: reactive[float] = reactive(0.0)

    def compose(self) -> ComposeResult:
        yield Static("◆ CURRENT PROGRESS", classes="progress-title")
        yield Static("Ready to process", classes="progress-stage", id="stage-text")
        # Initialize with progress=0 explicitly
        yield ProgressBar(total=100, show_eta=False, id="progress-bar")
        yield Static("0%", classes="progress-eta", id="eta-text")

    def on_mount(self) -> None:
        """Ensure progress bar starts at 0% on mount."""
        try:
            self.query_one("#progress-bar", ProgressBar).update(progress=0)
            self.query_one("#eta-text", Static).update("0%")
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
        """Reset progress to initial state."""
        self.progress_value = 0.0
        self.stage_label = "Ready to process"
        try:
            self.query_one("#progress-bar", ProgressBar).update(progress=0)
            self.query_one("#eta-text", Static).update("0%")
        except Exception:
            pass


# =============================================================================
# CONFIG PANEL (Unified with Env settings)
# =============================================================================

class ConfigPanel(Container):
    """
    Unified configuration panel with:
    - LLM provider/model settings
    - Template checkbox group with auto-detect logic
    - API keys (masked)
    - Advanced options
    - Save functionality
    """

    TEMPLATE_OPTIONS = [
        ("auto-detect", "Auto-detect template"),
        ("default", "Default"),
        ("sop", "SOP"),
        ("decision", "Decision Log"),
        ("brainstorm", "Brainstorm"),
        ("requirements", "Requirements"),
    ]

    SENSITIVE_KEYS = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "REPLICATE_API_TOKEN"}

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

    ConfigPanel .subsection-title {
        text-style: bold;
        color: #fbbf24;
        margin-top: 1;
        margin-bottom: 0;
    }

    ConfigPanel Label {
        color: #94a3b8;
        margin-top: 1;
    }

    ConfigPanel .key-label {
        color: #fbbf24;
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

    ConfigPanel .btn-save {
        background: #22c55e;
        color: #0a0e1a;
        text-style: bold;
    }

    ConfigPanel .btn-save:hover {
        background: #16a34a;
    }

    ConfigPanel Collapsible {
        margin-top: 1;
        background: #0f172a;
        border: solid #334155;
        padding: 0 1;
    }

    ConfigPanel .template-group {
        padding: 0 1;
        margin-top: 1;
    }

    ConfigPanel .template-group {
        height: auto;
        padding: 0;
        margin: 0 0 1 0;
    }

    ConfigPanel .template-group Checkbox {
        margin: 0;
        padding: 0;
        height: auto;
    }

    ConfigPanel .template-group Checkbox.disabled-template {
        opacity: 0.4;
    }

    /* Hide checkbox indicator when unchecked */
    Checkbox > .toggle--button {
        color: #64748b;
    }

    Checkbox.-on > .toggle--button {
        color: #38bdf8;
    }

    /* Run/Cancel toggle button */
    ConfigPanel .btn-run.btn-cancel-mode {
        background: #ef4444;
    }

    ConfigPanel .btn-run.btn-cancel-mode:hover {
        background: #dc2626;
    }

    ConfigPanel .env-status {
        color: #64748b;
        text-style: italic;
    }

    ConfigPanel .env-status.env-saved {
        color: #22c55e;
    }
    """

    def __init__(self, env_path: Optional[Path] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.env_path = env_path or Path(".env")
        self._env_values: dict[str, str] = load_env_file(self.env_path)

    def compose(self) -> ComposeResult:
        yield Static("◆ CONFIGURATION", classes="section-title")

        # LLM Settings
        yield Label("LLM Provider")
        provider_value = self._env_values.get("LLM_PROVIDER", "openai")
        if provider_value not in ("openai", "anthropic"):
            provider_value = "openai"
        yield Select(
            options=[("OpenAI", "openai"), ("Anthropic", "anthropic")],
            value=provider_value,
            id="provider"
        )

        yield Label("Model")
        yield Input(
            value=self._env_values.get("LLM_MODEL", "gpt-4o-mini"),
            id="model"
        )

        # Template Checkbox Group
        yield Static("Templates", classes="subsection-title")
        with Vertical(classes="template-group"):
            yield Checkbox("Auto-detect template", value=True, id="tpl-auto-detect")
            yield Checkbox("Default", value=False, id="tpl-default", classes="disabled-template")
            yield Checkbox("SOP", value=False, id="tpl-sop", classes="disabled-template")
            yield Checkbox("Decision Log", value=False, id="tpl-decision", classes="disabled-template")
            yield Checkbox("Brainstorm", value=False, id="tpl-brainstorm", classes="disabled-template")
            yield Checkbox("Requirements", value=False, id="tpl-requirements", classes="disabled-template")

        # API Keys (collapsed)
        with Collapsible(title="API Keys", collapsed=True):
            yield Label("OpenAI API Key", classes="key-label")
            yield MaskedInput(
                value=self._env_values.get("OPENAI_API_KEY", ""),
                placeholder="sk-...",
                id="env-openai-key"
            )

            yield Label("Anthropic API Key", classes="key-label")
            yield MaskedInput(
                value=self._env_values.get("ANTHROPIC_API_KEY", ""),
                placeholder="sk-ant-...",
                id="env-anthropic-key"
            )

            yield Label("Replicate API Token", classes="key-label")
            yield MaskedInput(
                value=self._env_values.get("REPLICATE_API_TOKEN", ""),
                placeholder="r8_...",
                id="env-replicate-token"
            )

        # Advanced Options
        with Collapsible(title="Advanced Options", collapsed=True):
            yield Label("Chunk Size (seconds)")
            yield Input(
                value=self._env_values.get("SUMMARY_CHUNK_SECONDS", "1800"),
                id="chunk-size"
            )

            yield Label("CoD Passes")
            yield Input(
                value=self._env_values.get("SUMMARY_COD_PASSES", "2"),
                id="cod-passes"
            )

            yield Label("Max Output Tokens")
            yield Input(
                value=self._env_values.get("SUMMARY_MAX_OUTPUT_TOKENS", "3000"),
                id="max-tokens"
            )

            yield Checkbox("Normalize audio", value=True, id="normalize")
            yield Checkbox("Increase volume", value=False, id="increase-volume")

        yield Static("", classes="env-status", id="env-status")
        yield Button("💾  Save Config", id="btn-save-env", classes="btn-save")
        yield Button("▶  Run Workflow", id="btn-run", classes="btn-run")

    def on_mount(self) -> None:
        """Initialize template checkbox states."""
        self._update_template_states()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle template checkbox changes."""
        if event.checkbox.id == "tpl-auto-detect":
            self._update_template_states()

    def _update_template_states(self) -> None:
        """Update template checkbox enabled/disabled states."""
        try:
            auto_detect = self.query_one("#tpl-auto-detect", Checkbox)
            is_auto = auto_detect.value

            template_ids = ["tpl-default", "tpl-sop", "tpl-decision", "tpl-brainstorm", "tpl-requirements"]

            for tpl_id in template_ids:
                try:
                    cb = self.query_one(f"#{tpl_id}", Checkbox)
                    cb.disabled = is_auto
                    if is_auto:
                        cb.value = False
                        cb.add_class("disabled-template")
                    else:
                        cb.remove_class("disabled-template")
                except Exception:
                    pass
        except Exception:
            pass

    def get_config(self) -> dict:
        """Extract current configuration values."""
        try:
            # Get selected templates
            auto_detect = self.query_one("#tpl-auto-detect", Checkbox).value
            selected_templates = []

            if not auto_detect:
                template_map = {
                    "tpl-default": "default",
                    "tpl-sop": "sop",
                    "tpl-decision": "decision",
                    "tpl-brainstorm": "brainstorm",
                    "tpl-requirements": "requirements",
                }
                for tpl_id, tpl_name in template_map.items():
                    try:
                        if self.query_one(f"#{tpl_id}", Checkbox).value:
                            selected_templates.append(tpl_name)
                    except Exception:
                        pass

            templates = selected_templates if selected_templates else ["default"]
            return {
                "provider": self.query_one("#provider", Select).value or "openai",
                "model": self.query_one("#model", Input).value or "gpt-4o-mini",
                "templates": templates,
                "template": templates[0] if templates else "default",  # Backward compat
                "auto_detect": auto_detect,
                "chunk_seconds": int(self.query_one("#chunk-size", Input).value or 1800),
                "cod_passes": int(self.query_one("#cod-passes", Input).value or 2),
                "max_tokens": int(self.query_one("#max-tokens", Input).value or 3000),
                "normalize": self.query_one("#normalize", Checkbox).value,
                "increase_volume": self.query_one("#increase-volume", Checkbox).value,
            }
        except Exception:
            return {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "templates": ["default"],
                "template": "default",
                "auto_detect": True,
                "chunk_seconds": 1800,
                "cod_passes": 2,
                "max_tokens": 3000,
                "normalize": True,
                "increase_volume": False,
            }

    def save_env(self) -> tuple[bool, str]:
        """Save current values to .env file."""
        try:
            # Get values from form
            provider = self.query_one("#provider", Select).value or "openai"
            model = self.query_one("#model", Input).value or "gpt-4o-mini"
            max_tokens = self.query_one("#max-tokens", Input).value or "3000"
            chunk_seconds = self.query_one("#chunk-size", Input).value or "1800"
            cod_passes = self.query_one("#cod-passes", Input).value or "2"

            openai_key = self.query_one("#env-openai-key", MaskedInput).get_real_value()
            anthropic_key = self.query_one("#env-anthropic-key", MaskedInput).get_real_value()
            replicate_token = self.query_one("#env-replicate-token", MaskedInput).get_real_value()

            # Build .env content
            lines = [
                "# Summeets Configuration",
                "# Generated by Summeets TUI",
                "",
                "# LLM Provider",
                f"LLM_PROVIDER={provider}",
                f"LLM_MODEL={model}",
                "",
                "# API Keys",
            ]

            if openai_key:
                lines.append(f"OPENAI_API_KEY={openai_key}")
            if anthropic_key:
                lines.append(f"ANTHROPIC_API_KEY={anthropic_key}")
            if replicate_token:
                lines.append(f"REPLICATE_API_TOKEN={replicate_token}")

            lines.extend([
                "",
                "# Summarization Settings",
                f"SUMMARY_MAX_OUTPUT_TOKENS={max_tokens}",
                f"SUMMARY_CHUNK_SECONDS={chunk_seconds}",
                f"SUMMARY_COD_PASSES={cod_passes}",
                "",
            ])

            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            # Update status
            try:
                status = self.query_one("#env-status", Static)
                status.update("✓ Config saved!")
                status.add_class("env-saved")
            except Exception:
                pass

            return True, "Configuration saved successfully"

        except Exception as e:
            return False, f"Failed to save: {e}"

    def set_processing(self, is_processing: bool) -> None:
        """Toggle Run button between Run/Cancel modes."""
        try:
            btn = self.query_one("#btn-run", Button)
            if is_processing:
                btn.label = "■  Cancel"
                btn.add_class("btn-cancel-mode")
            else:
                btn.label = "▶  Run Workflow"
                btn.remove_class("btn-cancel-mode")
        except Exception:
            pass


# =============================================================================
# ENV CONFIG PANEL (API Keys with masking)
# =============================================================================

class MaskedInput(Input):
    """Input field that masks sensitive values like API keys."""

    DEFAULT_CSS = """
    MaskedInput {
        margin-bottom: 1;
    }

    MaskedInput.masked {
        color: #64748b;
    }
    """

    is_masked: reactive[bool] = reactive(True)
    _real_value: str = ""

    def __init__(self, value: str = "", placeholder: str = "", **kwargs) -> None:
        self._real_value = value
        masked = mask_api_key(value) if value else ""
        super().__init__(value=masked, placeholder=placeholder, **kwargs)
        if value:
            self.add_class("masked")

    def on_focus(self) -> None:
        """Show real value when focused."""
        if self.is_masked and self._real_value:
            self.value = self._real_value
            self.is_masked = False
            self.remove_class("masked")

    def on_blur(self) -> None:
        """Mask value when unfocused."""
        if not self.is_masked:
            self._real_value = self.value
            self.value = mask_api_key(self._real_value) if self._real_value else ""
            self.is_masked = True
            if self._real_value:
                self.add_class("masked")

    def get_real_value(self) -> str:
        """Get the unmasked value."""
        if self.is_masked:
            return self._real_value
        return self.value

    def set_real_value(self, value: str) -> None:
        """Set the real value (will be masked if not focused)."""
        self._real_value = value
        if self.is_masked:
            self.value = mask_api_key(value) if value else ""
            if value:
                self.add_class("masked")
            else:
                self.remove_class("masked")
        else:
            self.value = value


class EnvConfigPanel(Container):
    """
    Panel for viewing and editing .env configuration.
    Masks sensitive values like API keys.
    """

    DEFAULT_CSS = """
    EnvConfigPanel {
        height: auto;
        padding: 1;
    }

    EnvConfigPanel .section-title {
        text-style: bold;
        color: #818cf8;
        margin-bottom: 1;
    }

    EnvConfigPanel .env-status {
        color: #64748b;
        text-style: italic;
        margin-bottom: 1;
    }

    EnvConfigPanel .env-status.env-missing {
        color: #ef4444;
    }

    EnvConfigPanel .env-status.env-loaded {
        color: #22c55e;
    }

    EnvConfigPanel Label {
        color: #94a3b8;
        margin-top: 1;
    }

    EnvConfigPanel .key-label {
        color: #fbbf24;
    }

    EnvConfigPanel Input {
        margin-bottom: 1;
    }

    EnvConfigPanel Button {
        width: 100%;
        margin-top: 1;
    }

    EnvConfigPanel .btn-save {
        background: #22c55e;
        color: #0a0e1a;
        text-style: bold;
    }

    EnvConfigPanel .btn-save:hover {
        background: #16a34a;
    }

    EnvConfigPanel Collapsible {
        margin-top: 1;
        background: #0f172a;
        border: solid #334155;
        padding: 0 1;
    }
    """

    # Keys that should be masked
    SENSITIVE_KEYS = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "REPLICATE_API_TOKEN"}

    def __init__(self, env_path: Optional[Path] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.env_path = env_path or Path(".env")
        self._env_values: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        yield Static("◆ ENVIRONMENT CONFIG", classes="section-title")

        # Status indicator
        if self.env_path.exists():
            yield Static("✓ .env file loaded", classes="env-status env-loaded", id="env-status")
        else:
            yield Static("⚠ .env file not found", classes="env-status env-missing", id="env-status")

        # Load existing values
        self._env_values = load_env_file(self.env_path)

        with Collapsible(title="API Keys", collapsed=False):
            yield Label("OpenAI API Key", classes="key-label")
            yield MaskedInput(
                value=self._env_values.get("OPENAI_API_KEY", ""),
                placeholder="sk-...",
                id="env-openai-key"
            )

            yield Label("Anthropic API Key", classes="key-label")
            yield MaskedInput(
                value=self._env_values.get("ANTHROPIC_API_KEY", ""),
                placeholder="sk-ant-...",
                id="env-anthropic-key"
            )

            yield Label("Replicate API Token", classes="key-label")
            yield MaskedInput(
                value=self._env_values.get("REPLICATE_API_TOKEN", ""),
                placeholder="r8_...",
                id="env-replicate-token"
            )

        with Collapsible(title="Default Settings", collapsed=True):
            yield Label("LLM Provider")
            yield Select(
                options=[("OpenAI", "openai"), ("Anthropic", "anthropic")],
                value=self._env_values.get("LLM_PROVIDER", "openai"),
                id="env-provider"
            )

            yield Label("LLM Model")
            yield Input(
                value=self._env_values.get("LLM_MODEL", "gpt-4o-mini"),
                id="env-model"
            )

            yield Label("Max Output Tokens")
            yield Input(
                value=self._env_values.get("SUMMARY_MAX_OUTPUT_TOKENS", "3000"),
                id="env-max-tokens"
            )

            yield Label("Chunk Seconds")
            yield Input(
                value=self._env_values.get("SUMMARY_CHUNK_SECONDS", "1800"),
                id="env-chunk-seconds"
            )

            yield Label("CoD Passes")
            yield Input(
                value=self._env_values.get("SUMMARY_COD_PASSES", "2"),
                id="env-cod-passes"
            )

        yield Button("💾  Save .env", id="btn-save-env", classes="btn-save")

    def get_env_values(self) -> dict[str, str]:
        """Get current env values from form."""
        values = {}

        # API Keys (masked inputs)
        try:
            values["OPENAI_API_KEY"] = self.query_one("#env-openai-key", MaskedInput).get_real_value()
            values["ANTHROPIC_API_KEY"] = self.query_one("#env-anthropic-key", MaskedInput).get_real_value()
            values["REPLICATE_API_TOKEN"] = self.query_one("#env-replicate-token", MaskedInput).get_real_value()

            # Settings
            values["LLM_PROVIDER"] = self.query_one("#env-provider", Select).value or "openai"
            values["LLM_MODEL"] = self.query_one("#env-model", Input).value or "gpt-4o-mini"
            values["SUMMARY_MAX_OUTPUT_TOKENS"] = self.query_one("#env-max-tokens", Input).value or "3000"
            values["SUMMARY_CHUNK_SECONDS"] = self.query_one("#env-chunk-seconds", Input).value or "1800"
            values["SUMMARY_COD_PASSES"] = self.query_one("#env-cod-passes", Input).value or "2"
        except Exception:
            pass

        # Filter out empty values
        return {k: v for k, v in values.items() if v}

    def save_env(self) -> tuple[bool, str]:
        """Save current values to .env file."""
        try:
            values = self.get_env_values()

            # Build .env content with comments
            lines = [
                "# Summeets Configuration",
                "# Generated by Summeets TUI",
                "",
                "# LLM Provider (openai or anthropic)",
                f"LLM_PROVIDER={values.get('LLM_PROVIDER', 'openai')}",
                f"LLM_MODEL={values.get('LLM_MODEL', 'gpt-4o-mini')}",
                "",
                "# API Keys",
            ]

            if values.get("OPENAI_API_KEY"):
                lines.append(f"OPENAI_API_KEY={values['OPENAI_API_KEY']}")
            if values.get("ANTHROPIC_API_KEY"):
                lines.append(f"ANTHROPIC_API_KEY={values['ANTHROPIC_API_KEY']}")
            if values.get("REPLICATE_API_TOKEN"):
                lines.append(f"REPLICATE_API_TOKEN={values['REPLICATE_API_TOKEN']}")

            lines.extend([
                "",
                "# Summarization Settings",
                f"SUMMARY_MAX_OUTPUT_TOKENS={values.get('SUMMARY_MAX_OUTPUT_TOKENS', '3000')}",
                f"SUMMARY_CHUNK_SECONDS={values.get('SUMMARY_CHUNK_SECONDS', '1800')}",
                f"SUMMARY_COD_PASSES={values.get('SUMMARY_COD_PASSES', '2')}",
                "",
            ])

            # Write to file
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            # Update status
            try:
                status = self.query_one("#env-status", Static)
                status.update("✓ .env file saved!")
                status.remove_class("env-missing")
                status.add_class("env-loaded")
            except Exception:
                pass

            return True, "Configuration saved successfully"

        except Exception as e:
            return False, f"Failed to save: {e}"
