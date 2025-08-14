#!/usr/bin/env python3
"""Base component class for all GUI tab components."""
import tkinter as tk
from tkinter import ttk
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional
import queue
from ..constants import *


class BaseTabComponent(ABC):
    """Abstract base class for all tab components."""
    
    def __init__(self, parent_notebook: ttk.Notebook, title: str, message_queue: queue.Queue):
        """Initialize base component.
        
        Args:
            parent_notebook: The parent notebook widget
            title: Tab title to display
            message_queue: Queue for cross-component communication
        """
        self.parent_notebook = parent_notebook
        self.title = title
        self.message_queue = message_queue
        
        # Create the main frame for this tab
        self.frame = ttk.Frame(parent_notebook)
        parent_notebook.add(self.frame, text=title)
        
        # Event callbacks - can be set by main GUI
        self.on_file_selected: Optional[Callable[[str], None]] = None
        self.on_config_changed: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_process_started: Optional[Callable[[str], None]] = None
        self.on_process_completed: Optional[Callable[[Dict[str, Any]], None]] = None
        
        # Component state
        self._enabled = True
        
        # Setup the component UI
        self.setup_ui()
    
    @abstractmethod
    def setup_ui(self) -> None:
        """Setup the UI elements for this component."""
        pass
    
    @abstractmethod
    def update_state(self, state: Dict[str, Any]) -> None:
        """Update component state based on external changes."""
        pass
    
    def enable(self) -> None:
        """Enable all interactive elements in the component."""
        self._enabled = True
        self._update_widget_states(tk.NORMAL)
    
    def disable(self) -> None:
        """Disable all interactive elements in the component."""
        self._enabled = False
        self._update_widget_states(tk.DISABLED)
    
    def _update_widget_states(self, state: str) -> None:
        """Update state of all child widgets recursively."""
        def update_children(widget):
            for child in widget.winfo_children():
                # Skip certain widget types that don't have state
                if hasattr(child, 'configure') and 'state' in child.configure():
                    try:
                        child.configure(state=state)
                    except tk.TclError:
                        pass  # Some widgets may not support state changes
                update_children(child)
        
        update_children(self.frame)
    
    def send_message(self, message_type: str, data: Any = None) -> None:
        """Send a message to other components via the message queue."""
        message = {
            'type': message_type,
            'source': self.__class__.__name__,
            'data': data
        }
        self.message_queue.put(message)
    
    def create_section(self, parent: tk.Widget, title: str, pady: int = SECTION_PADY) -> ttk.Frame:
        """Create a labeled section frame."""
        section_frame = ttk.Frame(parent)
        section_frame.pack(fill='x', padx=SECTION_PADX, pady=pady)
        
        # Section title
        title_label = ttk.Label(section_frame, text=title, font=HEADING_FONT)
        title_label.pack(anchor='w', padx=DEFAULT_PADX, pady=(DEFAULT_PADY, 0))
        
        # Content frame
        content_frame = ttk.Frame(section_frame)
        content_frame.pack(fill='x', padx=DEFAULT_PADX, pady=DEFAULT_PADY)
        
        return content_frame
    
    def create_button_row(self, parent: tk.Widget, buttons: list) -> ttk.Frame:
        """Create a row of buttons.
        
        Args:
            parent: Parent widget
            buttons: List of tuples (text, command, style)
        """
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        for i, (text, command, style) in enumerate(buttons):
            btn = ttk.Button(button_frame, text=text, command=command, style=style)
            btn.pack(side='left', padx=(0 if i == 0 else DEFAULT_PADX, 0))
        
        return button_frame
    
    def show_error(self, title: str, message: str) -> None:
        """Show error message to user."""
        from tkinter import messagebox
        messagebox.showerror(title, message)
    
    def show_info(self, title: str, message: str) -> None:
        """Show info message to user."""  
        from tkinter import messagebox
        messagebox.showinfo(title, message)
    
    def confirm_action(self, title: str, message: str) -> bool:
        """Show confirmation dialog."""
        from tkinter import messagebox
        return messagebox.askyesno(title, message)