# Summeets TUI Design Document

## Executive Summary

This document presents a comprehensive design for a modern, flicker-free Text User Interface (TUI) for the Summeets video processing workflow. The design prioritizes visual elegance, stability, and real-time feedback across all pipeline stages.

---

## 1. Current State Analysis

### 1.1 Existing CLI Workflow

The current `cli/app.py` provides these commands:
- `transcribe` - Video/audio to transcript (Replicate API)
- `summarize` - Transcript to summary (OpenAI/Anthropic)
- `process` - Complete pipeline (extract + transcribe + summarize)
- `templates` - List available summary templates
- `config` - Show current configuration
- `tui` - Launch existing Textual TUI

### 1.2 Pipeline Stages (from `core/workflow.py`)

```
WorkflowEngine Pipeline:
   1. extract_audio   [video only]     FFmpeg video → audio
   2. process_audio   [video/audio]    Volume/normalization/format
   3. transcribe      [video/audio]    Replicate API → segments
   4. summarize       [all types]      Map-reduce + CoD → markdown
```

### 1.3 Existing TUI Implementation (`cli/tui.py`)

The current TUI has:
- Basic form layout with input fields
- Provider/model/template selection
- Simple progress bar
- RichLog for status messages
- Background worker execution

**Current Issues Identified:**
- Limited visual hierarchy
- No file browser (manual path entry)
- No pipeline stage visualization
- No configuration panel
- No summary preview
- Basic styling (functional but not "futuristic")

---

## 2. Library Comparison and Selection

### 2.1 Comparison Matrix

| Feature | Rich | Textual | PyTermGUI |
|---------|------|---------|-----------|
| **Type** | Output library | Full TUI framework | TUI framework |
| **Widgets** | Renderable components | Interactive widgets | Window-based widgets |
| **Layout** | Columns, tables | CSS-like styling | Slot-based layouts |
| **Reactivity** | N/A | Built-in reactive system | Manual updates |
| **Event Handling** | N/A | Message-based | Event callbacks |
| **Anti-Flicker** | Live display context | Virtual DOM-like refresh | Manual management |
| **File Browser** | N/A | DirectoryTree widget | Manual implementation |
| **Progress** | Progress bars, spinners | ProgressBar widget | Basic support |
| **Logging** | Console, handlers | Log, RichLog widgets | Print-based |
| **Async Support** | N/A | Workers API | Limited |
| **Maturity** | Very mature | Mature, active | Less active |
| **Documentation** | Excellent | Excellent | Good |

### 2.2 Recommendation: Textual

**Selected Framework: Textual (with Rich as rendering engine)**

**Rationale:**
1. **Native anti-flicker** - Virtual DOM-like updates prevent screen artifacts
2. **Reactive architecture** - State changes automatically propagate to UI
3. **CSS-like styling** - Enables modern, futuristic aesthetics
4. **DirectoryTree widget** - Built-in file browser for selection
5. **Workers API** - Clean background task management with progress
6. **Message system** - Thread-safe UI updates from background processes
7. **Rich integration** - Textual builds on Rich for beautiful rendering
8. **Active development** - Regular updates, strong community

---

## 3. Anti-Flicker Strategy

### 3.1 Root Causes of Flickering

| Cause | Description | Frequency |
|-------|-------------|-----------|
| Full redraws | Clearing and redrawing entire screen | High |
| Print statements | Appending lines causing scroll | Medium |
| Rapid updates | Too many refreshes per second | High |
| Layout recalculation | CSS reflow on every change | Medium |

### 3.2 Textual Anti-Flicker Mechanisms

#### 3.2.1 Virtual DOM-Like Updates
```python
# BAD: Full screen clear and redraw
console.clear()
console.print(new_content)  # Causes flicker

# GOOD: Textual reactive updates
self.my_label.update(new_content)  # Only updates changed regions
```

#### 3.2.2 Consolidated Refresh Cycles
```python
# Textual batches multiple reactive changes into single refresh
self.progress = 50
self.status = "Processing..."
self.current_stage = "transcribe"
# All three changes render in ONE refresh cycle
```

