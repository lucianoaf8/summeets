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

__all__ = ["SummeetsApp", "SummeetsDemo", "run"]


def run_demo():
    """Launch the TUI in demo mode (simulated workflow)."""
    app = SummeetsDemo()
    app.run()
