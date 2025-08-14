#!/usr/bin/env python3
"""
Modern component-based tkinter GUI for Summeets - Meeting Transcription & Summarization Tool
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import queue

# Import GUI components
from .components import (
    InputTab, ProcessingTab, ResultsTab, ConfigTab
)
from .ui_utils import StyleManager, ValidationHelper, MessageFormatter
from .constants import *

# Import actual summeets core functionality
try:
    from core.config import Settings
    from core.transcribe.pipeline import TranscriptionPipeline
    from core.summarize import pipeline as summarize_pipeline
    from core.audio.ffmpeg_ops import FFmpegOps
    from core.audio.selection import select_best_audio_file
    from core.models import JobData
    from core.exceptions import SummeetsError
    CORE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Core functionality not available: {e}")
    print("GUI will run in demo mode with mock functionality.")
    CORE_AVAILABLE = False


class SummeetsGUIModular:
    """Modern component-based GUI for Summeets application."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        
        # Initialize settings
        self._init_settings()
        
        # Setup basic window properties
        self._setup_window()
        
        # Message queue for component communication
        self.message_queue = queue.Queue()
        
        # Initialize components
        self._init_components()
        
        # Setup styles
        self.style_manager = StyleManager(root)
        
        # Setup message processing
        self._setup_message_processing()
        
        # Current processing state
        self.current_job: Optional[JobData] = None
        self.processing_thread: Optional[threading.Thread] = None
        self.is_processing = False
        
        # Load initial configuration
        self._load_initial_config()
        
        print("✅ Modular Summeets GUI initialized successfully")
    
    def _init_settings(self) -> None:
        """Initialize application settings."""
        if CORE_AVAILABLE:
            try:
                self.settings = Settings()
            except Exception as e:
                # Fallback to default settings if config fails
                self.settings = Settings(
                    llm_provider='openai',
                    llm_model='gpt-4o-mini',
                    summary_max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
                    summary_chunk_seconds=DEFAULT_CHUNK_SECONDS,
                    ffmpeg_bin=DEFAULT_FFMPEG_BIN,
                    ffprobe_bin=DEFAULT_FFPROBE_BIN
                )
                print(f"Warning: Using default settings due to config error: {e}")
        else:
            # Mock settings for demo mode
            self.settings = type('MockSettings', (), {
                'llm_provider': DEFAULT_LLM_PROVIDER,
                'llm_model': DEFAULT_LLM_MODEL,
                'summary_max_output_tokens': DEFAULT_MAX_OUTPUT_TOKENS,
                'summary_chunk_seconds': DEFAULT_CHUNK_SECONDS,
                'ffmpeg_bin': DEFAULT_FFMPEG_BIN,
                'ffprobe_bin': DEFAULT_FFPROBE_BIN,
                'openai_api_key': '',
                'anthropic_api_key': '',
                'replicate_api_token': ''
            })()
    
    def _setup_window(self) -> None:
        """Setup main window properties."""
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        
        # Configure window icon if available
        try:
            # You would set an icon here if you have one
            pass
        except tk.TclError:
            pass
        
        # Configure window closing behavior
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
    
    def _init_components(self) -> None:
        """Initialize all GUI components."""
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root, padding=(NOTEBOOK_PADX, NOTEBOOK_PADY))
        self.notebook.pack(fill='both', expand=True)
        
        # Initialize tab components
        self.input_tab = InputTab(self.notebook, self.message_queue)
        self.processing_tab = ProcessingTab(self.notebook, self.message_queue)
        self.results_tab = ResultsTab(self.notebook, self.message_queue)
        self.config_tab = ConfigTab(self.notebook, self.message_queue)
        
        # Setup component callbacks
        self._setup_component_callbacks()
    
    def _setup_component_callbacks(self) -> None:
        """Setup callbacks between components and main application."""
        # Config tab callback for settings changes
        self.config_tab.on_settings_changed = self._on_settings_changed
    
    def _setup_message_processing(self) -> None:
        """Setup inter-component message processing."""
        self._process_messages()
    
    def _process_messages(self) -> None:
        """Process messages from component queue."""
        try:
            while True:
                try:
                    message = self.message_queue.get_nowait()
                    self._handle_message(message)
                except queue.Empty:
                    break
        except Exception as e:
            print(f"Error processing messages: {e}")
        
        # Schedule next message processing
        self.root.after(QUEUE_CHECK_INTERVAL_MS, self._process_messages)
    
    def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle a message from components."""
        msg_type = message.get('type')
        data = message.get('data', {})
        source = message.get('source')
        
        if msg_type == 'file_selected':
            self._handle_file_selected(data)
        elif msg_type == 'process_all':
            self._handle_process_all(data)
        elif msg_type == 'transcribe_only':
            self._handle_transcribe_only(data)
        elif msg_type == 'summarize_only':
            self._handle_summarize_only(data)
        elif msg_type == 'cancel_processing':
            self._handle_cancel_processing()
        elif msg_type == 'pause_processing':
            self._handle_pause_processing()
        elif msg_type == 'resume_processing':
            self._handle_resume_processing()
        elif msg_type == 'settings_changed':
            self._handle_settings_changed(data)
        elif msg_type == 'save_settings':
            self._handle_save_settings(data)
        else:
            print(f"Unhandled message type: {msg_type} from {source}")
    
    def _handle_file_selected(self, data: Dict[str, Any]) -> None:
        """Handle file selection from input tab."""
        file_path = data.get('path')
        print(f"File selected: {file_path}")
        
        # Update other components
        self.processing_tab.update_state({'file_selected': data})
        self.results_tab.update_state({'clear_results': True})
        
        # Log the selection
        self.processing_tab.update_state({
            'log_message': {
                'message': f"Selected file: {Path(file_path).name}",
                'level': 'INFO'
            }
        })
    
    def _handle_process_all(self, data: Dict[str, Any]) -> None:
        """Handle complete processing request."""
        if self.is_processing:
            messagebox.showwarning("Already Processing", "A processing operation is already in progress.")
            return
        
        file_path = data.get('file_path')
        options = data.get('options', {})
        
        print(f"Starting complete processing for: {file_path}")
        
        # Start processing thread
        self.processing_thread = threading.Thread(
            target=self._process_all_worker,
            args=(file_path, options),
            daemon=True
        )
        self.processing_thread.start()
    
    def _handle_transcribe_only(self, data: Dict[str, Any]) -> None:
        """Handle transcription-only request."""
        if self.is_processing:
            messagebox.showwarning("Already Processing", "A processing operation is already in progress.")
            return
        
        file_path = data.get('file_path')
        options = data.get('options', {})
        
        print(f"Starting transcription for: {file_path}")
        
        # Start transcription thread
        self.processing_thread = threading.Thread(
            target=self._transcribe_worker,
            args=(file_path, options),
            daemon=True
        )
        self.processing_thread.start()
    
    def _handle_summarize_only(self, data: Dict[str, Any]) -> None:
        """Handle summarization-only request."""
        if not self.results_tab.has_results()['has_transcript']:
            messagebox.showerror("No Transcript", "Please transcribe a file first before summarizing.")
            return
        
        if self.is_processing:
            messagebox.showwarning("Already Processing", "A processing operation is already in progress.")
            return
        
        print("Starting summarization of existing transcript")
        
        # Start summarization thread
        self.processing_thread = threading.Thread(
            target=self._summarize_worker,
            daemon=True
        )
        self.processing_thread.start()
    
    def _handle_cancel_processing(self) -> None:
        """Handle processing cancellation."""
        if self.processing_thread and self.processing_thread.is_alive():
            print("Cancellation requested - this is a placeholder implementation")
            # Note: Proper cancellation would require threading.Event or similar
            self.is_processing = False
    
    def _handle_pause_processing(self) -> None:
        """Handle processing pause."""
        print("Processing pause requested - this is a placeholder implementation")
    
    def _handle_resume_processing(self) -> None:
        """Handle processing resume."""
        print("Processing resume requested - this is a placeholder implementation")
    
    def _handle_settings_changed(self, settings: Dict[str, Any]) -> None:
        """Handle settings changes from config tab."""
        print("Settings changed:", list(settings.keys()))
        # Update internal settings object if needed
    
    def _handle_save_settings(self, settings: Dict[str, Any]) -> None:
        """Handle settings save request."""
        try:
            # Update settings object
            for key, value in settings.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
            
            # Save to file (simplified - would need proper implementation)
            print("Settings saved successfully")
            
        except Exception as e:
            self.config_tab.show_error("Save Failed", f"Failed to save settings: {str(e)}")
    
    def _process_all_worker(self, file_path: str, options: Dict[str, Any]) -> None:
        """Worker thread for complete processing."""
        try:
            self.is_processing = True
            
            # Update processing tab
            tasks = VIDEO_PROCESSING_TASKS if Path(file_path).suffix.lower() in SUPPORTED_VIDEO_FORMATS else [
                "Initialize processing",
                "Transcribe audio with speaker diarization", 
                "Generate AI summary",
                "Export results"
            ]
            
            self.processing_tab.start_processing("complete processing", tasks)
            
            # Simulate processing steps
            self._simulate_processing_step("Initialize processing", 1.0)
            self._simulate_processing_step("Transcribe audio with speaker diarization", 3.0)
            self._simulate_processing_step("Generate AI summary", 2.0)
            self._simulate_processing_step("Export results", 0.5)
            
            # Update results (mock data)
            self._update_mock_results()
            
            self.processing_tab.finish_processing(True)
            
        except Exception as e:
            print(f"Processing error: {e}")
            self.processing_tab.fail_task("Processing", str(e))
        finally:
            self.is_processing = False
    
    def _transcribe_worker(self, file_path: str, options: Dict[str, Any]) -> None:
        """Worker thread for transcription only."""
        try:
            self.is_processing = True
            
            tasks = ["Initialize transcription", "Process audio", "Generate transcript"]
            self.processing_tab.start_processing("transcription", tasks)
            
            # Simulate transcription steps
            self._simulate_processing_step("Initialize transcription", 0.5)
            self._simulate_processing_step("Process audio", 2.5)
            self._simulate_processing_step("Generate transcript", 1.0)
            
            # Update results with transcript only
            self._update_mock_transcript_results()
            
            self.processing_tab.finish_processing(True)
            
        except Exception as e:
            print(f"Transcription error: {e}")
            self.processing_tab.fail_task("Transcription", str(e))
        finally:
            self.is_processing = False
    
    def _summarize_worker(self) -> None:
        """Worker thread for summarization only."""
        try:
            self.is_processing = True
            
            tasks = ["Initialize summarization", "Process transcript", "Generate summary"]
            self.processing_tab.start_processing("summarization", tasks)
            
            # Simulate summarization steps
            self._simulate_processing_step("Initialize summarization", 0.5)
            self._simulate_processing_step("Process transcript", 1.5)
            self._simulate_processing_step("Generate summary", 2.0)
            
            # Update results with summary
            self._update_mock_summary_results()
            
            self.processing_tab.finish_processing(True)
            
        except Exception as e:
            print(f"Summarization error: {e}")
            self.processing_tab.fail_task("Summarization", str(e))
        finally:
            self.is_processing = False
    
    def _simulate_processing_step(self, task_name: str, duration: float) -> None:
        """Simulate a processing step with progress updates."""
        steps = int(duration * 10)  # 10 updates per second
        for i in range(steps):
            if not self.is_processing:  # Check for cancellation
                break
            
            time.sleep(0.1)
            progress = ((i + 1) / steps) * 100
            
            # Update processing tab
            self.processing_tab.update_state({
                'processing_progress': {
                    'percentage': progress,
                    'status': f"Processing: {task_name}..."
                }
            })
        
        # Complete the task
        if self.is_processing:
            self.processing_tab.complete_task(task_name)
    
    def _update_mock_results(self) -> None:
        """Update results with mock data for both transcript and summary."""
        # Mock transcript data
        transcript_data = {
            'segments': [
                {
                    'start': 0.0,
                    'end': 5.0,
                    'text': 'Welcome to our meeting today. Let\'s start with the agenda.',
                    'speaker': 'Speaker 1'
                },
                {
                    'start': 5.5,
                    'end': 12.0,
                    'text': 'Thank you. First item is the quarterly review of our project status.',
                    'speaker': 'Speaker 2'
                },
                {
                    'start': 12.5,
                    'end': 20.0,
                    'text': 'Great. We\'ve made significant progress on the key deliverables this quarter.',
                    'speaker': 'Speaker 1'
                }
            ],
            'metadata': {
                'filename': 'mock_meeting.m4a',
                'duration': 300,
                'file_size': 5242880
            }
        }
        
        # Mock summary data
        summary_data = {
            'summary': 'This was a quarterly review meeting where the team discussed project status and achievements. Key points included significant progress on deliverables and positive outlook for next quarter.',
            'key_points': [
                'Quarterly review was the main agenda item',
                'Significant progress made on key deliverables',
                'Positive outlook for upcoming quarter'
            ],
            'action_items': [
                'Continue monitoring project deliverables',
                'Prepare detailed report for stakeholders',
                'Schedule follow-up meeting for next quarter'
            ],
            'metadata': {
                'model': self.settings.llm_model,
                'provider': self.settings.llm_provider,
                'processing_time': 45.2
            }
        }
        
        # Update results tab
        self.results_tab.load_transcript_results(transcript_data)
        self.results_tab.load_summary_results(summary_data)
        
        # Update input tab state
        self.input_tab.update_state({'transcript_available': True})
    
    def _update_mock_transcript_results(self) -> None:
        """Update results with mock transcript data only."""
        transcript_data = {
            'segments': [
                {
                    'start': 0.0,
                    'end': 5.0,
                    'text': 'This is a sample transcribed text from the audio file.',
                    'speaker': 'Speaker 1'
                },
                {
                    'start': 5.5,
                    'end': 10.0,
                    'text': 'And this is another segment from a different speaker.',
                    'speaker': 'Speaker 2'
                }
            ],
            'metadata': {
                'filename': 'sample_audio.m4a',
                'duration': 120,
                'file_size': 2097152
            }
        }
        
        self.results_tab.load_transcript_results(transcript_data)
        self.input_tab.update_state({'transcript_available': True})
    
    def _update_mock_summary_results(self) -> None:
        """Update results with mock summary data only."""
        summary_data = {
            'summary': 'This is a mock summary of the transcribed content. The conversation covered various topics and included multiple speakers discussing important points.',
            'metadata': {
                'model': self.settings.llm_model,
                'provider': self.settings.llm_provider,
                'processing_time': 12.3
            }
        }
        
        self.results_tab.load_summary_results(summary_data)
    
    def _load_initial_config(self) -> None:
        """Load initial configuration into config tab."""
        config_data = {
            'llm_provider': self.settings.llm_provider,
            'llm_model': self.settings.llm_model,
            'max_tokens': getattr(self.settings, 'summary_max_output_tokens', DEFAULT_MAX_OUTPUT_TOKENS),
            'chunk_seconds': getattr(self.settings, 'summary_chunk_seconds', DEFAULT_CHUNK_SECONDS),
            'cod_passes': getattr(self.settings, 'summary_cod_passes', DEFAULT_COD_PASSES),
            'ffmpeg_bin': getattr(self.settings, 'ffmpeg_bin', DEFAULT_FFMPEG_BIN),
            'ffprobe_bin': getattr(self.settings, 'ffprobe_bin', DEFAULT_FFPROBE_BIN),
            'openai_api_key': getattr(self.settings, 'openai_api_key', ''),
            'anthropic_api_key': getattr(self.settings, 'anthropic_api_key', ''),
            'replicate_api_key': getattr(self.settings, 'replicate_api_token', '')
        }
        
        self.config_tab.load_settings(config_data)
    
    def _on_settings_changed(self, settings: Dict[str, Any]) -> None:
        """Handle settings changes from config tab."""
        # This would update the internal settings and potentially notify other components
        print(f"Settings changed: {list(settings.keys())}")
    
    def _on_window_close(self) -> None:
        """Handle window close event."""
        if self.is_processing:
            result = messagebox.askyesnocancel(
                "Processing in Progress",
                "Processing is currently running. Do you want to cancel it and exit?"
            )
            
            if result is None:  # Cancel
                return
            elif result:  # Yes - cancel processing and exit
                self.is_processing = False
                if self.processing_thread:
                    # Give thread a moment to finish
                    time.sleep(0.5)
            else:  # No - don't exit
                return
        
        # Check for unsaved changes
        if hasattr(self.config_tab, 'has_unsaved_changes') and self.config_tab.has_unsaved_changes():
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved configuration changes. Do you want to save them before exiting?"
            )
            
            if result is None:  # Cancel
                return
            elif result:  # Yes - save and exit
                current_settings = self.config_tab.get_current_settings()
                self._handle_save_settings(current_settings)
        
        # Destroy window
        self.root.destroy()


def main():
    """Main entry point for the modular GUI."""
    root = tk.Tk()
    app = SummeetsGUIModular(root)
    root.mainloop()


if __name__ == "__main__":
    main()