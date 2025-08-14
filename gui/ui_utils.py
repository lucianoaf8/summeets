#!/usr/bin/env python3
"""Common UI utilities and helper functions for the GUI."""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from .constants import *


class StyleManager:
    """Manages consistent styling across the application."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.style = ttk.Style()
        self._setup_styles()
    
    def _setup_styles(self) -> None:
        """Setup custom styles for the application."""
        # Use modern theme
        self.style.theme_use('clam')
        
        # Configure button styles
        self.style.configure(
            'primary.TButton',
            background=COLORS['primary'],
            foreground='white',
            focuscolor='none'
        )
        
        self.style.map('primary.TButton',
            background=[('active', COLORS['primary_hover'])]
        )
        
        self.style.configure(
            'success.TButton',
            background=COLORS['success'],
            foreground='white',
            focuscolor='none'
        )
        
        self.style.configure(
            'danger.TButton',
            background=COLORS['danger'],
            foreground='white',
            focuscolor='none'
        )
        
        self.style.configure(
            'warning.TButton',
            background=COLORS['warning'],
            foreground='white',
            focuscolor='none'
        )
        
        # Progress bar styles
        self.style.configure(
            'success.Horizontal.TProgressbar',
            background=COLORS['success']
        )
        
        # Notebook tab styles
        self.style.configure(
            'TNotebook.Tab',
            padding=[12, 8],
            focuscolor='none'
        )
    
    def get_style(self) -> ttk.Style:
        """Get the configured style object."""
        return self.style


class ValidationHelper:
    """Helper class for input validation."""
    
    @staticmethod
    def validate_file_path(path_str: str) -> Tuple[bool, str]:
        """Validate a file path.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not path_str.strip():
            return False, "Path cannot be empty"
        
        try:
            path = Path(path_str)
            
            # Check for directory traversal
            if '..' in path.parts:
                return False, "Directory traversal not allowed"
            
            # Check if file exists
            if not path.exists():
                return False, f"File does not exist: {path_str}"
            
            # Check if it's actually a file
            if not path.is_file():
                return False, f"Path is not a file: {path_str}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Invalid path: {str(e)}"
    
    @staticmethod
    def validate_api_key(key: str, provider: str) -> Tuple[bool, str]:
        """Validate an API key format.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not key.strip():
            return False, f"{provider} API key cannot be empty"
        
        key = key.strip()
        
        # Provider-specific validation
        if provider == 'openai':
            if not key.startswith('sk-'):
                return False, "OpenAI API keys must start with 'sk-'"
            if len(key) < 20:
                return False, "OpenAI API key appears too short"
                
        elif provider == 'anthropic':
            if not key.startswith('sk-ant-'):
                return False, "Anthropic API keys must start with 'sk-ant-'"
            if len(key) < 30:
                return False, "Anthropic API key appears too short"
                
        elif provider == 'replicate':
            if not key.startswith('r8_'):
                return False, "Replicate tokens must start with 'r8_'"
            if len(key) < 20:
                return False, "Replicate token appears too short"
        
        return True, ""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize a filename for safe file operations."""
        import re
        
        # Remove invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove control characters
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32)
        
        # Limit length
        if len(sanitized) > 200:
            name, ext = Path(sanitized).stem, Path(sanitized).suffix
            sanitized = name[:200-len(ext)] + ext
        
        return sanitized


class MessageFormatter:
    """Helper class for formatting various message types."""
    
    @staticmethod
    def format_file_info(file_path: Path) -> str:
        """Format file information for display."""
        try:
            stat = file_path.stat()
            size_mb = stat.st_size / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB" if size_mb > 1 else f"{stat.st_size:,} bytes"
            
            return f"""📁 Name: {file_path.name}
📍 Location: {file_path.parent}
📊 Size: {size_str}
🎵 Format: {file_path.suffix.upper()}
✅ Ready for processing"""
            
        except Exception as e:
            return f"❌ Error reading file information: {str(e)}"
    
    @staticmethod
    def format_error_message(error: Exception, context: str = "") -> str:
        """Format error messages consistently."""
        error_type = type(error).__name__
        error_msg = str(error)
        
        formatted = f"❌ {error_type}: {error_msg}"
        if context:
            formatted = f"{context}\n\n{formatted}"
        
        return formatted
    
    @staticmethod
    def format_processing_time(seconds: float) -> str:
        """Format processing time in a human-readable way."""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"