#### 3.2.3 Region-Based Refreshing
```python
# Textual's Line API enables partial updates
def render_line(self, y: int) -> Strip:
    # Only redraws specific lines that changed
    return Strip([Segment(self.lines[y])])
```

#### 3.2.4 Worker Thread Safety
```python
# Safe UI updates from background threads
@work(thread=True)
def process_file(self, path: Path) -> None:
    for progress in do_work():
        # Thread-safe message posting
        self.post_message(ProgressUpdate(progress))

def on_progress_update(self, message: ProgressUpdate) -> None:
    # Handler runs on main thread - safe to update UI
    self.progress_bar.update(progress=message.value)
```

### 3.3 Implementation Guidelines

1. **Never use print()** - Always use widget.update() or post_message()
2. **Use reactive attributes** - Let Textual manage refresh timing
3. **Batch state changes** - Group related updates together
4. **Throttle high-frequency updates** - Limit progress updates to ~10 Hz
5. **Use RichLog.write()** - Not repeated Static widget updates
6. **Avoid recompose()** - Prefer targeted updates over full rebuilds

---

## 4. TUI Architecture

### 4.1 Component Hierarchy

```
SummeetsApp (App)
   Header
   MainContainer (Container)
      LeftPanel (Vertical)
         FileExplorer (DirectoryTree)
         FileInfo (Static)
      CenterPanel (Vertical)
         PipelineStatus (Container)
            StageIndicator [extract_audio]
            StageIndicator [process_audio]
            StageIndicator [transcribe]
            StageIndicator [summarize]
         ActiveStageDetails (Container)
            StageProgress (ProgressBar)
            StageLog (RichLog)
      RightPanel (TabbedContent)
         ConfigTab (Vertical)
            ProviderSelect
            ModelInput
            TemplateSelect
            AdvancedOptions (Collapsible)
         PreviewTab (Vertical)
            SummaryPreview (Markdown)
         LogTab (Vertical)
            FullLog (RichLog)
   StatusBar (Static)
   Footer
```

### 4.2 Data Flow Architecture

```
User Input          State Layer              UI Layer
     |                   |                      |
     v                   v                      v
[FileSelected] --> [AppState] ----watch----> [Widgets]
[ButtonPressed] -> reactive vars            [Auto-refresh]
[ConfigChanged]      |
                     |
              [WorkflowEngine]
                     |
                     v
              [ProgressMessage] --post_message--> [StageIndicator]
              [LogMessage]                        [RichLog]
              [CompletionMessage]                 [PreviewTab]
```

### 4.3 State Management

```python
class SummeetsApp(App):
    # Reactive state
    selected_file: reactive[Path | None] = reactive(None)
    current_stage: reactive[str] = reactive("")
    overall_progress: reactive[float] = reactive(0.0)
    is_processing: reactive[bool] = reactive(False)

    # Configuration state
    provider: reactive[str] = reactive("openai")
    model: reactive[str] = reactive("gpt-4o-mini")
    template: reactive[str] = reactive("default")
    auto_detect: reactive[bool] = reactive(True)

    # Watchers trigger UI updates automatically
    def watch_current_stage(self, stage: str) -> None:
        self.query_one(PipelineStatus).highlight_stage(stage)

    def watch_selected_file(self, path: Path | None) -> None:
        self.query_one(FileInfo).update_info(path)
```

---

## 5. Component Specifications

### 5.1 StageIndicator Widget

Custom compound widget for each pipeline stage.

```python
class StageIndicator(Static):
    """Visual indicator for a single pipeline stage."""

    COMPONENT_CLASSES = {"stage--pending", "stage--active", "stage--complete", "stage--error"}

    stage_name: reactive[str] = reactive("")
    status: reactive[str] = reactive("pending")  # pending, active, complete, error
    progress: reactive[float] = reactive(0.0)
    duration: reactive[float] = reactive(0.0)

    def compose(self) -> ComposeResult:
        yield Static(self.stage_name, classes="stage-label")
        yield ProgressBar(total=100, show_eta=False, id="stage-progress")
        yield Static("", id="stage-status")

    def watch_status(self, status: str) -> None:
        self.remove_class("stage--pending", "stage--active", "stage--complete", "stage--error")
        self.add_class(f"stage--{status}")
```

