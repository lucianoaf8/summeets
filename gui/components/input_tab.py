#!/usr/bin/env python3
"""Input tab component for file selection and configuration."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Any, Dict, Optional
import queue

from .base_component import BaseTabComponent
from ..constants import *


class InputTab(BaseTabComponent):
    """File input and selection tab component."""
    
    def __init__(self, parent_notebook: ttk.Notebook, message_queue: queue.Queue):
        self.selected_file: Optional[Path] = None
        self.file_info_text: Optional[tk.Text] = None
        self.file_path_label: Optional[ttk.Label] = None
        self.process_buttons_frame: Optional[ttk.Frame] = None
        
        super().__init__(parent_notebook, TAB_INPUT, message_queue)
    
    def setup_ui(self) -> None:
        """Setup the input tab UI elements."""
        # File selection section
        self._create_file_selection_section()
        
        # File information section  
        self._create_file_info_section()
        
        # Processing options section
        self._create_processing_options_section()
        
        # Action buttons
        self._create_action_buttons()
    
    def _create_file_selection_section(self) -> None:
        """Create the file selection section."""
        section = self.create_section(self.frame, "📁 File Selection")
        
        # File path display
        path_frame = ttk.Frame(section)
        path_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        ttk.Label(path_frame, text="Selected file:", font=SECONDARY_FONT).pack(anchor='w')
        self.file_path_label = ttk.Label(
            path_frame, 
            text=STATUS_NO_FILE,
            font=INFO_FONT,
            foreground=COLORS['text_secondary']
        )
        self.file_path_label.pack(anchor='w', pady=(DEFAULT_PADY, 0))
        
        # File selection button
        button_frame = ttk.Frame(section)
        button_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        open_btn = ttk.Button(
            button_frame,
            text=BTN_OPEN_FILE,
            command=self._open_file_dialog,
            style='primary.TButton'
        )
        open_btn.pack(side='left')
        
        # Quick access buttons
        quick_frame = ttk.Frame(button_frame)
        quick_frame.pack(side='right')
        
        ttk.Button(
            quick_frame,
            text="📋 Paste Path",
            command=self._paste_file_path
        ).pack(side='left', padx=(DEFAULT_PADX, 0))
        
        ttk.Button(
            quick_frame,
            text="🔄 Refresh",
            command=self._refresh_file_info
        ).pack(side='left', padx=(DEFAULT_PADX, 0))
    
    def _create_file_info_section(self) -> None:
        """Create the file information display section."""
        section = self.create_section(self.frame, "ℹ️ File Information")
        
        # Scrolled text for file info
        self.file_info_text = tk.Text(
            section,
            height=FILE_INFO_HEIGHT,
            wrap='word',
            font=INFO_FONT,
            state='disabled',
            background=COLORS['bg_secondary'],
            relief='flat'
        )
        self.file_info_text.pack(fill='both', expand=True, pady=DEFAULT_PADY)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(section, orient='vertical', command=self.file_info_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.file_info_text.configure(yscrollcommand=scrollbar.set)
        
        # Initial message
        self._update_file_info("No file selected. Choose a media file to see details.")
    
    def _create_processing_options_section(self) -> None:
        """Create processing options section."""
        section = self.create_section(self.frame, "⚙️ Processing Options")
        
        # Audio processing options
        audio_frame = ttk.LabelFrame(section, text="Audio Processing")
        audio_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        self.normalize_audio_var = tk.BooleanVar(value=NORMALIZE_AUDIO_DEFAULT)
        self.extract_audio_var = tk.BooleanVar(value=EXTRACT_AUDIO_DEFAULT)
        
        ttk.Checkbutton(
            audio_frame,
            text="Normalize audio levels",
            variable=self.normalize_audio_var,
            command=self._on_option_changed
        ).pack(anchor='w', padx=DEFAULT_PADX, pady=DEFAULT_PADY)
        
        ttk.Checkbutton(
            audio_frame,
            text="Extract audio from video files",
            variable=self.extract_audio_var,
            command=self._on_option_changed
        ).pack(anchor='w', padx=DEFAULT_PADX, pady=DEFAULT_PADY)
        
        # Output format
        format_frame = ttk.Frame(audio_frame)
        format_frame.pack(fill='x', padx=DEFAULT_PADX, pady=DEFAULT_PADY)
        
        ttk.Label(format_frame, text="Audio output:").pack(side='left')
        self.audio_output_var = tk.StringVar(value=AUDIO_OUTPUT_DEFAULT)
        format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.audio_output_var,
            values=["Best", "M4A", "FLAC", "WAV"],
            state='readonly',
            width=10
        )
        format_combo.pack(side='left', padx=(DEFAULT_PADX, 0))
        format_combo.bind('<<ComboboxSelected>>', lambda e: self._on_option_changed())
    
    def _create_action_buttons(self) -> None:
        """Create the main action buttons."""
        self.process_buttons_frame = ttk.Frame(self.frame)
        self.process_buttons_frame.pack(fill='x', padx=SECTION_PADX, pady=SECTION_PADY)
        
        # Primary action buttons
        primary_frame = ttk.Frame(self.process_buttons_frame)
        primary_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        self.process_all_btn = ttk.Button(
            primary_frame,
            text=BTN_PROCESS_ALL,
            command=self._process_all,
            style='success.TButton'
        )
        self.process_all_btn.pack(side='left', fill='x', expand=True)
        
        # Individual processing buttons
        individual_frame = ttk.Frame(self.process_buttons_frame)
        individual_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        self.transcribe_btn = ttk.Button(
            individual_frame,
            text=BTN_TRANSCRIBE_ONLY,
            command=self._transcribe_only,
            style='primary.TButton'
        )
        self.transcribe_btn.pack(side='left', fill='x', expand=True, padx=(0, DEFAULT_PADX))
        
        self.summarize_btn = ttk.Button(
            individual_frame,
            text=BTN_SUMMARIZE_ONLY,
            command=self._summarize_only,
            state='disabled'
        )
        self.summarize_btn.pack(side='left', fill='x', expand=True)
        
        # Initially disable all process buttons
        self._update_button_states(False)
    
    def _open_file_dialog(self) -> None:
        """Open file selection dialog."""
        filename = filedialog.askopenfilename(
            title="Select media file",
            filetypes=MEDIA_FILE_TYPES
        )
        
        if filename:
            self._set_selected_file(filename)
    
    def _paste_file_path(self) -> None:
        """Paste file path from clipboard."""
        try:
            clipboard_text = self.frame.clipboard_get()
            path = Path(clipboard_text.strip())
            if path.exists() and path.is_file():
                self._set_selected_file(str(path))
            else:
                self.show_error("Invalid Path", "The path in clipboard is not a valid file.")
        except tk.TclError:
            self.show_error("Clipboard Error", "Could not read from clipboard.")
        except Exception as e:
            self.show_error("Error", f"Failed to process clipboard content: {str(e)}")
    
    def _set_selected_file(self, file_path: str) -> None:
        """Set the selected file and update UI."""
        try:
            path = Path(file_path)
            if not path.exists():
                self.show_error("File Not Found", f"The selected file does not exist:\n{file_path}")
                return
            
            self.selected_file = path
            self.file_path_label.configure(
                text=str(path),
                foreground=COLORS['text']
            )
            
            # Update file info
            self._display_file_info()
            
            # Enable processing buttons
            self._update_button_states(True)
            
            # Notify other components
            self.send_message('file_selected', {
                'path': str(path),
                'name': path.name,
                'processing_options': self._get_processing_options()
            })
            
        except Exception as e:
            self.show_error("File Selection Error", f"Failed to select file: {str(e)}")
    
    def _display_file_info(self) -> None:
        """Display information about the selected file."""
        if not self.selected_file:
            return
        
        try:
            path = self.selected_file
            stat = path.stat()
            
            # Format file size
            size_mb = stat.st_size / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB" if size_mb > 1 else f"{stat.st_size:,} bytes"
            
            # File info text
            info_lines = [
                f"📁 Name: {path.name}",
                f"📍 Location: {path.parent}",
                f"📊 Size: {size_str}",
                f"📅 Modified: {stat.st_mtime}",
                f"🎵 Format: {path.suffix.upper()}",
                "",
                f"✅ File is ready for processing"
            ]
            
            # Check if it's a supported format
            if path.suffix.lower() not in ALL_MEDIA_FORMATS:
                info_lines.append("⚠️ Warning: Unsupported file format")
            
            self._update_file_info("\n".join(info_lines))
            
        except Exception as e:
            self._update_file_info(f"❌ Error reading file information: {str(e)}")
    
    def _refresh_file_info(self) -> None:
        """Refresh file information display."""
        if self.selected_file:
            self._display_file_info()
        else:
            self.show_info("No File Selected", "Please select a file first.")
    
    def _update_file_info(self, text: str) -> None:
        """Update the file info text widget."""
        if self.file_info_text:
            self.file_info_text.configure(state='normal')
            self.file_info_text.delete(1.0, 'end')
            self.file_info_text.insert(1.0, text)
            self.file_info_text.configure(state='disabled')
    
    def _update_button_states(self, enabled: bool) -> None:
        """Update the state of processing buttons."""
        state = 'normal' if enabled else 'disabled'
        if hasattr(self, 'process_all_btn'):
            self.process_all_btn.configure(state=state)
        if hasattr(self, 'transcribe_btn'):
            self.transcribe_btn.configure(state=state)
        # Summarize button handled separately based on transcript availability
    
    def _get_processing_options(self) -> Dict[str, Any]:
        """Get current processing options."""
        return {
            'normalize_audio': self.normalize_audio_var.get(),
            'extract_audio': self.extract_audio_var.get(),
            'audio_output': self.audio_output_var.get()
        }
    
    def _on_option_changed(self) -> None:
        """Handle processing option changes."""
        if self.selected_file:
            self.send_message('options_changed', self._get_processing_options())
    
    def _process_all(self) -> None:
        """Start complete processing (transcribe + summarize)."""
        if not self.selected_file:
            self.show_error("No File Selected", "Please select a file to process.")
            return
        
        self.send_message('process_all', {
            'file_path': str(self.selected_file),
            'options': self._get_processing_options()
        })
    
    def _transcribe_only(self) -> None:
        """Start transcription only."""
        if not self.selected_file:
            self.show_error("No File Selected", "Please select a file to transcribe.")
            return
        
        self.send_message('transcribe_only', {
            'file_path': str(self.selected_file),
            'options': self._get_processing_options()
        })
    
    def _summarize_only(self) -> None:
        """Start summarization only."""
        self.send_message('summarize_only', {})
    
    def update_state(self, state: Dict[str, Any]) -> None:
        """Update component state based on external changes."""
        if 'processing_active' in state:
            # Disable/enable controls during processing
            if state['processing_active']:
                self.disable()
            else:
                self.enable()
        
        if 'transcript_available' in state:
            # Enable summarize button if transcript is available
            self.summarize_btn.configure(
                state='normal' if state['transcript_available'] else 'disabled'
            )
    
    def get_selected_file(self) -> Optional[Path]:
        """Get the currently selected file."""
        return self.selected_file