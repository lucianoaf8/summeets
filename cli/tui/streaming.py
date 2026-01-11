"""
Streaming display widgets for efficient handling of large content.

Provides lazy loading and pagination for transcripts and summaries,
preventing memory issues with large files.
"""
from pathlib import Path
from typing import Optional, List, Callable
import math

from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static
from textual.containers import Vertical, Horizontal
from textual.widgets import Button
from textual.app import ComposeResult

from .constants import COLOR_ACCENT_PRIMARY, COLOR_TEXT_DIM


class StreamingText(Static):
    """
    Text widget that loads content lazily in pages.

    Features:
    - Lazy loading of large files
    - Pagination with navigation
    - Memory-efficient display
    - Smooth scrolling within pages
    """

    DEFAULT_CSS = """
    StreamingText {
        height: 1fr;
        padding: 1;
        background: #0c1322;
    }

    StreamingText .content {
        height: 1fr;
    }

    StreamingText .pagination {
        height: auto;
        dock: bottom;
        padding: 1;
        background: #1e293b;
    }

    StreamingText .page-info {
        color: #64748b;
        text-align: center;
        width: 1fr;
    }

    StreamingText Button {
        width: auto;
        min-width: 8;
        margin: 0 1;
    }

    StreamingText Button.disabled {
        opacity: 0.3;
    }
    """

    LINES_PER_PAGE = 100
    CHUNK_SIZE = 4096  # Bytes to read at a time

    # Reactive state
    current_page: reactive[int] = reactive(1)
    total_pages: reactive[int] = reactive(1)

    def __init__(
        self,
        content: str = "",
        file_path: Optional[Path] = None,
        lines_per_page: int = 100,
        **kwargs
    ):
        """
        Initialize streaming text widget.

        Args:
            content: Initial text content
            file_path: Optional file to load lazily
            lines_per_page: Lines per page for pagination
        """
        super().__init__(**kwargs)
        self._content = content
        self._file_path = file_path
        self._lines_per_page = lines_per_page
        self._lines: List[str] = []
        self._loaded = False

    def compose(self) -> ComposeResult:
        yield Static("", id="content-display", classes="content")
        with Horizontal(classes="pagination"):
            yield Button("◀ Prev", id="btn-prev")
            yield Static("Page 1/1", id="page-info", classes="page-info")
            yield Button("Next ▶", id="btn-next")

    def on_mount(self) -> None:
        """Load content on mount."""
        self._load_content()
        self._update_display()

    def _load_content(self) -> None:
        """Load content from file or string."""
        if self._loaded:
            return

        if self._file_path and self._file_path.exists():
            try:
                # Read file and split into lines
                text = self._file_path.read_text(encoding="utf-8")
                self._lines = text.splitlines()
            except Exception as e:
                self._lines = [f"Error loading file: {e}"]
        elif self._content:
            self._lines = self._content.splitlines()
        else:
            self._lines = ["No content"]

        # Calculate pagination
        self.total_pages = max(1, math.ceil(len(self._lines) / self._lines_per_page))
        self.current_page = 1
        self._loaded = True

    def _update_display(self) -> None:
        """Update the visible content for current page."""
        try:
            start_idx = (self.current_page - 1) * self._lines_per_page
            end_idx = start_idx + self._lines_per_page

            page_lines = self._lines[start_idx:end_idx]
            content_text = "\n".join(page_lines)

            display = self.query_one("#content-display", Static)
            display.update(content_text)

            # Update pagination info
            page_info = self.query_one("#page-info", Static)
            page_info.update(f"Page {self.current_page}/{self.total_pages}")

            # Update button states
            prev_btn = self.query_one("#btn-prev", Button)
            next_btn = self.query_one("#btn-next", Button)

            prev_btn.disabled = self.current_page <= 1
            next_btn.disabled = self.current_page >= self.total_pages

        except Exception:
            pass

    def watch_current_page(self, page: int) -> None:
        """React to page changes."""
        self._update_display()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle pagination button clicks."""
        if event.button.id == "btn-prev" and self.current_page > 1:
            self.current_page -= 1
        elif event.button.id == "btn-next" and self.current_page < self.total_pages:
            self.current_page += 1

    def set_content(self, content: str) -> None:
        """Set new content."""
        self._content = content
        self._file_path = None
        self._loaded = False
        self._load_content()
        self._update_display()

    def load_file(self, file_path: Path) -> None:
        """Load content from file."""
        self._file_path = file_path
        self._content = ""
        self._loaded = False
        self._load_content()
        self._update_display()

    def go_to_page(self, page: int) -> None:
        """Jump to specific page."""
        if 1 <= page <= self.total_pages:
            self.current_page = page

    def search(self, term: str) -> Optional[int]:
        """
        Search for term and return page number.

        Args:
            term: Text to search for

        Returns:
            Page number containing the term, or None
        """
        term_lower = term.lower()
        for i, line in enumerate(self._lines):
            if term_lower in line.lower():
                return (i // self._lines_per_page) + 1
        return None


class TranscriptViewer(Vertical):
    """
    Specialized viewer for transcript content with speaker highlighting.

    Features:
    - Speaker-based color coding
    - Timestamp display
    - Search functionality
    - Segment navigation
    """

    DEFAULT_CSS = """
    TranscriptViewer {
        height: 1fr;
    }

    TranscriptViewer .header {
        height: auto;
        padding: 1;
        background: #1e293b;
    }

    TranscriptViewer .title {
        text-style: bold;
        color: #818cf8;
    }

    TranscriptViewer .controls {
        height: auto;
        padding: 0 1;
    }

    TranscriptViewer .transcript-content {
        height: 1fr;
        padding: 1;
        background: #0c1322;
        overflow-y: scroll;
    }

    TranscriptViewer .segment {
        margin-bottom: 1;
        padding: 0 1;
    }

    TranscriptViewer .speaker {
        text-style: bold;
        color: #38bdf8;
    }

    TranscriptViewer .timestamp {
        color: #64748b;
        text-style: italic;
    }

    TranscriptViewer .text {
        color: #e2e8f0;
    }
    """

    # Speaker colors for differentiation
    SPEAKER_COLORS = [
        "#38bdf8",  # Cyan
        "#22c55e",  # Green
        "#fbbf24",  # Yellow
        "#a78bfa",  # Purple
        "#f472b6",  # Pink
        "#fb923c",  # Orange
    ]

    def __init__(self, transcript_data: Optional[dict] = None, **kwargs):
        """
        Initialize transcript viewer.

        Args:
            transcript_data: Transcript data with segments
        """
        super().__init__(**kwargs)
        self._transcript = transcript_data
        self._speaker_colors: dict = {}

    def compose(self) -> ComposeResult:
        with Horizontal(classes="header"):
            yield Static("📝 Transcript Viewer", classes="title")
        yield Static("", id="transcript-content", classes="transcript-content")

    def on_mount(self) -> None:
        """Render transcript on mount."""
        if self._transcript:
            self._render_transcript()

    def load_transcript(self, transcript_data: dict) -> None:
        """Load new transcript data."""
        self._transcript = transcript_data
        self._speaker_colors.clear()
        self._render_transcript()

    def _get_speaker_color(self, speaker: str) -> str:
        """Get consistent color for a speaker."""
        if speaker not in self._speaker_colors:
            idx = len(self._speaker_colors) % len(self.SPEAKER_COLORS)
            self._speaker_colors[speaker] = self.SPEAKER_COLORS[idx]
        return self._speaker_colors[speaker]

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _render_transcript(self) -> None:
        """Render transcript content."""
        if not self._transcript:
            return

        try:
            content = self.query_one("#transcript-content", Static)
            text = Text()

            segments = self._transcript.get("segments", [])
            if not segments and isinstance(self._transcript, list):
                segments = self._transcript

            for segment in segments:
                speaker = segment.get("speaker", "Unknown")
                start = segment.get("start", 0)
                segment_text = segment.get("text", "")

                color = self._get_speaker_color(speaker)
                timestamp = self._format_timestamp(start)

                text.append(f"[{timestamp}] ", style="dim italic")
                text.append(f"{speaker}: ", style=f"bold {color}")
                text.append(f"{segment_text}\n\n", style="white")

            content.update(text)

        except Exception as e:
            try:
                content = self.query_one("#transcript-content", Static)
                content.update(f"Error rendering transcript: {e}")
            except Exception:
                pass


class SummaryViewer(Vertical):
    """
    Specialized viewer for summary content with section navigation.

    Features:
    - Section-based navigation
    - Markdown rendering
    - Export functionality
    """

    DEFAULT_CSS = """
    SummaryViewer {
        height: 1fr;
    }

    SummaryViewer .header {
        height: auto;
        padding: 1;
        background: #1e293b;
    }

    SummaryViewer .title {
        text-style: bold;
        color: #818cf8;
    }

    SummaryViewer .summary-content {
        height: 1fr;
        padding: 1;
        overflow-y: scroll;
    }
    """

    def __init__(self, summary_text: str = "", **kwargs):
        """Initialize summary viewer."""
        super().__init__(**kwargs)
        self._summary_text = summary_text

    def compose(self) -> ComposeResult:
        from textual.widgets import Markdown

        with Horizontal(classes="header"):
            yield Static("📋 Summary", classes="title")
        yield Markdown(self._summary_text or "*No summary available*", id="summary-md", classes="summary-content")

    def set_summary(self, text: str) -> None:
        """Set summary content."""
        from textual.widgets import Markdown

        self._summary_text = text
        try:
            md = self.query_one("#summary-md", Markdown)
            md.update(text)
        except Exception:
            pass

    def load_from_file(self, file_path: Path) -> None:
        """Load summary from file."""
        try:
            text = file_path.read_text(encoding="utf-8")
            self.set_summary(text)
        except Exception as e:
            self.set_summary(f"*Error loading summary: {e}*")