### 5.2 PipelineStatus Container

```python
class PipelineStatus(Container):
    """Container showing all pipeline stages with visual flow."""

    def compose(self) -> ComposeResult:
        with Horizontal(classes="pipeline-flow"):
            yield StageIndicator("Extract Audio", id="stage-extract")
            yield Static(" -> ", classes="stage-connector")
            yield StageIndicator("Process Audio", id="stage-process")
            yield Static(" -> ", classes="stage-connector")
            yield StageIndicator("Transcribe", id="stage-transcribe")
            yield Static(" -> ", classes="stage-connector")
            yield StageIndicator("Summarize", id="stage-summarize")

    def highlight_stage(self, stage_name: str) -> None:
        stage_map = {
            "extract_audio": "#stage-extract",
            "process_audio": "#stage-process",
            "transcribe": "#stage-transcribe",
            "summarize": "#stage-summarize"
        }
        if stage_name in stage_map:
            self.query_one(stage_map[stage_name]).status = "active"
```

### 5.3 FileExplorer (Enhanced DirectoryTree)

```python
class FileExplorer(DirectoryTree):
    """File browser filtered for supported formats."""

    SUPPORTED_EXTENSIONS = {
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",  # Video
        ".m4a", ".flac", ".wav", ".mka", ".ogg", ".mp3",  # Audio
        ".json", ".txt", ".srt"  # Transcripts
    }

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [
            path for path in paths
            if path.is_dir() or path.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ]

    def render_label(self, node, base_style, style) -> Text:
        label = super().render_label(node, base_style, style)
        if node.data.path.is_file():
            ext = node.data.path.suffix.lower()
            if ext in {".mp4", ".mkv", ".avi", ".mov"}:
                label.stylize("bold cyan")  # Video files
            elif ext in {".m4a", ".flac", ".wav", ".mp3"}:
                label.stylize("bold green")  # Audio files
            elif ext in {".json", ".txt", ".srt"}:
                label.stylize("bold yellow")  # Transcript files
        return label
```

### 5.4 Background Worker Integration

```python
class SummeetsApp(App):

    @work(thread=True, exclusive=True)
    def run_workflow(self) -> None:
        """Execute workflow in background thread."""
        worker = get_current_worker()

        config = self._build_workflow_config()

        def progress_callback(step, total, step_name, status):
            if not worker.is_cancelled:
                self.post_message(WorkflowProgress(step, total, step_name, status))

        try:
            results = execute_workflow(config, progress_callback)
            if not worker.is_cancelled:
                self.post_message(WorkflowComplete(results))
        except Exception as e:
            if not worker.is_cancelled:
                self.post_message(WorkflowError(str(e)))

    def on_workflow_progress(self, message: WorkflowProgress) -> None:
        """Handle progress updates on main thread (safe for UI)."""
        self.current_stage = message.step_name
        self.overall_progress = message.step / message.total * 100

        log = self.query_one("#stage-log", RichLog)
        log.write(Text(f"[{message.step}/{message.total}] {message.status}"))
```

---

## 6. Visual Design Specifications

### 6.1 Color Palette

```css
/* Futuristic Dark Theme */
$background: #0a0e1a;         /* Deep navy */
$surface: #111827;             /* Elevated panels */
$surface-bright: #1f2937;      /* Highlighted areas */
$border: #374151;              /* Subtle borders */

$primary: #38bdf8;             /* Cyan - main accent */
$secondary: #818cf8;           /* Violet - secondary accent */
$success: #22c55e;             /* Green - completion */
$warning: #f59e0b;             /* Amber - warnings */
$error: #ef4444;               /* Red - errors */

$text: #e2e8f0;                /* Primary text */
$text-muted: #94a3b8;          /* Secondary text */
$text-dim: #64748b;            /* Tertiary text */

/* Gradient accents for futuristic feel */
$gradient-primary: linear-gradient(135deg, #38bdf8, #818cf8);
$gradient-success: linear-gradient(135deg, #22c55e, #38bdf8);
```

