#!/usr/bin/env python3
"""
Test script for the new modular GUI implementation.
"""

import tkinter as tk
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from gui.app_new import SummeetsGUIModular
    print("✅ Successfully imported modular GUI components")
except ImportError as e:
    print(f"❌ Failed to import modular GUI: {e}")
    sys.exit(1)

def test_gui():
    """Test the modular GUI."""
    print("🚀 Starting modular GUI test...")
    
    try:
        # Create root window
        root = tk.Tk()
        
        # Initialize the modular GUI
        app = SummeetsGUIModular(root)
        
        print("✅ GUI initialized successfully!")
        print("📝 The GUI should now be running with the following tabs:")
        print("   - Input: File selection and processing options")
        print("   - Processing: Progress monitoring and control")
        print("   - Results: Transcript and summary display")
        print("   - Configuration: Settings and API keys")
        print()
        print("💡 Try selecting a file and testing the interface!")
        print("🔄 Close the window to end the test.")
        
        # Start the GUI
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Error during GUI test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("✅ GUI test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_gui()
    sys.exit(0 if success else 1)