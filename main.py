#!/usr/bin/env python3
"""
Main entry point for Summeets - Audio Meeting Transcription and Summarization Tool

Usage:
    python main.py          # Opens GUI by default
    python main.py gui      # Explicitly opens GUI
    python main.py cli      # Opens CLI
    python main.py cli [args...]  # Pass arguments to CLI
"""

import sys
import os
from pathlib import Path

def main():
    """Main entry point that routes to GUI or CLI based on arguments."""
    
    # Default to GUI if no arguments provided
    if len(sys.argv) == 1:
        mode = "gui"
    else:
        mode = sys.argv[1].lower()
    
    if mode == "gui":
        # Launch GUI application
        try:
            from gui.app import main as gui_main
            # Remove 'gui' from argv if present
            if len(sys.argv) > 1 and sys.argv[1].lower() == "gui":
                sys.argv.pop(1)
            gui_main()
        except ImportError as e:
            print(f"Error: Could not import GUI module. {e}")
            print("Make sure you have installed the package with: pip install -e .")
            sys.exit(1)
    
    elif mode == "cli":
        # Launch CLI application
        try:
            from cli.app import main as cli_main
            # Remove 'cli' from argv to pass remaining args to CLI
            sys.argv.pop(1) if len(sys.argv) > 1 else None
            cli_main()
        except ImportError as e:
            print(f"Error: Could not import CLI module. {e}")
            print("Make sure you have installed the package with: pip install -e .")
            sys.exit(1)
    
    elif mode in ["--help", "-h", "help"]:
        print(__doc__)
        sys.exit(0)
    
    else:
        # Assume it's a CLI command, insert 'cli' and let CLI handle it
        sys.argv.insert(1, "cli")
        try:
            from cli.app import main as cli_main
            sys.argv.pop(1)  # Remove the inserted 'cli'
            cli_main()
        except ImportError as e:
            print(f"Error: Could not import CLI module. {e}")
            print("Make sure you have installed the package with: pip install -e .")
            sys.exit(1)

if __name__ == "__main__":
    main()