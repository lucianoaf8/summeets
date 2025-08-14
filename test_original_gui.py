#!/usr/bin/env python3
"""
Test script to verify the original GUI still works.
"""

import tkinter as tk
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_original_gui():
    """Test the original GUI to ensure it still works."""
    print("🚀 Testing original GUI...")
    
    try:
        from gui.app import SummeetsGUI
        print("✅ Successfully imported original GUI")
        
        # Create root window
        root = tk.Tk()
        
        # Initialize the original GUI
        app = SummeetsGUI(root)
        
        print("✅ Original GUI initialized successfully!")
        print("📝 Original monolithic GUI is working")
        print("🔄 Close the window to end the test.")
        
        # Start the GUI (will block until window is closed)
        root.mainloop()
        
        print("✅ Original GUI test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during original GUI test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_original_gui()
    sys.exit(0 if success else 1)