### 6.2 Typography Hierarchy

```css
/* Headers */
.header-title { text-style: bold; color: $primary; }
.section-title { text-style: bold; color: $text; }
.subsection-title { color: $text-muted; }

/* Status indicators */
.status-pending { color: $text-dim; }
.status-active { color: $primary; text-style: bold; }
.status-complete { color: $success; }
.status-error { color: $error; text-style: bold; }

/* Data display */
.mono { font-family: "monospace"; }
.file-path { color: $secondary; }
.timestamp { color: $text-muted; }
```

### 6.3 Component Styling

```css
Screen {
    background: $background;
    color: $text;
}

#left-panel {
    width: 30%;
    background: $surface;
    border: solid $border;
    padding: 1;
}

#center-panel {
    width: 45%;
    background: $surface;
    border: solid $border;
    padding: 1;
}

#right-panel {
    width: 25%;
    background: $surface;
    border: solid $border;
}

.pipeline-flow {
    height: auto;
    align: center middle;
    padding: 1 2;
}

StageIndicator {
    width: auto;
    min-width: 16;
    padding: 1;
    border: solid $border;
    border-radius: 1;
}

StageIndicator.stage--pending {
    opacity: 0.5;
}

StageIndicator.stage--active {
    border: solid $primary;
    background: $surface-bright;
}

StageIndicator.stage--complete {
    border: solid $success;
}

StageIndicator.stage--error {
    border: solid $error;
    background: $surface-bright;
}

.stage-connector {
    color: $text-dim;
    padding: 0 1;
}

ProgressBar {
    padding: 1;
}

ProgressBar > .bar--bar {
    color: $primary;
}

ProgressBar > .bar--complete {
    color: $success;
}

DirectoryTree {
    scrollbar-color: $primary;
    scrollbar-color-hover: $secondary;
}

RichLog {
    scrollbar-color: $primary;
    background: $background;
    border: solid $border;
    padding: 1;
}

TabbedContent {
    height: 100%;
}

ContentSwitcher {
    height: 1fr;
}

TabPane {
    padding: 1;
}

Button.primary {
    background: $primary;
    color: $background;
}

Button.primary:hover {
    background: $secondary;
}

Button.danger {
    background: $error;
    color: $text;
}

Input {
    border: solid $border;
    background: $surface-bright;
}

Input:focus {
    border: solid $primary;
}

Select {
    border: solid $border;
}

Checkbox {
    padding: 0 1;
}

Footer {
    background: $surface;
}

#status-bar {
    dock: bottom;
    height: 1;
    background: $surface-bright;
    padding: 0 2;
}
```

---

## 7. Wireframes

### 7.1 Main Application Layout

