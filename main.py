#!/usr/bin/env python3
"""
Main entry point for Summeets - Audio Meeting Transcription and Summarization Tool

Usage:
    python main.py              # Opens CLI
    python main.py [args...]    # Pass arguments to CLI
    summeets [args...]          # Via installed package
"""

import sys


def main():
    """Main entry point that launches the CLI."""
    try:
        from cli.app import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"Error: Could not import CLI module. {e}")
        print("Make sure you have installed the package with: pip install -e .")
        sys.exit(1)


if __name__ == "__main__":
    main()
