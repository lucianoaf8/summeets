#!/usr/bin/env python3
"""Processing tab component for monitoring and controlling operations."""
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Any, Dict, List
import queue
from datetime import datetime

from .base_component import BaseTabComponent  
from ..constants import *


class ProcessingTab(BaseTabComponent):
    """Processing control and monitoring tab component."""
    
    def __init__(self, parent_notebook: ttk.Notebook, message_queue: queue.Queue):
        # Task management
        self.remaining_tasks: List[str] = DEFAULT_INITIAL_TASKS.copy()
        self.completed_tasks: List[str] = []
        
        # UI elements
        self.progress_bar: Optional[ttk.Progressbar] = None
        self.status_label: Optional[ttk.Label] = None
        self.task_listbox: Optional[tk.Listbox] = None
        self.log_text: Optional[scrolledtext.ScrolledText] = None
        self.control_buttons_frame: Optional[ttk.Frame] = None
        
        # Processing state
        self.is_processing = False
        self.current_task = ""
        self.progress_value = 0.0
        
        super().__init__(parent_notebook, TAB_PROCESSING, message_queue)
    
    def setup_ui(self) -> None:
        """Setup the processing tab UI elements."""
        # Progress section
        self._create_progress_section()
        
        # Task list section
        self._create_task_section()
        
        # Control buttons
        self._create_control_section()
        
        # Log section
        self._create_log_section()
        
        # Initialize task display
        self._update_task_display()
    
    def _create_progress_section(self) -> None:
        """Create the progress monitoring section."""
        section = self.create_section(self.frame, "⚡ Progress")
        
        # Status label
        self.status_label = ttk.Label(
            section,
            text=STATUS_READY,
            font=HEADING_FONT,
            foreground=COLORS['success']
        )
        self.status_label.pack(anchor='w', pady=DEFAULT_PADY)
        
        # Progress bar
        progress_frame = ttk.Frame(section)
        progress_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            length=PROGRESS_BAR_LENGTH,
            mode='determinate',
            style='success.Horizontal.TProgressbar'
        )
        self.progress_bar.pack(side='left', fill='x', expand=True)
        
        # Progress percentage
        self.progress_label = ttk.Label(
            progress_frame,
            text="0%",
            font=SECONDARY_FONT
        )
        self.progress_label.pack(side='right', padx=(DEFAULT_PADX, 0))
    
    def _create_task_section(self) -> None:
        """Create the task monitoring section."""
        section = self.create_section(self.frame, "📋 Tasks")
        
        # Task listbox with scrollbar
        task_frame = ttk.Frame(section)
        task_frame.pack(fill='both', expand=True, pady=DEFAULT_PADY)
        
        self.task_listbox = tk.Listbox(
            task_frame,
            height=LISTBOX_HEIGHT,
            font=LISTBOX_FONT,
            selectmode='none',
            relief='flat',
            background=COLORS['bg_secondary']
        )
        self.task_listbox.pack(side='left', fill='both', expand=True)
        
        # Scrollbar for task list
        task_scrollbar = ttk.Scrollbar(
            task_frame,
            orient='vertical',
            command=self.task_listbox.yview
        )
        task_scrollbar.pack(side='right', fill='y')
        self.task_listbox.configure(yscrollcommand=task_scrollbar.set)
    
    def _create_control_section(self) -> None:
        """Create the processing control buttons."""
        self.control_buttons_frame = ttk.Frame(self.frame)
        self.control_buttons_frame.pack(fill='x', padx=SECTION_PADX, pady=SECTION_PADY)
        
        # Control buttons
        self.cancel_btn = ttk.Button(
            self.control_buttons_frame,
            text="⏹️ Cancel",
            command=self._cancel_processing,
            state='disabled',
            style='danger.TButton'
        )
        self.cancel_btn.pack(side='left')
        
        self.pause_btn = ttk.Button(
            self.control_buttons_frame,
            text="⏸️ Pause",
            command=self._pause_processing,
            state='disabled'
        )
        self.pause_btn.pack(side='left', padx=(DEFAULT_PADX, 0))
        
        # Utility buttons on the right
        utility_frame = ttk.Frame(self.control_buttons_frame)
        utility_frame.pack(side='right')
        
        ttk.Button(
            utility_frame,
            text="🔄 Reset",
            command=self._reset_tasks
        ).pack(side='left')
        
        ttk.Button(
            utility_frame,
            text="📋 Copy Log",
            command=self._copy_log
        ).pack(side='left', padx=(DEFAULT_PADX, 0))
    
    def _create_log_section(self) -> None:
        """Create the processing log section."""
        section = self.create_section(self.frame, "📄 Processing Log")
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(
            section,
            height=LOG_TEXT_HEIGHT,
            wrap='word',
            font=INFO_FONT,
            state='disabled',
            background=COLORS['bg_secondary']
        )
        self.log_text.pack(fill='both', expand=True, pady=DEFAULT_PADY)
        
        # Add initial log entry
        self._add_log_entry("System ready. Waiting for file selection...")
    
    def _update_task_display(self) -> None:
        """Update the task list display."""
        if not self.task_listbox:
            return
        
        self.task_listbox.delete(0, 'end')
        
        # Add completed tasks with checkmark
        for task in self.completed_tasks:
            self.task_listbox.insert('end', f"✅ {task}")
            self.task_listbox.itemconfig('end', foreground=COLORS['success'])
        
        # Add remaining tasks
        for i, task in enumerate(self.remaining_tasks):
            if i == 0 and self.is_processing:
                # Current task - highlight
                self.task_listbox.insert('end', f"⏳ {task}")
                self.task_listbox.itemconfig('end', foreground=COLORS['primary'])
            else:
                self.task_listbox.insert('end', f"⏸️ {task}")
                self.task_listbox.itemconfig('end', foreground=COLORS['text_secondary'])
    
    def _add_log_entry(self, message: str, level: str = "INFO") -> None:
        """Add an entry to the processing log."""
        if not self.log_text:
            return
        
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        
        # Color based on log level
        color = COLORS['text']
        if level == "ERROR":
            color = COLORS['danger']
        elif level == "WARNING":
            color = COLORS['warning']
        elif level == "SUCCESS":
            color = COLORS['success']
        
        # Add to log
        self.log_text.configure(state='normal')
        log_line = f"[{timestamp}] {level}: {message}\n"
        self.log_text.insert('end', log_line)
        self.log_text.configure(state='disabled')
        self.log_text.see('end')  # Auto-scroll to bottom
    
    def _cancel_processing(self) -> None:
        """Cancel the current processing operation."""
        if self.confirm_action("Cancel Processing", "Are you sure you want to cancel the current operation?"):
            self.send_message('cancel_processing', {})
            self._add_log_entry("Processing cancelled by user", "WARNING")
    
    def _pause_processing(self) -> None:
        """Pause/resume the current processing operation."""
        if self.is_processing:
            self.send_message('pause_processing', {})
            self.pause_btn.configure(text="▶️ Resume")
            self._add_log_entry("Processing paused", "INFO")
        else:
            self.send_message('resume_processing', {})
            self.pause_btn.configure(text="⏸️ Pause")
            self._add_log_entry("Processing resumed", "INFO")
    
    def _reset_tasks(self) -> None:
        """Reset the task list to initial state."""
        if self.confirm_action("Reset Tasks", "This will reset the task list. Continue?"):
            self.remaining_tasks = DEFAULT_INITIAL_TASKS.copy()
            self.completed_tasks = []
            self.progress_value = 0.0
            self.is_processing = False
            
            self._update_progress(0.0, STATUS_READY)
            self._update_task_display()
            self._add_log_entry("Task list reset", "INFO")
    
    def _copy_log(self) -> None:
        """Copy the log content to clipboard."""
        if self.log_text:
            log_content = self.log_text.get(1.0, 'end-1c')
            self.frame.clipboard_clear()
            self.frame.clipboard_append(log_content)
            self.show_info("Log Copied", "Processing log copied to clipboard.")
    
    def start_processing(self, process_type: str, tasks: List[str]) -> None:
        """Start a new processing operation."""
        self.is_processing = True
        self.remaining_tasks = tasks.copy()
        self.completed_tasks = []
        self.progress_value = 0.0
        
        # Update UI
        self._update_progress(0.0, f"Starting {process_type}...")
        self._update_task_display()
        self._update_control_buttons(True)
        
        self._add_log_entry(f"Started {process_type} with {len(tasks)} tasks", "INFO")
    
    def complete_task(self, task: str) -> None:
        """Mark a task as completed."""
        if task in self.remaining_tasks:
            self.remaining_tasks.remove(task)
            self.completed_tasks.append(task)
            
            # Update progress
            total_tasks = len(self.remaining_tasks) + len(self.completed_tasks)
            if total_tasks > 0:
                progress = (len(self.completed_tasks) / total_tasks) * 100
                self._update_progress(progress, f"Completed: {task}")
            
            self._update_task_display()
            self._add_log_entry(f"Completed task: {task}", "SUCCESS")
    
    def fail_task(self, task: str, error: str) -> None:
        """Mark a task as failed."""
        self.is_processing = False
        self._update_progress(self.progress_value, STATUS_ERROR)
        self._update_control_buttons(False)
        
        self._add_log_entry(f"Task failed: {task} - {error}", "ERROR")
    
    def finish_processing(self, success: bool = True) -> None:
        """Complete the processing operation."""
        self.is_processing = False
        
        if success:
            self._update_progress(100.0, STATUS_COMPLETE)
            self._add_log_entry("All tasks completed successfully!", "SUCCESS")
        else:
            self._update_progress(self.progress_value, STATUS_ERROR)
            self._add_log_entry("Processing completed with errors", "ERROR")
        
        self._update_control_buttons(False)
    
    def _update_progress(self, value: float, status: str) -> None:
        """Update progress bar and status."""
        self.progress_value = value
        
        if self.progress_bar:
            self.progress_bar['value'] = value
        
        if self.progress_label:
            self.progress_label.configure(text=PROGRESS_FORMAT.format(value))
        
        if self.status_label:
            # Set color based on status
            color = COLORS['text']
            if status == STATUS_COMPLETE:
                color = COLORS['success']
            elif status == STATUS_ERROR:
                color = COLORS['danger']
            elif "processing" in status.lower():
                color = COLORS['primary']
            
            self.status_label.configure(text=status, foreground=color)
    
    def _update_control_buttons(self, processing: bool) -> None:
        """Update control button states."""
        self.cancel_btn.configure(state='normal' if processing else 'disabled')
        self.pause_btn.configure(state='normal' if processing else 'disabled')
        
        if not processing:
            self.pause_btn.configure(text="⏸️ Pause")
    
    def update_state(self, state: Dict[str, Any]) -> None:
        """Update component state based on external changes."""
        if 'file_selected' in state:
            file_info = state['file_selected']
            # Update tasks based on file type
            if Path(file_info['path']).suffix.lower() in SUPPORTED_VIDEO_FORMATS:
                self.remaining_tasks = VIDEO_PROCESSING_TASKS.copy()
            else:
                self.remaining_tasks = DEFAULT_INITIAL_TASKS.copy()
            
            self._update_task_display()
            self._add_log_entry(f"File selected: {file_info['name']}", "INFO")
        
        if 'processing_progress' in state:
            progress_info = state['processing_progress']
            self._update_progress(progress_info['percentage'], progress_info['status'])
        
        if 'task_completed' in state:
            self.complete_task(state['task_completed'])
        
        if 'task_failed' in state:
            task_info = state['task_failed']
            self.fail_task(task_info['task'], task_info['error'])
        
        if 'processing_finished' in state:
            self.finish_processing(state['processing_finished'].get('success', True))
        
        if 'log_message' in state:
            log_info = state['log_message']
            self._add_log_entry(log_info['message'], log_info.get('level', 'INFO'))
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current processing status."""
        return {
            'is_processing': self.is_processing,
            'progress': self.progress_value,
            'completed_tasks': len(self.completed_tasks),
            'remaining_tasks': len(self.remaining_tasks),
            'current_task': self.remaining_tasks[0] if self.remaining_tasks else None
        }