```
+==============================================================================+
|  SUMMEETS - Video Transcription & Summarization              [12:34:56 PM]   |
+==============================================================================+
|                         |                              |                     |
|  FILE EXPLORER          |  PIPELINE STATUS             |  [Config] [Preview] |
|  ---------------------- |  ------------------------    |  ---------------    |
|  v Documents            |                              |                     |
|    v Meetings           |  +--------+    +--------+    |  Provider:          |
|      > 2024-01-09       |  |Extract |    |Process |    |  [OpenAI      v]    |
|      > 2024-01-08       |  |Audio   | -> |Audio   | -> |                     |
|    v Recordings         |  |   --   |    |   --   |    |  Model:             |
|      meeting.mp4        |  +--------+    +--------+    |  [gpt-4o-mini    ]  |
|      interview.m4a      |       |             |        |                     |
|    v Transcripts        |       v             v        |  Template:          |
|      notes.json         |  +--------+    +--------+    |  [Default      v]   |
|                         |  |Transcr-| -> |Summar- |    |                     |
|  ---------------------- |  |ibe     |    |ize     |    |  [x] Auto-detect    |
|  FILE INFO              |  |  [##]  |    |   --   |    |                     |
|  meeting.mp4            |  +--------+    +--------+    |  ---------------    |
|  Size: 245.3 MB         |                              |  > Advanced...      |
|  Duration: 01:23:45     |  CURRENT STAGE: Transcribe   |                     |
|  Type: Video (MP4)      |  [==============      ] 67%  |  [  Run Workflow  ] |
|                         |  ETA: 2:34                   |  [     Cancel      ]|
|                         |                              |                     |
|                         |  ----- Stage Log -----       |                     |
|                         |  [12:30] Starting transcr... |                     |
|                         |  [12:31] Uploaded to Repl... |                     |
|                         |  [12:32] Processing segm...  |                     |
|                         |  [12:33] 245/367 segments... |                     |
+==============================================================================+
|  Ready | meeting.mp4 selected | OpenAI/gpt-4o-mini | Template: Default      |
+==============================================================================+
|  Q Quit | R Run | C Config | P Preview | ? Help                              |
+==============================================================================+
```

### 7.2 Preview Tab Active

```
+==============================================================================+
|  SUMMEETS - Video Transcription & Summarization              [12:45:00 PM]   |
+==============================================================================+
|                         |                              |                     |
|  FILE EXPLORER          |  PIPELINE STATUS             |  [Config] [Preview] |
|  ---------------------- |  ------------------------    |  ===============    |
|  ...                    |                              |                     |
|                         |  +--------+    +--------+    |  SUMMARY PREVIEW    |
|                         |  |Extract |    |Process |    |  ---------------    |
|                         |  |Audio   | -> |Audio   | -> |                     |
|                         |  |  [OK]  |    |  [OK]  |    |  # Meeting Summary  |
|                         |  +--------+    +--------+    |                     |
|                         |       |             |        |  ## Key Points      |
|                         |       v             v        |  - Discussed Q1...  |
|                         |  +--------+    +--------+    |  - Agreed on new... |
|                         |  |Transcr-| -> |Summar- |    |  - Timeline for...  |
|                         |  |ibe     |    |ize     |    |                     |
|                         |  |  [OK]  |    |  [OK]  |    |  ## Action Items    |
|                         |  +--------+    +--------+    |  1. John: Review... |
|                         |                              |  2. Mary: Schedule..|
|                         |  COMPLETED IN 5:23           |  3. Team: Update... |
|                         |  [====================] 100% |                     |
|                         |                              |  ## Decisions       |
|                         |  ----- Stage Log -----       |  - Approved budget  |
|                         |  [12:45] Complete!           |  - New deadline set |
+==============================================================================+
```

### 7.3 Error State

```
+==============================================================================+
|  SUMMEETS - Video Transcription & Summarization              [12:50:00 PM]   |
+==============================================================================+
|                         |                              |                     |
|  FILE EXPLORER          |  PIPELINE STATUS             |  [Config] [Preview] |
|  ---------------------- |  ------------------------    |  ---------------    |
|  ...                    |                              |                     |
|                         |  +--------+    +--------+    |  ERROR DETAILS      |
|                         |  |Extract |    |Process |    |  ---------------    |
|                         |  |Audio   | -> |Audio   | -> |                     |
|                         |  |  [OK]  |    |  [OK]  |    |  Transcription      |
|                         |  +--------+    +--------+    |  Failed             |
|                         |       |             |        |                     |
|                         |       v             v        |  API Error:         |
|                         |  +--------+    +--------+    |  Rate limit         |
|                         |  |Transcr-| -> |Summar- |    |  exceeded.          |
|                         |  |ibe     |    |ize     |    |  Please try again   |
|                         |  | [ERR]  |    |   --   |    |  in 60 seconds.     |
|                         |  +--------+    +--------+    |                     |
|                         |                              |  ---------------    |
|                         |  ERROR: API rate limit       |                     |
|                         |  [==========          ] 50%  |  [   Retry    ]     |
|                         |                              |  [ View Full Log ]  |
|                         |  ----- Stage Log -----       |                     |
|                         |  [12:49] Replicate error...  |                     |
+==============================================================================+
```