class WidgetHelpers:
    """Helper functions for creating common widget patterns."""
    
    @staticmethod
    def create_labeled_entry(parent: tk.Widget, label_text: str, 
                           textvariable: tk.Variable, width: int = ENTRY_WIDTH,
                           **kwargs) -> Tuple[ttk.Frame, ttk.Label, ttk.Entry]:
        """Create a labeled entry widget.
        
        Returns:
            Tuple of (container_frame, label, entry)
        """
        frame = ttk.Frame(parent)
        
        label = ttk.Label(frame, text=label_text, width=12)
        label.pack(side='left')
        
        entry = ttk.Entry(frame, textvariable=textvariable, width=width, **kwargs)
        entry.pack(side='left', padx=(DEFAULT_PADX, 0), fill='x', expand=True)
        
        return frame, label, entry
    
    @staticmethod
    def create_labeled_combobox(parent: tk.Widget, label_text: str,
                               textvariable: tk.Variable, values: list,
                               width: int = 15, **kwargs) -> Tuple[ttk.Frame, ttk.Label, ttk.Combobox]:
        """Create a labeled combobox widget.
        
        Returns:
            Tuple of (container_frame, label, combobox)
        """
        frame = ttk.Frame(parent)
        
        label = ttk.Label(frame, text=label_text, width=12)
        label.pack(side='left')
        
        combobox = ttk.Combobox(
            frame, 
            textvariable=textvariable, 
            values=values,
            width=width,
            state='readonly',
            **kwargs
        )
        combobox.pack(side='left', padx=(DEFAULT_PADX, 0))
        
        return frame, label, combobox
    
    @staticmethod
    def create_labeled_spinbox(parent: tk.Widget, label_text: str,
                              textvariable: tk.Variable, from_: int, to: int,
                              increment: int = 1, width: int = SPINBOX_WIDTH,
                              **kwargs) -> Tuple[ttk.Frame, ttk.Label, tk.Spinbox]:
        """Create a labeled spinbox widget.
        
        Returns:
            Tuple of (container_frame, label, spinbox)
        """
        frame = ttk.Frame(parent)
        
        label = ttk.Label(frame, text=label_text, width=12)
        label.pack(side='left')
        
        spinbox = tk.Spinbox(
            frame,
            textvariable=textvariable,
            from_=from_,
            to=to,
            increment=increment,
            width=width,
            **kwargs
        )
        spinbox.pack(side='left', padx=(DEFAULT_PADX, 0))
        
        return frame, label, spinbox
    
    @staticmethod
    def create_button_row(parent: tk.Widget, button_configs: list,
                         fill: str = 'x') -> ttk.Frame:
        """Create a row of buttons.
        
        Args:
            button_configs: List of dicts with keys: text, command, style (optional)
        """
        frame = ttk.Frame(parent)
        frame.pack(fill=fill, pady=DEFAULT_PADY)
        
        for i, config in enumerate(button_configs):
            btn_kwargs = {
                'text': config['text'],
                'command': config['command']
            }
            
            if 'style' in config:
                btn_kwargs['style'] = config['style']
            
            if 'state' in config:
                btn_kwargs['state'] = config['state']
            
            btn = ttk.Button(frame, **btn_kwargs)
            
            if config.get('expand', False):
                btn.pack(side='left', fill='x', expand=True, 
                        padx=(0 if i == 0 else DEFAULT_PADX, 0))
            else:
                btn.pack(side='left', padx=(0 if i == 0 else DEFAULT_PADX, 0))
        
        return frame
    
    @staticmethod
    def create_info_text(parent: tk.Widget, text: str, 
                        font: tuple = INFO_FONT,
                        color: str = COLORS['text_secondary']) -> ttk.Label:
        """Create an info text label."""
        return ttk.Label(
            parent,
            text=text,
            font=font,
            foreground=color,
            wraplength=DEFAULT_WRAP_LENGTH
        )


class ClipboardHelper:
    """Helper for clipboard operations."""
    
    @staticmethod
    def copy_text(root: tk.Tk, text: str) -> bool:
        """Copy text to clipboard.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            root.clipboard_clear()
            root.clipboard_append(text)
            return True
        except tk.TclError:
            return False
    
    @staticmethod
    def get_clipboard_text(root: tk.Tk) -> Optional[str]:
        """Get text from clipboard.
        
        Returns:
            Clipboard text or None if error
        """
        try:
            return root.clipboard_get()
        except tk.TclError:
            return None


class FileDialogHelper:
    """Helper for consistent file dialogs."""
    
    @staticmethod
    def open_media_file(title: str = "Select Media File") -> Optional[str]:
        """Open dialog for selecting media files."""
        from tkinter import filedialog
        
        return filedialog.askopenfilename(
            title=title,
            filetypes=MEDIA_FILE_TYPES
        )
    
    @staticmethod
    def save_json_file(title: str = "Save JSON File", 
                      default_name: str = "") -> Optional[str]:
        """Save dialog for JSON files."""
        from tkinter import filedialog
        
        return filedialog.asksaveasfilename(
            title=title,
            defaultextension=".json",
            filetypes=EXPORT_JSON_TYPES,
            initialvalue=default_name
        )
    
    @staticmethod
    def save_text_file(title: str = "Save Text File",
                      default_name: str = "",
                      extension: str = ".txt") -> Optional[str]:
        """Save dialog for text files."""
        from tkinter import filedialog
        
        filetypes = [("Text files", f"*{extension}"), ("All files", "*.*")]
        
        return filedialog.asksaveasfilename(
            title=title,
            defaultextension=extension,
            filetypes=filetypes,
            initialvalue=default_name
        )