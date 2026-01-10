# Summeets TUI Implementation Guide

A comprehensive guide to building the Summeets Terminal User Interface using Textual.

---

## Table of Contents

1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Anti-Flicker Strategies](#anti-flicker-strategies)
4. [Theme & Color System](#theme--color-system)
5. [Layout Architecture](#layout-architecture)
6. [Widget Components](#widget-components)
7. [Message System](#message-system)
8. [Background Workers](#background-workers)
9. [CSS Styling Reference](#css-styling-reference)
10. [Implementation Checklist](#implementation-checklist)

---

## Overview

The Summeets TUI is a modern, flicker-free terminal interface for video transcription and summarization. It features:

- **3-Panel Layout**: File Browser | Pipeline Status | Configuration
- **Futuristic Dark Theme**: Navy background with cyan/violet accents
- **Real-time Progress**: Animated pipeline stages with progress tracking
- **Non-blocking Execution**: Background workers for long-running tasks

### Design Goals

| Goal | Implementation |
|------|----------------|
| No Flickering | Reactive attributes, CSS class toggling, message-based updates |
| Modern Aesthetic | Dark theme, gradient accents, consistent typography |
| Responsive | Percentage-based panel widths, scrollable containers |
| Accessible | Keyboard shortcuts, clear visual hierarchy |

---

## Technology Stack

### Required Dependencies

```toml
[project.dependencies]
textual = ">=0.52.0"    # TUI framework (tested with 0.89.1)
rich = ">=13.0.0"       # Terminal rendering (bundled with Textual)
```

### Import Structure

```python
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button, Checkbox, Collapsible, DirectoryTree, Footer, Header,
    Input, Label, Markdown, ProgressBar, RichLog, Rule, Select,
    Static, TabbedContent, TabPane,
)
from textual.worker import get_current_worker
from rich.text import Text
```

### Why Textual?

| Feature | Benefit |
|---------|---------|
| Virtual DOM | Only changed regions are re-rendered |
| Reactive System | State changes automatically propagate to UI |
| CSS Styling | Familiar, powerful styling system |
| Workers API | Clean background task management |
| Message System | Thread-safe UI updates |
| Rich Integration | Beautiful terminal rendering |

---

## Anti-Flicker Strategies

### Root Causes of Flickering

1. **Full Screen Redraws**: Clearing and redrawing entire screen
2. **Print Statements**: Appending lines causing scroll
3. **Rapid Updates**: Too many refreshes per second (>60 Hz)
4. **Layout Recalculation**: CSS reflow on every change

### Solutions Implemented

#### 1. Reactive Attributes (Not Direct Updates)

```python
# BAD: Direct widget manipulation
self.label.renderable = "New text"  # May cause flicker

# GOOD: Reactive attribute
class MyWidget(Static):
    text: reactive[str] = reactive("")

    def watch_text(self, value: str) -> None:
        self.update(value)  # Textual batches this
```

#### 2. CSS Class Toggling (Not Style Changes)

```python
# BAD: Inline style changes
widget.styles.background = "red"  # Triggers reflow

# GOOD: CSS class swapping
widget.remove_class("state--inactive")
widget.add_class("state--active")  # Single batched update
```

#### 3. Message-Based Worker Updates

```python
# BAD: Direct UI access from thread
def background_task(self):
    self.progress_bar.update(50)  # Thread unsafe!

# GOOD: Message posting
@work(thread=True)
def background_task(self):
    self.post_message(ProgressUpdate(50))  # Thread safe

def on_progress_update(self, msg: ProgressUpdate) -> None:
    self.progress_bar.update(msg.value)  # Runs on main thread
```

#### 4. Guard Watchers Against Pre-Mount Calls

```python
def watch_status(self, old: str, new: str) -> None:
    self.remove_class(f"stage--{old}")
    self.add_class(f"stage--{new}")
    # Guard against pre-compose calls
    try:
        self.query_one("#icon", Static).update(self._get_icon())
    except Exception:
        pass  # Widget not yet composed
```

#### 5. RichLog for Streaming Output

```python
# BAD: Repeated Static updates
log_widget.update(log_widget.renderable + "\n" + new_line)

# GOOD: RichLog.write() - purpose-built for logs
log_widget.write(Text(new_line))  # Appends efficiently
```

---

## Theme & Color System

### Color Palette

```css
/* Primary Colors */
$background:      #0a0e1a;   /* Deep navy - main background */
$surface:         #0f172a;   /* Panel backgrounds */
$surface-elevated: #1e293b;  /* Cards, elevated elements */
$surface-bright:  #1e3a5f;   /* Active/highlighted areas */

/* Borders */
$border:          #374151;   /* Default borders */
$border-active:   #1e3a5f;   /* Active panel borders */

/* Accent Colors */
$primary:         #38bdf8;   /* Cyan - main accent */
$secondary:       #818cf8;   /* Violet - secondary accent */
$success:         #22c55e;   /* Green - completion states */
$warning:         #fbbf24;   /* Amber - warnings */
$error:           #ef4444;   /* Red - errors */

/* Text Colors */
$text:            #e2e8f0;   /* Primary text */
$text-muted:      #94a3b8;   /* Secondary text */
$text-dim:        #64748b;   /* Tertiary/disabled text */
```

### Typography

| Element | Style |
|---------|-------|
| Headers | Bold, $primary color |
| Labels | $text-muted color |
| Values | $text color |
| Timestamps | Dim, monospace |
| Status Active | Bold, $primary |
| Status Complete | $success |
| Status Error | Bold, $error |

### File Type Color Coding

| Type | Color | Hex |
|------|-------|-----|
| Video (.mp4, .mkv, etc.) | Cyan | `#38bdf8` |
| Audio (.m4a, .mp3, etc.) | Green | `#22c55e` |
| Transcript (.json, .txt) | Yellow | `#fbbf24` |

---

## Layout Architecture

### Panel Structure

```
+============================================================================+
|  HEADER (show_clock=True)                                                   |
+============================================================================+
|                    |                           |                            |
|  LEFT PANEL (28%)  |  CENTER PANEL (44%)       |  RIGHT PANEL (28%)         |
|                    |                           |                            |
|  +------------+    |  +-------------------+    |  [Config] [Preview] [Log]  |
|  | File       |    |  | Pipeline Status   |    |  +--------------------+    |
|  | Explorer   |    |  | Extract -> Process|    |  | ConfigPanel        |    |
|  | (tree)     |    |  | -> Trans -> Summ  |    |  | - Provider         |    |
|  +------------+    |  +-------------------+    |  | - Model            |    |
|  +------------+    |  +-------------------+    |  | - Template         |    |
|  | File Info  |    |  | Progress Panel    |    |  | - Advanced...      |    |
|  | (metadata) |    |  | [=======    ] 70% |    |  | [Run] [Cancel]     |    |
|  +------------+    |  +-------------------+    |  +--------------------+    |
|                    |  +-------------------+    |                            |
|                    |  | Stage Log         |    |                            |
|                    |  | (RichLog)         |    |                            |
|                    |  +-------------------+    |                            |
+============================================================================+
|  STATUS BAR: Ready | filename.mp4 | OpenAI/gpt-4o-mini                      |
+============================================================================+
|  FOOTER: Q Quit | R Run | Escape Cancel                                     |
+============================================================================+
```

### Widget Hierarchy

```
SummeetsApp (App)
├── Header
├── Horizontal#main-container
│   ├── Vertical#left-panel
│   │   ├── Static.panel-header ("FILE EXPLORER")
│   │   ├── FileExplorer (DirectoryTree)
│   │   └── FileInfo
│   ├── Vertical#center-panel
│   │   ├── PipelineStatus
│   │   │   ├── Static.pipeline-title
│   │   │   └── Horizontal.pipeline-flow
│   │   │       ├── StageIndicator#stage-extract
│   │   │       ├── Static.connector
│   │   │       ├── StageIndicator#stage-process
│   │   │       ├── Static.connector
│   │   │       ├── StageIndicator#stage-transcribe
│   │   │       ├── Static.connector
│   │   │       └── StageIndicator#stage-summarize
│   │   ├── ProgressPanel
│   │   │   ├── Static.progress-title
│   │   │   ├── Static#stage-text
│   │   │   ├── ProgressBar#progress-bar
│   │   │   └── Static#eta-text
│   │   ├── Static.panel-header ("ACTIVITY LOG")
│   │   └── RichLog#stage-log
│   └── Vertical#right-panel
│       └── TabbedContent
│           ├── TabPane#config-tab
│           │   └── ConfigPanel
│           ├── TabPane#preview-tab
│           │   └── ScrollableContainer
│           │       └── Markdown#preview-md
│           └── TabPane#log-tab
│               └── RichLog#full-log
├── Static#status-bar
└── Footer
```

---

## Widget Components

### StageIndicator

Custom widget showing pipeline stage status with animated transitions.

```python
class StageIndicator(Static):
    """Pipeline stage with status icon and elapsed time."""

    status: reactive[str] = reactive("pending")  # pending|active|complete|error
    elapsed: reactive[str] = reactive("")

    def __init__(self, name: str, icon: str = "○", **kwargs):
        super().__init__(**kwargs)
        self.stage_name = name
        self.icon = icon
        self.add_class("stage--pending")

    def compose(self) -> ComposeResult:
        yield Static(self.stage_name, classes="stage-name")
        yield Static(self._get_status_display(), classes="stage-icon", id="icon")
        yield Static("", classes="stage-time", id="time")
```

**CSS States:**
- `.stage--pending`: Opacity 0.4, dashed border
- `.stage--active`: Cyan border, bright background, blinking icon
- `.stage--complete`: Green border, checkmark icon
- `.stage--error`: Red border, X icon

### PipelineStatus

Container showing all 4 stages with connectors.

```python
class PipelineStatus(Container):
    def compose(self) -> ComposeResult:
        yield Static("━━━  PROCESSING PIPELINE  ━━━", classes="pipeline-title")
        with Horizontal(classes="pipeline-flow"):
            yield StageIndicator("Extract", id="stage-extract")
            yield Static("━━▶", classes="connector")
            yield StageIndicator("Process", id="stage-process")
            yield Static("━━▶", classes="connector")
            yield StageIndicator("Transcribe", id="stage-transcribe")
            yield Static("━━▶", classes="connector")
            yield StageIndicator("Summarize", id="stage-summarize")

    def update_stage(self, stage_id: str, status: str, elapsed: str = ""):
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
```

### FileExplorer

Extended DirectoryTree with format filtering and color coding.

```python
class FileExplorer(DirectoryTree):
    VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}
    AUDIO_EXT = {".m4a", ".flac", ".wav", ".mp3", ".ogg"}
    TRANSCRIPT_EXT = {".json", ".txt", ".srt"}

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        supported = self.VIDEO_EXT | self.AUDIO_EXT | self.TRANSCRIPT_EXT
        return [p for p in paths if p.is_dir() or p.suffix.lower() in supported]

    def render_label(self, node, base_style, style) -> Text:
        label = super().render_label(node, base_style, style)
        if node.data and hasattr(node.data, 'path') and node.data.path.is_file():
            ext = node.data.path.suffix.lower()
            if ext in self.VIDEO_EXT:
                label.stylize("bold #38bdf8")
            elif ext in self.AUDIO_EXT:
                label.stylize("bold #22c55e")
            elif ext in self.TRANSCRIPT_EXT:
                label.stylize("bold #fbbf24")
        return label
```

### ConfigPanel

Form with provider/model/template selection and collapsible advanced options.

```python
class ConfigPanel(Container):
    def compose(self) -> ComposeResult:
        yield Static("◆ CONFIGURATION", classes="section-title")

        yield Label("LLM Provider")
        yield Select(options=[("OpenAI", "openai"), ("Anthropic", "anthropic")],
                     value="openai", id="provider")

        yield Label("Model")
        yield Input(value="gpt-4o-mini", id="model")

        yield Label("Template")
        yield Select(options=[("Default", "default"), ...], id="template")

        yield Checkbox("Auto-detect template", value=True, id="auto-detect")

        with Collapsible(title="Advanced Options", collapsed=True):
            yield Label("Chunk Size (seconds)")
            yield Input(value="1800", id="chunk-size")
            # ... more options

        yield Button("▶  Run Workflow", id="btn-run", classes="btn-run")
        yield Button("■  Cancel", id="btn-cancel", classes="btn-cancel", disabled=True)
```

---

## Message System

Custom messages enable thread-safe communication between workers and UI.

### Message Definitions

```python
from textual.message import Message

class StageUpdate(Message):
    """Update a pipeline stage status."""
    def __init__(self, stage_id: str, status: str, progress: float = 0):
        self.stage_id = stage_id
        self.status = status
        self.progress = progress
        super().__init__()

class LogMessage(Message):
    """Add a log entry."""
    def __init__(self, text: str, style: str = ""):
        self.text = text
        self.style = style
        super().__init__()

class OverallProgress(Message):
    """Update overall progress bar."""
    def __init__(self, progress: float, label: str = ""):
        self.progress = progress
        self.label = label
        super().__init__()

class WorkflowDone(Message):
    """Workflow completed."""
    def __init__(self, success: bool = True):
        self.success = success
        super().__init__()
```

### Message Handlers

```python
class SummeetsApp(App):
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
            self._log("✓ Workflow completed!", "bold green")
```

---

## Background Workers

### Worker Pattern

```python
from textual import work
from textual.worker import get_current_worker

class SummeetsApp(App):
    @work(thread=True, exclusive=True)
    async def run_workflow(self) -> None:
        """Execute workflow in background thread."""
        worker = get_current_worker()

        stages = [
            ("extract", "Extracting audio", 3),
            ("process", "Processing audio", 2),
            ("transcribe", "Transcribing", 5),
            ("summarize", "Summarizing", 4),
        ]

        for stage_id, description, duration in stages:
            if worker.is_cancelled:
                return

            # Post stage start
            self.post_message(StageUpdate(stage_id, "active"))
            self.post_message(LogMessage(f"▸ {description}...", "cyan"))

            # Simulate/execute work
            for progress in range(100):
                if worker.is_cancelled:
                    return

                # Update progress via message (thread-safe)
                self.post_message(OverallProgress(progress, description))
                await asyncio.sleep(0.01 * duration)

            # Post stage complete
            self.post_message(StageUpdate(stage_id, "complete"))

        self.post_message(WorkflowDone(True))
```

### Worker Decorator Options

| Option | Description |
|--------|-------------|
| `thread=True` | Run in thread pool (required for blocking I/O) |
| `exclusive=True` | Cancel previous worker when starting new one |
| `exit_on_error=False` | Don't exit app on worker exception |

### Cancellation Handling

```python
def action_cancel(self) -> None:
    for w in self.workers:
        w.cancel()
    self.is_processing = False
    self._toggle_buttons(False)
    self._log("⚠ Workflow cancelled", "yellow")
```

---

## CSS Styling Reference

### Complete App CSS

```css
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

Footer {
    background: #0f172a;
}
```

### StageIndicator CSS

```css
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
```

### Button Styling

```css
.btn-run {
    background: #38bdf8;
    color: #0a0e1a;
    text-style: bold;
}

.btn-run:hover {
    background: #818cf8;
}

.btn-cancel {
    background: #374151;
    color: #94a3b8;
}

.btn-cancel:hover {
    background: #ef4444;
    color: white;
}
```

---

## Implementation Checklist

### Phase 1: Foundation
- [ ] Create `cli/tui/` directory structure
- [ ] Set up `__init__.py` with exports
- [ ] Define custom message types in `messages.py`
- [ ] Create base CSS in `styles.py` or inline

### Phase 2: Widgets
- [ ] Implement `StageIndicator` with reactive status
- [ ] Implement `PipelineStatus` container
- [ ] Implement `FileExplorer` with filtering
- [ ] Implement `FileInfo` panel
- [ ] Implement `ProgressPanel`
- [ ] Implement `ConfigPanel` with all options

### Phase 3: Main App
- [ ] Create `SummeetsApp` class
- [ ] Define keyboard bindings
- [ ] Implement `compose()` with full layout
- [ ] Add event handlers for file selection
- [ ] Add button event handlers

### Phase 4: Workflow Integration
- [ ] Create background worker for workflow
- [ ] Connect to `src/workflow.py`
- [ ] Implement progress callbacks
- [ ] Add error handling
- [ ] Test with real files

### Phase 5: Polish
- [ ] Add summary preview loading
- [ ] Fine-tune animations
- [ ] Add keyboard navigation
- [ ] Test cancellation
- [ ] Performance testing

---

## File Structure

```
summeets/
├── cli/
│   ├── app.py           # CLI commands
│   └── tui/
│       ├── __init__.py  # Exports run()
│       ├── app.py       # SummeetsApp class
│       ├── widgets.py   # Custom widgets
│       ├── messages.py  # Custom message types
│       └── demo.py      # Demo/test version
├── src/                 # (renamed from core/)
│   ├── workflow.py      # Workflow engine
│   ├── models.py        # Data models
│   └── ...
└── docs/
    └── TUI-IMPLEMENTATION-GUIDE.md
```

---

## Running the TUI

```bash
# Demo mode (simulated workflow)
python -m cli.tui.demo

# Production mode
python main.py gui
# or
summeets tui
```

---

*Document Version: 1.0 | Last Updated: 2025-01-10*