### 7.4 Advanced Configuration Expanded

```
+==================================+
|  CONFIGURATION                   |
|  ---------------                 |
|                                  |
|  Provider:                       |
|  [OpenAI           v]            |
|                                  |
|  Model:                          |
|  [gpt-4o-mini              ]     |
|                                  |
|  Template:                       |
|  [Default          v]            |
|    - Default                     |
|    - SOP                         |
|    - Decision                    |
|    - Brainstorm                  |
|    - Requirements                |
|                                  |
|  [x] Auto-detect template        |
|                                  |
|  v ADVANCED OPTIONS              |
|  +------------------------------+|
|  | Chunk Size (seconds):       ||
|  | [1800                     ] ||
|  |                             ||
|  | CoD Passes:                 ||
|  | [2                        ] ||
|  |                             ||
|  | Max Tokens:                 ||
|  | [3000                     ] ||
|  |                             ||
|  | Audio Format:               ||
|  | [m4a            v]          ||
|  |                             ||
|  | [x] Normalize audio         ||
|  | [ ] Increase volume         ||
|  | Volume Gain (dB): [10]      ||
|  +------------------------------+|
|                                  |
|  [     Run Workflow     ]        |
|  [       Cancel         ]        |
+==================================+
```

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Create new `cli/tui_v2.py` with basic app structure
- [ ] Implement CSS styling with futuristic theme
- [ ] Create custom StageIndicator widget
- [ ] Build PipelineStatus container

### Phase 2: File Selection (Week 1-2)
- [ ] Implement FileExplorer with format filtering
- [ ] Add FileInfo panel with metadata display
- [ ] Integrate file type detection

### Phase 3: Configuration (Week 2)
- [ ] Build configuration panel with all options
- [ ] Add collapsible advanced settings
- [ ] Implement reactive state binding

### Phase 4: Workflow Execution (Week 2-3)
- [ ] Create background worker with progress callback
- [ ] Implement custom messages for stage updates
- [ ] Add proper error handling and display
- [ ] Integrate with existing WorkflowEngine

### Phase 5: Preview & Polish (Week 3)
- [ ] Add summary preview with Markdown rendering
- [ ] Implement full log tab
- [ ] Add keyboard shortcuts
- [ ] Final styling refinements

### Phase 6: Testing & Documentation (Week 4)
- [ ] Unit tests for custom widgets
- [ ] Integration tests for workflow execution
- [ ] Update README with TUI usage
- [ ] Performance testing for large files

---

## 9. File Structure

```
summeets/
   cli/
      app.py              # Existing CLI (unchanged)
      tui.py              # Existing basic TUI (deprecated)
      tui_v2/
         __init__.py      # Module exports
         app.py           # Main SummeetsApp class
         widgets/
            __init__.py
            stage_indicator.py
            pipeline_status.py
            file_explorer.py
            file_info.py
            config_panel.py
            preview_panel.py
         messages.py      # Custom message types
         styles.tcss      # CSS styling
```

---

## 10. Key Dependencies

```toml
[project.optional-dependencies]
tui = [
    "textual>=0.52.0",     # TUI framework
    "rich>=13.0.0",        # Rendering engine (already a dependency)
]
```

---

## 11. Summary

This design document provides a comprehensive blueprint for building a modern, flicker-free TUI for Summeets. Key decisions include:

1. **Framework Selection**: Textual with Rich rendering for optimal stability and aesthetics
2. **Anti-Flicker Strategy**: Reactive updates, worker-based background processing, message-based UI updates
3. **Visual Design**: Dark futuristic theme with cyan/violet accent gradients
4. **Architecture**: Compound widgets, reactive state management, clean separation of concerns
5. **User Experience**: File browser, visual pipeline status, real-time logs, preview pane

The implementation follows a phased approach, prioritizing foundation and core functionality before polish and optimization.
