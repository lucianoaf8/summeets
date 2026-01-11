"""
Summeets TUI - Modern Textual-based Terminal User Interface

This package provides a flicker-free, futuristic TUI for the Summeets
video transcription and summarization workflow.

Usage:
    from cli.tui import run
    run()

Or run demo mode:
    from cli.tui import run_demo
    run_demo()
"""

from .app import SummeetsApp, run
from .demo import SummeetsDemo
from .processing import ProcessingController, WorkflowAdapter
from .exceptions import TUIError, format_error_for_display
from .constants import (
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
    TRANSCRIPT_EXTENSIONS,
    VALID_PROVIDERS,
    DEFAULT_MODELS,
)

__all__ = [
    "SummeetsApp",
    "SummeetsDemo",
    "run",
    "ProcessingController",
    "WorkflowAdapter",
    "TUIError",
    "format_error_for_display",
    "VIDEO_EXTENSIONS",
    "AUDIO_EXTENSIONS",
    "TRANSCRIPT_EXTENSIONS",
    "VALID_PROVIDERS",
    "DEFAULT_MODELS",
]


def run_demo():
    """Launch the TUI in demo mode (simulated workflow)."""
    app = SummeetsDemo()
    app.run()
