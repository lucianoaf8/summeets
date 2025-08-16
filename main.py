#!/usr/bin/env python3
"""
Main entry point for Summeets - Audio Meeting Transcription and Summarization Tool

Usage:
    python main.py          # Opens Electron GUI by default
    python main.py gui      # Explicitly opens Electron GUI
    python main.py cli      # Opens CLI
    python main.py cli [args...]  # Pass arguments to CLI
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path

def main():
    """Main entry point that routes to Electron GUI or CLI based on arguments."""
    
    # Default to GUI if no arguments provided
    if len(sys.argv) == 1:
        mode = "gui"
    else:
        mode = sys.argv[1].lower()
    
    if mode == "gui":
        # Launch Electron GUI application
        try:
            # Check if npm is available (Windows-compatible)
            npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
            if not shutil.which(npm_cmd):
                print("Error: npm is required to run the GUI.")
                print("Please install Node.js and npm from https://nodejs.org/")
                print("Make sure to restart your terminal after installation.")
                sys.exit(1)
            
            # Check if we're in the project directory with package.json
            project_root = Path(__file__).parent
            package_json = project_root / "package.json"
            
            if not package_json.exists():
                print("Error: package.json not found. Please run from the project root directory.")
                sys.exit(1)
            
            print("Starting Summeets Electron GUI...")
            
            # Change to project directory and start Electron
            os.chdir(project_root)
            
            # First install dependencies if node_modules doesn't exist
            node_modules = project_root / "node_modules"
            if not node_modules.exists():
                print("Installing Node.js dependencies...")
                result = subprocess.run([npm_cmd, "install"], capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"Error installing dependencies: {result.stderr}")
                    sys.exit(1)
                print("Dependencies installed successfully.")
            
            # Start the Electron app
            print("Launching Electron application...")
            subprocess.run([npm_cmd, "start"], check=True)
            
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to start Electron GUI. {e}")
            print("Make sure Node.js and npm are installed.")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nGUI application terminated by user.")
            sys.exit(0)
    
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
        print("\nAdditional Information:")
        print("  GUI: Launches the Electron-based graphical interface")
        print("  CLI: Command-line interface for automated processing")
        print("\nRequirements:")
        print("  GUI: Node.js and npm must be installed")
        print("  CLI: Python package installed with 'pip install -e .'")
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