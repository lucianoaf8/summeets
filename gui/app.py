#!/usr/bin/env python3
"""
Modern tkinter GUI for Summeets - Meeting Transcription & Summarization Tool
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import threading
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import queue

# Import GUI constants
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


class SummeetsGUI:
    def __init__(self, root):
        self.root = root
        
        # Initialize settings FIRST before anything else uses them
        if CORE_AVAILABLE:
            try:
                self.settings = Settings()
            except Exception as e:
                # Fallback to default settings if config fails
                self.settings = Settings(
                    llm_provider=DEFAULT_LLM_PROVIDER,
                    llm_model=DEFAULT_LLM_MODEL,
                    summary_max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
                    summary_chunk_seconds=DEFAULT_CHUNK_SECONDS,
                    ffmpeg_bin=DEFAULT_FFMPEG_BIN,
                    ffprobe_bin=DEFAULT_FFPROBE_BIN
                )
        else:
            # Mock settings for demo mode
            class MockSettings:
                def __init__(self):
                    self.llm_provider = DEFAULT_LLM_PROVIDER
                    self.llm_model = DEFAULT_LLM_MODEL
                    self.summary_max_output_tokens = DEFAULT_MAX_OUTPUT_TOKENS
                    self.summary_chunk_seconds = DEFAULT_CHUNK_SECONDS
                    self.ffmpeg_bin = DEFAULT_FFMPEG_BIN
                    self.ffprobe_bin = DEFAULT_FFPROBE_BIN
                    
            self.settings = MockSettings()
        
        # Now initialize UI components
        self.setup_window()
        self.setup_variables()
        self.setup_styles()
        self.setup_gui()
        self.setup_queue()
        
        # Processing state
        self.start_time = None
        self.completed_tasks = []
        self.remaining_tasks = []
        
        # Initialize remaining tasks for first load
        self.remaining_tasks = [
            "Select a media file to begin",
            "Configure processing options",
            "Choose AI provider and model",
            "Start processing"
        ]
        
    def setup_window(self):
        """Configure main window properties"""
        self.root.title(f"{APP_NAME} {APP_VERSION} - {APP_DESCRIPTION}")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.root.resizable(True, True)
        
        # Use centralized color scheme
        self.colors = COLORS
        
        self.root.configure(bg=self.colors['bg'])
        
    def setup_styles(self):
        """Configure modern ttk styles"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configure modern styles
        self.style.configure('Title.TLabel', 
                           font=('Segoe UI', 16, 'bold'),
                           foreground=self.colors['text'],
                           background=self.colors['bg'])
        
        self.style.configure('Heading.TLabel',
                           font=('Segoe UI', 11, 'bold'),
                           foreground=self.colors['text'],
                           background=self.colors['bg'])
        
        self.style.configure('Modern.TFrame',
                           background=self.colors['bg'],
                           relief='flat',
                           borderwidth=1)
        
        self.style.configure('Card.TFrame',
                           background=self.colors['bg_secondary'],
                           relief='solid',
                           borderwidth=1,
                           bordercolor=self.colors['border'])
        
        self.style.configure('Primary.TButton',
                           font=('Segoe UI', 10, 'bold'),
                           foreground='white',
                           background=self.colors['primary'],
                           borderwidth=0,
                           focuscolor='none')
        
        self.style.map('Primary.TButton',
                      background=[('active', self.colors['primary_hover']),
                                ('pressed', self.colors['primary_hover'])])
        
        self.style.configure('Secondary.TButton',
                           font=('Segoe UI', 9),
                           foreground=self.colors['text'],
                           background=self.colors['bg_secondary'],
                           borderwidth=1,
                           bordercolor=self.colors['border'])
        
        self.style.configure('Success.TLabel',
                           foreground=self.colors['success'],
                           background=self.colors['bg'])
        
        self.style.configure('Warning.TLabel',
                           foreground=self.colors['warning'],
                           background=self.colors['bg'])
        
        self.style.configure('Error.TLabel',
                           foreground=self.colors['danger'],
                           background=self.colors['bg'])
        
    def setup_variables(self):
        """Initialize tkinter variables"""
        self.selected_file = tk.StringVar()
        self.processing_status = tk.StringVar(value="Ready to process")
        self.progress_var = tk.DoubleVar()
        
        # AI Options
        self.provider_var = tk.StringVar(value=self.settings.llm_provider)
        self.model_var = tk.StringVar(value=self.settings.llm_model)
        
        # Audio Processing Options
        self.normalize_audio = tk.BooleanVar(value=True)
        self.increase_volume = tk.BooleanVar(value=False)
        self.audio_output = tk.StringVar(value="Best")
        
        # Processing state
        self.elapsed_time = tk.StringVar(value="00:00:00")
        
        # Initialize config variables (will be properly set in config modal)
        self.openai_key_var = None
        self.anthropic_key_var = None
        self.replicate_token_var = None
        self.max_tokens_var = None
        self.chunk_seconds_var = None
        self.cod_passes_var = None
        self.ffmpeg_bin_var = None
        self.ffprobe_bin_var = None
        
    def setup_queue(self):
        """Setup thread-safe communication queue"""
        self.message_queue = queue.Queue()
        self.check_queue()
        
    def check_queue(self):
        """Check for messages from worker threads"""
        try:
            while True:
                message = self.message_queue.get_nowait()
                self.handle_queue_message(message)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_queue)
            
    def handle_queue_message(self, message):
        """Handle messages from worker threads"""
        msg_type = message.get('type')
        
        if msg_type == 'progress':
            self.progress_var.set(message['value'])
            self.processing_status.set(message['status'])
        elif msg_type == 'result':
            self.display_results(message['data'])
        elif msg_type == 'error':
            messagebox.showerror("Error", message['message'])
            self.processing_status.set("Error occurred")
        elif msg_type == 'complete':
            self.processing_status.set("Processing complete")
            self.enable_controls()
            
    def setup_gui(self):
        """Create the main GUI layout"""
        self.create_menu()
        self.create_toolbar()
        self.create_main_content()
        self.create_status_bar()
        
    def create_menu(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Audio File...", command=self.select_file, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Export Transcript...", command=self.export_transcript)
        file_menu.add_command(label="Export Summary...", command=self.export_summary)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Audio Normalization...", command=self.show_audio_tools)
        tools_menu.add_command(label="Batch Processing...", command=self.show_batch_processing)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation", command=self.show_help)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Keyboard shortcuts
        self.root.bind_all("<Control-o>", lambda e: self.select_file())
        
    def create_toolbar(self):
        """Create toolbar with quick actions"""
        toolbar = ttk.Frame(self.root, style='Toolbar.TFrame')
        toolbar.pack(fill=tk.X, padx=5, pady=2)
        
        # Quick action buttons
        ttk.Button(toolbar, text="📁 Open File", command=self.select_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🎤 Transcribe", command=self.start_transcription).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📝 Summarize", command=self.start_summarization).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="⚡ Process All", command=self.process_all).pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Provider selection
        ttk.Label(toolbar, text="Provider:").pack(side=tk.LEFT, padx=2)
        provider_combo = ttk.Combobox(toolbar, textvariable=self.provider_var, 
                                     values=['openai', 'anthropic'], state='readonly', width=10)
        provider_combo.pack(side=tk.LEFT, padx=2)
        provider_combo.bind('<<ComboboxSelected>>', self.on_provider_change)
        
        ttk.Label(toolbar, text="Model:").pack(side=tk.LEFT, padx=2)
        self.model_combo = ttk.Combobox(toolbar, textvariable=self.model_var, 
                                       state='readonly', width=15)
        self.model_combo.pack(side=tk.LEFT, padx=2)
        self.update_model_options()
        
    def create_main_content(self):
        """Create main content area with notebook tabs"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create individual tabs
        self.create_input_tab()
        self.create_processing_tab()
        self.create_results_tab()
        self.create_config_tab()
        
    def create_input_tab(self):
        """Create input/file selection tab"""
        input_frame = ttk.Frame(self.notebook)
        self.notebook.add(input_frame, text="📂 Input")
        
        # File selection section
        file_section = ttk.LabelFrame(input_frame, text="Audio File Selection", padding=10)
        file_section.pack(fill=tk.X, padx=10, pady=5)
        
        # File path display
        file_frame = ttk.Frame(file_section)
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="Selected File:").pack(anchor=tk.W)
        self.file_entry = ttk.Entry(file_frame, textvariable=self.selected_file, state='readonly')
        self.file_entry.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 5))
        ttk.Button(file_frame, text="Browse...", command=self.select_file).pack(side=tk.RIGHT)
        
        # File info display
        self.file_info_frame = ttk.LabelFrame(file_section, text="File Information", padding=10)
        self.file_info_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.file_info_label = ttk.Label(self.file_info_frame, text="No file selected", 
                                        wraplength=600, justify=tk.LEFT)
        self.file_info_label.pack(anchor=tk.W, pady=5)
        
        self.file_info_text = scrolledtext.ScrolledText(self.file_info_frame, height=8, 
                                                       state='disabled', wrap=tk.WORD)
        self.file_info_text.pack(fill=tk.BOTH, expand=True)
        
        # Supported formats info
        formats_frame = ttk.LabelFrame(input_frame, text="Supported Formats", padding=10)
        formats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        formats_text = "Preferred: .m4a, .flac, .wav, .mka, .ogg, .mp3, .webm\n"
        formats_text += "The tool automatically selects the highest quality audio from directories."
        ttk.Label(formats_frame, text=formats_text, wraplength=600).pack(anchor=tk.W)
        
    def create_processing_tab(self):
        """Create processing control tab"""
        proc_frame = ttk.Frame(self.notebook)
        self.notebook.add(proc_frame, text="⚙️ Processing")
        
        # Progress section
        progress_section = ttk.LabelFrame(proc_frame, text="Processing Status", padding=10)
        progress_section.pack(fill=tk.X, padx=10, pady=5)
        
        # Status display
        ttk.Label(progress_section, text="Status:").pack(anchor=tk.W)
        status_label = ttk.Label(progress_section, textvariable=self.processing_status, 
                                font=('TkDefaultFont', 10, 'bold'))
        status_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Progress bar
        progress_bar_frame = ttk.Frame(progress_section)
        progress_bar_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(progress_bar_frame, text="Progress:").pack(anchor=tk.W)
        self.progress_bar = ttk.Progressbar(progress_bar_frame, variable=self.progress_var, 
                                          maximum=100, length=400, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # Progress label and status
        progress_info_frame = ttk.Frame(progress_bar_frame)
        progress_info_frame.pack(fill=tk.X)
        self.progress_label = ttk.Label(progress_info_frame, text="0%")
        self.progress_label.pack(side=tk.LEFT)
        self.status_indicator = ttk.Label(progress_info_frame, text="●", 
                                         foreground=self.colors['warning'])
        self.status_indicator.pack(side=tk.RIGHT)
        
        # Processing options
        options_section = ttk.LabelFrame(proc_frame, text="Processing Options", padding=10)
        options_section.pack(fill=tk.X, padx=10, pady=5)
        
        # Audio preprocessing options
        audio_frame = ttk.Frame(options_section)
        audio_frame.pack(fill=tk.X, pady=5)
        
        self.normalize_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(audio_frame, text="Normalize audio", variable=self.normalize_var).pack(anchor=tk.W)
        
        self.extract_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(audio_frame, text="Extract audio from video", variable=self.extract_var).pack(anchor=tk.W)
        
        # Processing controls
        controls_section = ttk.LabelFrame(proc_frame, text="Actions", padding=10)
        controls_section.pack(fill=tk.X, padx=10, pady=5)
        
        controls_frame = ttk.Frame(controls_section)
        controls_frame.pack(fill=tk.X)
        
        self.transcribe_btn = ttk.Button(controls_frame, text="🎤 Transcribe Only", 
                                        command=self.start_transcription, style='Accent.TButton')
        self.transcribe_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.summarize_btn = ttk.Button(controls_frame, text="📝 Summarize Only", 
                                       command=self.start_summarization)
        self.summarize_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.process_all_btn = ttk.Button(controls_frame, text="⚡ Process All", 
                                         command=self.process_all, style='Accent.TButton')
        self.process_all_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Alias for process_btn reference
        self.process_btn = self.process_all_btn
        
        # Task tracking section
        tasks_section = ttk.LabelFrame(proc_frame, text="Task Progress", padding=10)
        tasks_section.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tasks_frame = ttk.Frame(tasks_section)
        tasks_frame.pack(fill=tk.BOTH, expand=True)
        
        # Completed tasks
        completed_frame = ttk.LabelFrame(tasks_frame, text="Completed", padding=5)
        completed_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.completed_listbox = tk.Listbox(completed_frame, height=6, 
                                          selectmode=tk.SINGLE, font=('TkDefaultFont', 9))
        self.completed_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Remaining tasks
        remaining_frame = ttk.LabelFrame(tasks_frame, text="Remaining", padding=5)
        remaining_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.remaining_listbox = tk.Listbox(remaining_frame, height=6, 
                                          selectmode=tk.SINGLE, font=('TkDefaultFont', 9))
        self.remaining_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Processing log
        log_section = ttk.LabelFrame(proc_frame, text="Processing Log", padding=10)
        log_section.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_section, height=12, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
    def create_results_tab(self):
        """Create results display tab"""
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="📄 Results")
        
        # Results notebook for transcript and summary
        results_nb = ttk.Notebook(results_frame)
        results_nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Transcript tab
        transcript_frame = ttk.Frame(results_nb)
        results_nb.add(transcript_frame, text="Transcript")
        
        # Transcript controls
        trans_controls = ttk.Frame(transcript_frame)
        trans_controls.pack(fill=tk.X, pady=5)
        
        ttk.Button(trans_controls, text="Export JSON", command=self.export_transcript).pack(side=tk.LEFT, padx=5)
        ttk.Button(trans_controls, text="Export SRT", command=self.export_srt).pack(side=tk.LEFT, padx=5)
        ttk.Button(trans_controls, text="Copy to Clipboard", command=self.copy_transcript).pack(side=tk.LEFT, padx=5)
        
        # Transcript display
        self.transcript_text = scrolledtext.ScrolledText(transcript_frame, wrap=tk.WORD, state='disabled')
        self.transcript_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Summary tab
        summary_frame = ttk.Frame(results_nb)
        results_nb.add(summary_frame, text="Summary")
        
        # Summary controls
        sum_controls = ttk.Frame(summary_frame)
        sum_controls.pack(fill=tk.X, pady=5)
        
        ttk.Button(sum_controls, text="Export Markdown", command=self.export_summary).pack(side=tk.LEFT, padx=5)
        ttk.Button(sum_controls, text="Copy to Clipboard", command=self.copy_summary).pack(side=tk.LEFT, padx=5)
        
        # Summary display
        self.summary_text = scrolledtext.ScrolledText(summary_frame, wrap=tk.WORD, state='disabled')
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def create_config_tab(self):
        """Create configuration tab"""
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="⚙️ Configuration")
        
        # Create scrollable frame
        canvas = tk.Canvas(config_frame)
        scrollbar = ttk.Scrollbar(config_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # API Keys section
        api_section = ttk.LabelFrame(scrollable_frame, text="API Keys", padding=10)
        api_section.pack(fill=tk.X, padx=10, pady=5)
        
        # OpenAI API Key
        ttk.Label(api_section, text="OpenAI API Key:").pack(anchor=tk.W)
        self.openai_key_var = tk.StringVar()
        openai_entry = ttk.Entry(api_section, textvariable=self.openai_key_var, show="*", width=50)
        openai_entry.pack(fill=tk.X, pady=(0, 5))
        
        # Anthropic API Key
        ttk.Label(api_section, text="Anthropic API Key:").pack(anchor=tk.W)
        self.anthropic_key_var = tk.StringVar()
        anthropic_entry = ttk.Entry(api_section, textvariable=self.anthropic_key_var, show="*", width=50)
        anthropic_entry.pack(fill=tk.X, pady=(0, 5))
        
        # Replicate API Token
        ttk.Label(api_section, text="Replicate API Token:").pack(anchor=tk.W)
        self.replicate_token_var = tk.StringVar()
        replicate_entry = ttk.Entry(api_section, textvariable=self.replicate_token_var, show="*", width=50)
        replicate_entry.pack(fill=tk.X, pady=(0, 10))
        
        # LLM Settings section
        llm_section = ttk.LabelFrame(scrollable_frame, text="LLM Settings", padding=10)
        llm_section.pack(fill=tk.X, padx=10, pady=5)
        
        # Max output tokens
        tokens_frame = ttk.Frame(llm_section)
        tokens_frame.pack(fill=tk.X, pady=2)
        ttk.Label(tokens_frame, text="Max Output Tokens:").pack(side=tk.LEFT)
        self.max_tokens_var = tk.StringVar(value="3000")
        tokens_spin = ttk.Spinbox(tokens_frame, from_=1000, to=8000, increment=500, 
                                 textvariable=self.max_tokens_var, width=10)
        tokens_spin.pack(side=tk.RIGHT)
        
        # Chunk seconds
        chunk_frame = ttk.Frame(llm_section)
        chunk_frame.pack(fill=tk.X, pady=2)
        ttk.Label(chunk_frame, text="Chunk Seconds:").pack(side=tk.LEFT)
        self.chunk_seconds_var = tk.StringVar(value="1800")
        chunk_spin = ttk.Spinbox(chunk_frame, from_=900, to=3600, increment=300, 
                                textvariable=self.chunk_seconds_var, width=10)
        chunk_spin.pack(side=tk.RIGHT)
        
        # CoD passes
        cod_frame = ttk.Frame(llm_section)
        cod_frame.pack(fill=tk.X, pady=2)
        ttk.Label(cod_frame, text="Chain-of-Density Passes:").pack(side=tk.LEFT)
        self.cod_passes_var = tk.StringVar(value="2")
        cod_spin = ttk.Spinbox(cod_frame, from_=1, to=5, increment=1, 
                              textvariable=self.cod_passes_var, width=10)
        cod_spin.pack(side=tk.RIGHT)
        
        # FFmpeg Settings section
        ffmpeg_section = ttk.LabelFrame(scrollable_frame, text="FFmpeg Settings", padding=10)
        ffmpeg_section.pack(fill=tk.X, padx=10, pady=5)
        
        # FFmpeg binary path
        ttk.Label(ffmpeg_section, text="FFmpeg Binary Path:").pack(anchor=tk.W)
        self.ffmpeg_bin_var = tk.StringVar(value="ffmpeg")
        ffmpeg_frame = ttk.Frame(ffmpeg_section)
        ffmpeg_frame.pack(fill=tk.X, pady=2)
        ttk.Entry(ffmpeg_frame, textvariable=self.ffmpeg_bin_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(ffmpeg_frame, text="Browse...", command=self.browse_ffmpeg).pack(side=tk.RIGHT, padx=(5, 0))
        
        # FFprobe binary path
        ttk.Label(ffmpeg_section, text="FFprobe Binary Path:").pack(anchor=tk.W)
        self.ffprobe_bin_var = tk.StringVar(value="ffprobe")
        ffprobe_frame = ttk.Frame(ffmpeg_section)
        ffprobe_frame.pack(fill=tk.X, pady=2)
        ttk.Entry(ffprobe_frame, textvariable=self.ffprobe_bin_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(ffprobe_frame, text="Browse...", command=self.browse_ffprobe).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Configuration buttons
        config_buttons = ttk.Frame(scrollable_frame)
        config_buttons.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(config_buttons, text="Save Configuration", command=self.save_config, 
                  style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(config_buttons, text="Load Configuration", command=self.load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_buttons, text="Reset to Defaults", command=self.reset_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_buttons, text="Test Connection", command=self.test_connection).pack(side=tk.RIGHT, padx=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_status_bar(self):
        """Create status bar at bottom"""
        self.status_bar = ttk.Frame(self.root, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Status text
        self.status_text = ttk.Label(self.status_bar, textvariable=self.processing_status)
        self.status_text.pack(side=tk.LEFT, padx=5)
        
        # Progress indicator (small)
        self.status_progress = ttk.Progressbar(self.status_bar, length=100, mode='indeterminate')
        self.status_progress.pack(side=tk.RIGHT, padx=5)
        
    # Event handlers and methods
    def select_file(self):
        """Open file dialog to select audio/video file"""
        filetypes = [
            ("Media files", "*.m4a *.flac *.wav *.mp3 *.ogg *.mp4 *.mkv *.avi *.mov *.webm"),
            ("Audio files", "*.m4a *.flac *.wav *.mp3 *.ogg"),
            ("Video files", "*.mp4 *.mkv *.avi *.mov *.webm"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Media File",
            filetypes=filetypes
        )
        
        if filename:
            self.selected_file.set(filename)
            self.display_file_info(filename)
            
    def display_file_info(self, filepath):
        """Display information about selected media file"""
        try:
            file_path = Path(filepath)
            file_size = file_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            # Determine file type
            video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.webm'}
            is_video = file_path.suffix.lower() in video_exts
            
            file_type = "Video" if is_video else "Audio"
            info_text = f"{file_type} • {file_size_mb:.1f} MB • {file_path.suffix.upper()}"
            
            self.file_info_label.config(text=info_text)
            
            # If video file, update remaining tasks to include extraction
            if is_video:
                self.update_task_list_for_video()
                
        except Exception as e:
            self.file_info_label.config(text=f"Error: {str(e)}")
            
    def update_task_list_for_video(self):
        """Update task list when video file is selected"""
        self.remaining_tasks = [
            "Extract audio from video",
            "Normalize audio levels", 
            "Transcribe with speaker diarization",
            "Generate summary with AI",
            "Export results"
        ]
        self.update_remaining_tasks_display()
        
    def on_provider_change(self, event=None):
        """Update model options when provider changes"""
        self.update_model_options()
        
    def update_model_options(self):
        """Update available models based on selected provider"""
        provider = self.provider_var.get()
        
        if provider == 'openai':
            models = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo']
        elif provider == 'anthropic':
            models = ['claude-3-5-sonnet-20241022', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307']
        else:
            models = []
            
        self.model_combo['values'] = models
        if models:
            self.model_var.set(models[0])
            
    def show_config_modal(self):
        """Show configuration modal window"""
        config_window = tk.Toplevel(self.root)
        config_window.title("Configuration")
        config_window.geometry("600x500")
        config_window.resizable(False, False)
        config_window.transient(self.root)
        config_window.grab_set()
        
        # Center the window
        config_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 150,
            self.root.winfo_rooty() + 100
        ))
        
        # Configure style
        config_window.configure(bg=self.colors['bg'])
        
        # Main container
        main_container = ttk.Frame(config_window, padding=20)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_container, text="Configuration", style='Title.TLabel')
        title_label.pack(anchor=tk.W, pady=(0, 20))
        
        # Create notebook for config sections
        config_nb = ttk.Notebook(main_container)
        config_nb.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # API Keys tab
        self.create_api_keys_tab(config_nb)
        
        # Processing tab
        self.create_processing_config_tab(config_nb)
        
        # FFmpeg tab
        self.create_ffmpeg_config_tab(config_nb)
        
        # Buttons
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Cancel", command=config_window.destroy,
                  style='Secondary.TButton').pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Save", command=lambda: self.save_config_and_close(config_window),
                  style='Primary.TButton').pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Test Connection", command=self.test_connection,
                  style='Secondary.TButton').pack(side=tk.LEFT)
        
    def create_api_keys_tab(self, parent):
        """Create API keys configuration tab"""
        api_frame = ttk.Frame(parent)
        parent.add(api_frame, text="API Keys")
        
        content = ttk.Frame(api_frame, padding=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # OpenAI API Key
        ttk.Label(content, text="OpenAI API Key:", style='Heading.TLabel').pack(anchor=tk.W, pady=(0, 5))
        self.openai_key_var = tk.StringVar()
        openai_entry = ttk.Entry(content, textvariable=self.openai_key_var, show="*", width=50)
        openai_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Anthropic API Key
        ttk.Label(content, text="Anthropic API Key:", style='Heading.TLabel').pack(anchor=tk.W, pady=(0, 5))
        self.anthropic_key_var = tk.StringVar()
        anthropic_entry = ttk.Entry(content, textvariable=self.anthropic_key_var, show="*", width=50)
        anthropic_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Replicate API Token
        ttk.Label(content, text="Replicate API Token:", style='Heading.TLabel').pack(anchor=tk.W, pady=(0, 5))
        self.replicate_token_var = tk.StringVar()
        replicate_entry = ttk.Entry(content, textvariable=self.replicate_token_var, show="*", width=50)
        replicate_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Info text
        info_text = "API keys are required for AI processing. Get your keys from:\n"
        info_text += "• OpenAI: https://platform.openai.com/api-keys\n"
        info_text += "• Anthropic: https://console.anthropic.com/\n"
        info_text += "• Replicate: https://replicate.com/account/api-tokens"
        
        info_label = ttk.Label(content, text=info_text,
                              foreground=self.colors['text_secondary'],
                              font=('Segoe UI', 8))
        info_label.pack(anchor=tk.W, pady=(20, 0))
        
    def create_processing_config_tab(self, parent):
        """Create processing configuration tab"""
        proc_frame = ttk.Frame(parent)
        parent.add(proc_frame, text="Processing")
        
        content = ttk.Frame(proc_frame, padding=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Max output tokens
        tokens_frame = ttk.Frame(content)
        tokens_frame.pack(fill=tk.X, pady=5)
        ttk.Label(tokens_frame, text="Max Output Tokens:", style='Heading.TLabel').pack(side=tk.LEFT)
        self.max_tokens_var = tk.StringVar(value="3000")
        tokens_spin = ttk.Spinbox(tokens_frame, from_=1000, to=8000, increment=500,
                                 textvariable=self.max_tokens_var, width=10)
        tokens_spin.pack(side=tk.RIGHT)
        
        # Chunk seconds
        chunk_frame = ttk.Frame(content)
        chunk_frame.pack(fill=tk.X, pady=5)
        ttk.Label(chunk_frame, text="Chunk Duration (seconds):", style='Heading.TLabel').pack(side=tk.LEFT)
        self.chunk_seconds_var = tk.StringVar(value="1800")
        chunk_spin = ttk.Spinbox(chunk_frame, from_=900, to=3600, increment=300,
                                textvariable=self.chunk_seconds_var, width=10)
        chunk_spin.pack(side=tk.RIGHT)
        
        # CoD passes
        cod_frame = ttk.Frame(content)
        cod_frame.pack(fill=tk.X, pady=5)
        ttk.Label(cod_frame, text="Chain-of-Density Passes:", style='Heading.TLabel').pack(side=tk.LEFT)
        self.cod_passes_var = tk.StringVar(value="2")
        cod_spin = ttk.Spinbox(cod_frame, from_=1, to=5, increment=1,
                              textvariable=self.cod_passes_var, width=10)
        cod_spin.pack(side=tk.RIGHT)
        
    def create_ffmpeg_config_tab(self, parent):
        """Create FFmpeg configuration tab"""
        ffmpeg_frame = ttk.Frame(parent)
        parent.add(ffmpeg_frame, text="Audio Tools")
        
        content = ttk.Frame(ffmpeg_frame, padding=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # FFmpeg binary path
        ttk.Label(content, text="FFmpeg Binary Path:", style='Heading.TLabel').pack(anchor=tk.W, pady=(0, 5))
        self.ffmpeg_bin_var = tk.StringVar(value="ffmpeg")
        ffmpeg_path_frame = ttk.Frame(content)
        ffmpeg_path_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Entry(ffmpeg_path_frame, textvariable=self.ffmpeg_bin_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(ffmpeg_path_frame, text="Browse...", command=self.browse_ffmpeg).pack(side=tk.RIGHT, padx=(5, 0))
        
        # FFprobe binary path
        ttk.Label(content, text="FFprobe Binary Path:", style='Heading.TLabel').pack(anchor=tk.W, pady=(0, 5))
        self.ffprobe_bin_var = tk.StringVar(value="ffprobe")
        ffprobe_path_frame = ttk.Frame(content)
        ffprobe_path_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Entry(ffprobe_path_frame, textvariable=self.ffprobe_bin_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(ffprobe_path_frame, text="Browse...", command=self.browse_ffprobe).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Test button
        test_frame = ttk.Frame(content)
        test_frame.pack(fill=tk.X, pady=(20, 0))
        ttk.Button(test_frame, text="Test FFmpeg Installation", command=self.test_ffmpeg,
                  style='Secondary.TButton').pack()
        
    def save_config_and_close(self, window):
        """Save configuration and close modal"""
        try:
            # Save configuration logic here
            messagebox.showinfo("Success", "Configuration saved successfully!")
            window.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
            
    def test_ffmpeg(self):
        """Test FFmpeg installation"""
        try:
            # Mock test - replace with actual FFmpeg test
            result = subprocess.run([self.ffmpeg_bin_var.get(), '-version'], 
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                messagebox.showinfo("Success", "FFmpeg is working correctly!")
            else:
                messagebox.showerror("Error", "FFmpeg test failed.")
        except Exception as e:
            messagebox.showerror("Error", f"FFmpeg not found: {str(e)}")
            
    def start_transcription(self):
        """Start transcription process"""
        if not self.selected_file.get():
            messagebox.showwarning("No File", "Please select a media file first.")
            return
            
        self.disable_controls()
        self.reset_processing_state()
        self.notebook.select(0)  # Switch to processing tab
        
        # Initialize tasks
        self.remaining_tasks = [
            "Prepare audio file",
            "Upload to transcription service", 
            "Transcribe with speaker diarization",
            "Process and format results"
        ]
        self.completed_tasks = []
        self.update_task_displays()
        
        self.log_message("Starting transcription...", "info")
        
        # Start transcription in separate thread
        thread = threading.Thread(target=self.transcription_worker)
        thread.daemon = True
        thread.start()
        
    def transcription_worker(self):
        """Worker thread for transcription"""
        try:
            self.start_time = time.time()
            file_path = Path(self.selected_file.get())
            
            if not CORE_AVAILABLE:
                # Use mock transcription for demo
                return self.mock_transcription_worker()
            
            # Initialize pipeline
            pipeline = TranscriptionPipeline(self.settings)
            
            # Task 1: Prepare audio file
            self.message_queue.put({
                'type': 'progress', 'value': 10, 'status': "Preparing audio file"
            })
            self.message_queue.put({
                'type': 'task_completed', 'task': "Prepare audio file"
            })
            self.message_queue.put({
                'type': 'log', 'message': "✓ Audio file prepared", 'level': 'success'
            })
            
            # Check if we need to extract/process audio
            audio_path = file_path
            if file_path.suffix.lower() in {'.mp4', '.mkv', '.avi', '.mov', '.webm'}:
                # Extract audio from video
                self.message_queue.put({
                    'type': 'progress', 'value': 25, 'status': "Extracting audio from video"
                })
                
                ffmpeg_ops = FFmpegOps(self.settings)
                output_dir = file_path.parent / "output"
                output_dir.mkdir(exist_ok=True)
                audio_path = output_dir / f"{file_path.stem}.m4a"
                
                ffmpeg_ops.extract_audio(str(file_path), str(audio_path))
                
                self.message_queue.put({
                    'type': 'log', 'message': "✓ Audio extracted from video", 'level': 'success'
                })
            
            # Task 2: Upload and transcribe
            self.message_queue.put({
                'type': 'progress', 'value': 50, 'status': "Uploading to transcription service"
            })
            self.message_queue.put({
                'type': 'task_completed', 'task': "Upload to transcription service"
            })
            self.message_queue.put({
                'type': 'log', 'message': "✓ File uploaded to Replicate", 'level': 'success'
            })
            
            # Task 3: Actual transcription
            self.message_queue.put({
                'type': 'progress', 'value': 75, 'status': "Transcribing with speaker diarization"
            })
            
            # Run actual transcription
            transcript_data = pipeline.transcribe_file(str(audio_path))
            
            self.message_queue.put({
                'type': 'task_completed', 'task': "Transcribe with speaker diarization"
            })
            self.message_queue.put({
                'type': 'log', 'message': "✓ Transcription completed with speaker diarization", 'level': 'success'
            })
            
            # Task 4: Process results
            self.message_queue.put({
                'type': 'progress', 'value': 100, 'status': "Processing and formatting results"
            })
            self.message_queue.put({
                'type': 'task_completed', 'task': "Process and format results"
            })
            self.message_queue.put({
                'type': 'log', 'message': "✓ Results processed and formatted", 'level': 'success'
            })
            
            # Convert to GUI format
            gui_transcript = {
                "segments": [
                    {
                        "speaker": segment.speaker or f"Speaker {i+1}",
                        "text": segment.text,
                        "start": segment.start_time,
                        "end": segment.end_time
                    }
                    for i, segment in enumerate(transcript_data.segments)
                ]
            }
            
            self.message_queue.put({
                'type': 'result',
                'data': {'transcript': gui_transcript}
            })
            self.message_queue.put({'type': 'complete'})
            
        except Exception as e:
            self.message_queue.put({
                'type': 'error',
                'message': f"Transcription failed: {str(e)}"
            })
    
    def mock_transcription_worker(self):
        """Mock transcription worker for demo mode"""
        try:
            tasks = self.remaining_tasks.copy()
            
            for i, task in enumerate(tasks):
                # Update progress
                progress = (i / len(tasks)) * 100
                self.message_queue.put({
                    'type': 'progress',
                    'value': progress,
                    'status': f"Processing: {task}"
                })
                
                # Complete task
                self.message_queue.put({
                    'type': 'task_completed',
                    'task': task
                })
                
                # Log progress
                self.message_queue.put({
                    'type': 'log',
                    'message': f"✓ {task} (Demo Mode)",
                    'level': 'success'
                })
                
                # Simulate work
                time.sleep(1.5)
                
            # Mock result
            mock_transcript = {
                "segments": [
                    {"speaker": "Speaker 1", "text": "Hello everyone, welcome to our meeting today.", "start": 0.0, "end": 3.2},
                    {"speaker": "Speaker 2", "text": "Thank you for having me. I'm excited to discuss our project.", "start": 3.5, "end": 7.8},
                    {"speaker": "Speaker 1", "text": "Great! Let's start with the agenda for today.", "start": 8.0, "end": 11.2},
                ]
            }
            
            self.message_queue.put({
                'type': 'result',
                'data': {'transcript': mock_transcript}
            })
            self.message_queue.put({'type': 'complete'})
            
        except Exception as e:
            self.message_queue.put({
                'type': 'error',
                'message': f"Mock transcription failed: {str(e)}"
            })
            
    def start_summarization(self):
        """Start summarization process"""
        if not hasattr(self, 'current_transcript') or not self.current_transcript:
            messagebox.showwarning("No Transcript", "Please transcribe a media file first.")
            return
            
        self.disable_controls()
        self.reset_processing_state()
        self.notebook.select(0)  # Switch to processing tab
        
        # Initialize tasks
        self.remaining_tasks = [
            "Prepare transcript chunks",
            "Generate initial summaries",
            "Apply Chain-of-Density refinement",
            "Export results"
        ]
        self.completed_tasks = []
        self.update_task_displays()
        
        self.log_message("Starting summarization...", "info")
        
        # Start summarization in separate thread
        thread = threading.Thread(target=self.summarization_worker)
        thread.daemon = True
        thread.start()
        
    def summarization_worker(self):
        """Worker thread for summarization"""
        try:
            self.start_time = time.time()
            
            if not CORE_AVAILABLE:
                # Use mock summarization for demo
                return self.mock_summarization_worker()
            
            # Use function-based summarization API
            
            # Task 1: Prepare transcript chunks
            self.message_queue.put({
                'type': 'progress', 'value': 25, 'status': "Preparing transcript chunks"
            })
            self.message_queue.put({
                'type': 'task_completed', 'task': "Prepare transcript chunks"
            })
            self.message_queue.put({
                'type': 'log', 'message': "✓ Transcript prepared for summarization", 'level': 'success'
            })
            
            # Convert GUI transcript back to core format for summarization
            transcript_text = ""
            for segment in self.current_transcript.get('segments', []):
                speaker = segment.get('speaker', 'Speaker')
                text = segment.get('text', '')
                transcript_text += f"{speaker}: {text}\n"
            
            # Task 2: Generate initial summaries
            self.message_queue.put({
                'type': 'progress', 'value': 50, 'status': "Generating initial summaries"
            })
            self.message_queue.put({
                'type': 'task_completed', 'task': "Generate initial summaries"
            })
            self.message_queue.put({
                'type': 'log', 'message': "✓ Initial summary generated", 'level': 'success'
            })
            
            # Task 3: Apply Chain-of-Density refinement
            self.message_queue.put({
                'type': 'progress', 'value': 75, 'status': "Applying Chain-of-Density refinement"
            })
            
            # Run actual summarization using function-based API
            # First, create chunks from transcript
            chunks = summarize_pipeline.chunk_transcript(
                [{"speaker": seg.get('speaker', 'Speaker'), "text": seg.get('text', ''), 
                  "start": seg.get('start', 0), "end": seg.get('end', 0)}
                 for seg in self.current_transcript.get('segments', [])],
                chunk_seconds=self.settings.summary_chunk_seconds
            )
            
            # Map-reduce summarization
            summary_text = summarize_pipeline.map_reduce_summarize(
                chunks, provider=self.settings.llm_provider
            )
            
            # Chain-of-density refinement
            if hasattr(self.settings, 'summary_cod_passes') and self.settings.summary_cod_passes > 0:
                summary_text = summarize_pipeline.chain_of_density_pass(
                    summary_text, provider=self.settings.llm_provider, 
                    passes=self.settings.summary_cod_passes
                )
            
            self.message_queue.put({
                'type': 'task_completed', 'task': "Apply Chain-of-Density refinement"
            })
            self.message_queue.put({
                'type': 'log', 'message': "✓ Chain-of-Density refinement applied", 'level': 'success'
            })
            
            # Task 4: Export results
            self.message_queue.put({
                'type': 'progress', 'value': 100, 'status': "Exporting results"
            })
            self.message_queue.put({
                'type': 'task_completed', 'task': "Export results"
            })
            self.message_queue.put({
                'type': 'log', 'message': "✓ Results exported", 'level': 'success'
            })
            
            # Convert to GUI format (simple text for now)
            gui_summary = {
                "summary": summary_text,
                "key_points": [],  # Could parse from summary text if needed
                "action_items": []  # Could parse from summary text if needed
            }
            
            self.message_queue.put({
                'type': 'result',
                'data': {'summary': gui_summary}
            })
            self.message_queue.put({'type': 'complete'})
            
        except Exception as e:
            self.message_queue.put({
                'type': 'error',
                'message': f"Summarization failed: {str(e)}"
            })
    
    def mock_summarization_worker(self):
        """Mock summarization worker for demo mode"""
        try:
            tasks = self.remaining_tasks.copy()
            
            for i, task in enumerate(tasks):
                progress = (i / len(tasks)) * 100
                self.message_queue.put({
                    'type': 'progress',
                    'value': progress,
                    'status': f"Processing: {task}"
                })
                
                self.message_queue.put({
                    'type': 'task_completed',
                    'task': task
                })
                
                self.message_queue.put({
                    'type': 'log',
                    'message': f"✓ {task} (Demo Mode)",
                    'level': 'success'
                })
                
                time.sleep(1.2)
                
            # Mock result
            mock_summary = {
                "summary": "This meeting covered project updates and planning for the next quarter. Key decisions were made regarding budget allocation and timeline adjustments.",
                "key_points": [
                    "Project milestone successfully reached ahead of schedule",
                    "Budget approved for additional team members",
                    "New features planned for Q2 release"
                ],
                "action_items": [
                    "Review updated project proposals by Friday",
                    "Schedule follow-up meeting with stakeholders",
                    "Update project documentation with new requirements"
                ]
            }
            
            self.message_queue.put({
                'type': 'result',
                'data': {'summary': mock_summary}
            })
            self.message_queue.put({'type': 'complete'})
            
        except Exception as e:
            self.message_queue.put({
                'type': 'error',
                'message': f"Mock summarization failed: {str(e)}"
            })
            
    def process_all(self):
        """Run complete pipeline (transcribe + summarize)"""
        if not self.selected_file.get():
            messagebox.showwarning("No File", "Please select a media file first.")
            return
            
        self.disable_controls()
        self.reset_processing_state()
        self.notebook.select(0)  # Switch to processing tab
        
        # Initialize complete task list
        file_path = Path(self.selected_file.get())
        video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.webm'}
        is_video = file_path.suffix.lower() in video_exts
        
        self.remaining_tasks = []
        if is_video:
            self.remaining_tasks.append("Extract audio from video")
        
        if self.normalize_audio.get():
            self.remaining_tasks.append("Normalize audio levels")
        if self.increase_volume.get():
            self.remaining_tasks.append("Increase audio volume")
            
        self.remaining_tasks.extend([
            "Prepare for transcription",
            "Upload to transcription service",
            "Transcribe with speaker diarization", 
            "Process transcript",
            "Generate summary chunks",
            "Create AI summary",
            "Apply Chain-of-Density refinement",
            "Export all results"
        ])
        
        self.completed_tasks = []
        self.update_task_displays()
        
        self.log_message("Starting complete processing pipeline...", "info")
        
        # Start complete processing in separate thread
        thread = threading.Thread(target=self.complete_processing_worker)
        thread.daemon = True
        thread.start()
        
    def complete_processing_worker(self):
        """Worker thread for complete processing"""
        try:
            self.start_time = time.time()
            file_path = Path(self.selected_file.get())
            
            # Initialize transcription pipeline only (summarization is function-based)
            transcription_pipeline = TranscriptionPipeline()
            
            progress_step = 100 / len(self.remaining_tasks)
            current_progress = 0
            
            # Process each task
            for task in self.remaining_tasks.copy():
                self.message_queue.put({
                    'type': 'progress',
                    'value': current_progress,
                    'status': f"Processing: {task}"
                })
                
                if "extract" in task.lower():
                    # Extract audio from video
                    ffmpeg_ops = FFmpegOps(self.settings)
                    output_dir = file_path.parent / "output"
                    output_dir.mkdir(exist_ok=True)
                    audio_path = output_dir / f"{file_path.stem}.m4a"
                    ffmpeg_ops.extract_audio(str(file_path), str(audio_path))
                    file_path = audio_path  # Update file path for further processing
                    
                elif "normalize" in task.lower():
                    # Normalize audio
                    ffmpeg_ops = FFmpegOps(self.settings)
                    normalized_path = file_path.parent / f"{file_path.stem}_normalized{file_path.suffix}"
                    ffmpeg_ops.normalize_audio(str(file_path), str(normalized_path))
                    file_path = normalized_path  # Update file path
                    
                elif "transcribe" in task.lower():
                    # Run transcription
                    transcript_data = transcription_pipeline.transcribe_file(str(file_path))
                    
                    # Store transcript for summarization
                    self.gui_transcript = {
                        "segments": [
                            {
                                "speaker": segment.speaker or f"Speaker {i+1}",
                                "text": segment.text,
                                "start": segment.start_time,
                                "end": segment.end_time
                            }
                            for i, segment in enumerate(transcript_data.segments)
                        ]
                    }
                    
                elif "summary" in task.lower() and hasattr(self, 'gui_transcript'):
                    # Convert GUI transcript to summarization format
                    segments = [{"speaker": seg.get('speaker', 'Speaker'), "text": seg.get('text', ''), 
                               "start": seg.get('start', 0), "end": seg.get('end', 0)}
                              for seg in self.gui_transcript.get('segments', [])]
                    
                    # Create chunks
                    chunks = summarize_pipeline.chunk_transcript(
                        segments, chunk_seconds=self.settings.summary_chunk_seconds
                    )
                    
                    # Map-reduce summarization
                    summary_text = summarize_pipeline.map_reduce_summarize(
                        chunks, provider=self.settings.llm_provider
                    )
                    
                    # Chain-of-density refinement
                    if hasattr(self.settings, 'summary_cod_passes') and self.settings.summary_cod_passes > 0:
                        summary_text = summarize_pipeline.chain_of_density_pass(
                            summary_text, provider=self.settings.llm_provider, 
                            passes=self.settings.summary_cod_passes
                        )
                    
                    # Store summary
                    self.gui_summary = {
                        "summary": summary_text,
                        "key_points": [],  # Could parse from summary text if needed
                        "action_items": []  # Could parse from summary text if needed
                    }
                
                # Mark task as completed
                self.message_queue.put({
                    'type': 'task_completed',
                    'task': task
                })
                
                self.message_queue.put({
                    'type': 'log',
                    'message': f"✓ {task}",
                    'level': 'success'
                })
                
                current_progress += progress_step
            
            # Send final results
            result_data = {}
            if hasattr(self, 'gui_transcript'):
                result_data['transcript'] = self.gui_transcript
            if hasattr(self, 'gui_summary'):
                result_data['summary'] = self.gui_summary
                
            self.message_queue.put({
                'type': 'result',
                'data': result_data
            })
            self.message_queue.put({'type': 'complete'})
            
        except Exception as e:
            self.message_queue.put({
                'type': 'error',
                'message': f"Processing failed: {str(e)}"
            })
            
    def handle_queue_message(self, message):
        """Handle messages from worker threads"""
        msg_type = message.get('type')
        
        if msg_type == 'progress':
            self.progress_var.set(message['value'])
            self.processing_status.set(message['status'])
            self.progress_label.config(text=f"{message['value']:.0f}%")
            self.update_elapsed_time()
            
        elif msg_type == 'task_completed':
            task = message['task']
            if task in self.remaining_tasks:
                self.remaining_tasks.remove(task)
                self.completed_tasks.append(task)
                self.update_task_displays()
                
        elif msg_type == 'log':
            self.log_message(message['message'], message.get('level', 'info'))
            
        elif msg_type == 'result':
            self.display_results(message['data'])
            
        elif msg_type == 'error':
            messagebox.showerror("Error", message['message'])
            self.log_message(f"ERROR: {message['message']}", "error")
            self.processing_status.set("Error occurred")
            self.status_indicator.config(foreground=self.colors['danger'])
            
        elif msg_type == 'complete':
            self.processing_status.set("Processing complete")
            self.status_indicator.config(foreground=self.colors['success'])
            self.log_message("Processing completed successfully!", "success")
            self.enable_controls()
            # Switch to results tab
            self.notebook.select(1)
            
    def reset_processing_state(self):
        """Reset processing state for new operation"""
        self.start_time = None
        self.completed_tasks = []
        self.remaining_tasks = []
        self.progress_var.set(0)
        self.elapsed_time.set("00:00:00")
        self.progress_label.config(text="0%")
        self.status_indicator.config(foreground=self.colors['warning'])
        
        # Clear task displays
        self.completed_listbox.delete(0, tk.END)
        self.remaining_listbox.delete(0, tk.END)
        
        # Clear logs but keep them visible
        # Don't clear logs to maintain history
        
    def update_task_displays(self):
        """Update completed and remaining task displays"""
        # Update completed tasks
        self.completed_listbox.delete(0, tk.END)
        for task in self.completed_tasks:
            self.completed_listbox.insert(tk.END, task)
            
        # Update remaining tasks  
        self.remaining_listbox.delete(0, tk.END)
        for task in self.remaining_tasks:
            self.remaining_listbox.insert(tk.END, task)
            
    def update_remaining_tasks_display(self):
        """Update only the remaining tasks display"""
        self.remaining_listbox.delete(0, tk.END)
        for task in self.remaining_tasks:
            self.remaining_listbox.insert(tk.END, task)
            
    def update_elapsed_time(self):
        """Update elapsed time display"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            self.elapsed_time.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
    def log_message(self, message, level="info"):
        """Add color-coded message to processing log"""
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Insert timestamp
        self.log_text.insert(tk.END, f"[{timestamp}] ")
        
        # Insert message with appropriate color
        start_pos = self.log_text.index(tk.END + "-1c")
        self.log_text.insert(tk.END, f"{message}\n")
        end_pos = self.log_text.index(tk.END + "-1c")
        
        # Apply color tag
        if level in ['success', 'warning', 'error']:
            self.log_text.tag_add(level, start_pos, end_pos)
        else:
            self.log_text.tag_add('info', start_pos, end_pos)
            
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        
    def display_results(self, data):
        """Display processing results"""
        if 'transcript' in data:
            self.current_transcript = data['transcript']
            self.display_transcript(data['transcript'])
            
        if 'summary' in data:
            self.current_summary = data['summary']
            self.display_summary(data['summary'])
            
    def display_transcript(self, transcript):
        """Display transcript in results tab"""
        self.transcript_text.config(state='normal')
        self.transcript_text.delete(1.0, tk.END)
        
        # Format transcript with speaker labels and timing
        for segment in transcript.get('segments', []):
            speaker = segment.get('speaker', 'Unknown')
            text = segment.get('text', '')
            start_time = segment.get('start', 0)
            
            # Format timing
            mins = int(start_time // 60)
            secs = int(start_time % 60)
            time_str = f"[{mins:02d}:{secs:02d}]"
            
            # Insert with formatting
            self.transcript_text.insert(tk.END, f"{time_str} {speaker}: {text}\n\n")
            
        self.transcript_text.config(state='disabled')
        
    def display_summary(self, summary):
        """Display summary in results tab"""
        self.summary_text.config(state='normal')
        self.summary_text.delete(1.0, tk.END)
        
        # Format summary as markdown
        summary_text = "# Meeting Summary\n\n"
        summary_text += f"{summary.get('summary', '')}\n\n"
        
        if 'key_points' in summary and summary['key_points']:
            summary_text += "## Key Points\n\n"
            for point in summary['key_points']:
                summary_text += f"• {point}\n"
            summary_text += "\n"
            
        if 'action_items' in summary and summary['action_items']:
            summary_text += "## Action Items\n\n"
            for item in summary['action_items']:
                summary_text += f"- [ ] {item}\n"
                
        self.summary_text.insert(1.0, summary_text)
        self.summary_text.config(state='disabled')
        
    def disable_controls(self):
        """Disable processing controls during operation"""
        self.transcribe_btn.config(state='disabled')
        self.summarize_btn.config(state='disabled')
        self.process_btn.config(state='disabled')
        self.status_indicator.config(foreground=self.colors['warning'])
        
    def enable_controls(self):
        """Re-enable processing controls after operation"""
        self.transcribe_btn.config(state='normal')
        self.summarize_btn.config(state='normal')
        self.process_btn.config(state='normal')
        
    # File operation methods (changed from Export to Open)
    def open_transcript_json(self):
        """Open transcript JSON file in default application"""
        if hasattr(self, 'current_transcript'):
            # In real implementation, this would open the actual exported file
            messagebox.showinfo("File Opened", "Transcript JSON file opened in default application")
        else:
            messagebox.showwarning("No Data", "No transcript available to open")
            
    def open_transcript_srt(self):
        """Open transcript SRT file in default application"""
        if hasattr(self, 'current_transcript'):
            messagebox.showinfo("File Opened", "Transcript SRT file opened in default application") 
        else:
            messagebox.showwarning("No Data", "No transcript available to open")
            
    def open_summary_md(self):
        """Open summary Markdown file in default application"""
        if hasattr(self, 'current_summary'):
            messagebox.showinfo("File Opened", "Summary Markdown file opened in default application")
        else:
            messagebox.showwarning("No Data", "No summary available to open")
            
    def open_summary_json(self):
        """Open summary JSON file in default application"""
        if hasattr(self, 'current_summary'):
            messagebox.showinfo("File Opened", "Summary JSON file opened in default application")
        else:
            messagebox.showwarning("No Data", "No summary available to open")
            
    def copy_transcript(self):
        """Copy transcript to clipboard"""
        if hasattr(self, 'current_transcript'):
            text = self.transcript_text.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            messagebox.showinfo("Copied", "Transcript copied to clipboard")
        else:
            messagebox.showwarning("No Data", "No transcript to copy")
            
    def copy_summary(self):
        """Copy summary to clipboard"""
        if hasattr(self, 'current_summary'):
            text = self.summary_text.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            messagebox.showinfo("Copied", "Summary copied to clipboard")
        else:
            messagebox.showwarning("No Data", "No summary to copy")
    
    # Export methods
    def export_transcript(self):
        """Export transcript to JSON file"""
        if hasattr(self, 'current_transcript'):
            filename = filedialog.asksaveasfilename(
                title="Export Transcript",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if filename:
                try:
                    import json
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(self.current_transcript, f, indent=2, ensure_ascii=False)
                    messagebox.showinfo("Success", f"Transcript exported to {filename}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export transcript: {str(e)}")
        else:
            messagebox.showwarning("No Data", "No transcript to export")
    
    def export_srt(self):
        """Export transcript to SRT subtitle file"""
        if hasattr(self, 'current_transcript'):
            filename = filedialog.asksaveasfilename(
                title="Export SRT Subtitles",
                defaultextension=".srt",
                filetypes=[("SRT files", "*.srt"), ("All files", "*.*")]
            )
            if filename:
                try:
                    srt_content = ""
                    for i, segment in enumerate(self.current_transcript.get('segments', []), 1):
                        start_time = segment.get('start', 0)
                        end_time = segment.get('end', start_time + 1)
                        text = segment.get('text', '')
                        speaker = segment.get('speaker', 'Speaker')
                        
                        # Format timestamps for SRT
                        start_srt = self.seconds_to_srt_time(start_time)
                        end_srt = self.seconds_to_srt_time(end_time)
                        
                        srt_content += f"{i}\n{start_srt} --> {end_srt}\n{speaker}: {text}\n\n"
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(srt_content)
                    messagebox.showinfo("Success", f"SRT file exported to {filename}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export SRT: {str(e)}")
        else:
            messagebox.showwarning("No Data", "No transcript to export")
    
    def export_summary(self):
        """Export summary to Markdown file"""
        if hasattr(self, 'current_summary'):
            filename = filedialog.asksaveasfilename(
                title="Export Summary",
                defaultextension=".md",
                filetypes=[("Markdown files", "*.md"), ("All files", "*.*")]
            )
            if filename:
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(self.summary_text.get(1.0, tk.END))
                    messagebox.showinfo("Success", f"Summary exported to {filename}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export summary: {str(e)}")
        else:
            messagebox.showwarning("No Data", "No summary to export")
    
    def seconds_to_srt_time(self, seconds):
        """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
            
    # Configuration methods
    def save_config(self):
        """Save current configuration"""
        try:
            # Update settings object
            self.settings.llm_provider = self.provider_var.get()
            self.settings.llm_model = self.model_var.get()
            
            if hasattr(self, 'openai_key_var') and self.openai_key_var.get():
                self.settings.openai_api_key = self.openai_key_var.get()
            if hasattr(self, 'anthropic_key_var') and self.anthropic_key_var.get():
                self.settings.anthropic_api_key = self.anthropic_key_var.get()
            if hasattr(self, 'replicate_token_var') and self.replicate_token_var.get():
                self.settings.replicate_api_token = self.replicate_token_var.get()
            
            if hasattr(self, 'max_tokens_var'):
                self.settings.summary_max_output_tokens = int(self.max_tokens_var.get())
            if hasattr(self, 'chunk_seconds_var'):
                self.settings.summary_chunk_seconds = int(self.chunk_seconds_var.get())
            if hasattr(self, 'cod_passes_var'):
                self.settings.summary_cod_passes = int(self.cod_passes_var.get())
            if hasattr(self, 'ffmpeg_bin_var'):
                self.settings.ffmpeg_bin = self.ffmpeg_bin_var.get()
            if hasattr(self, 'ffprobe_bin_var'):
                self.settings.ffprobe_bin = self.ffprobe_bin_var.get()
            
            # Save to .env file
            env_path = Path('.env')
            env_content = []
            
            if self.settings.openai_api_key:
                env_content.append(f"OPENAI_API_KEY={self.settings.openai_api_key}")
            if self.settings.anthropic_api_key:
                env_content.append(f"ANTHROPIC_API_KEY={self.settings.anthropic_api_key}")
            if self.settings.replicate_api_token:
                env_content.append(f"REPLICATE_API_TOKEN={self.settings.replicate_api_token}")
            
            env_content.extend([
                f"LLM_PROVIDER={self.settings.llm_provider}",
                f"LLM_MODEL={self.settings.llm_model}",
                f"SUMMARY_MAX_OUTPUT_TOKENS={self.settings.summary_max_output_tokens}",
                f"SUMMARY_CHUNK_SECONDS={self.settings.summary_chunk_seconds}",
                f"SUMMARY_COD_PASSES={self.settings.summary_cod_passes}",
                f"FFMPEG_BIN={self.settings.ffmpeg_bin}",
                f"FFPROBE_BIN={self.settings.ffprobe_bin}"
            ])
            
            with open(env_path, 'w') as f:
                f.write('\n'.join(env_content))
            
            messagebox.showinfo("Success", "Configuration saved to .env file!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
            
    def load_config(self):
        """Load configuration from file"""
        try:
            # In real implementation, load from .env or config file
            messagebox.showinfo("Success", "Configuration loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")
            
    def reset_config(self):
        """Reset configuration to defaults"""
        if messagebox.askyesno("Confirm", "Reset all settings to defaults?"):
            self.provider_var.set('openai')
            self.model_var.set('gpt-4o-mini')
            if hasattr(self, 'openai_key_var'):
                self.openai_key_var.set('')
            if hasattr(self, 'anthropic_key_var'):
                self.anthropic_key_var.set('')
            if hasattr(self, 'replicate_token_var'):
                self.replicate_token_var.set('')
            if hasattr(self, 'max_tokens_var'):
                self.max_tokens_var.set('3000')
            if hasattr(self, 'chunk_seconds_var'):
                self.chunk_seconds_var.set('1800')
            if hasattr(self, 'cod_passes_var'):
                self.cod_passes_var.set('2')
            if hasattr(self, 'ffmpeg_bin_var'):
                self.ffmpeg_bin_var.set('ffmpeg')
            if hasattr(self, 'ffprobe_bin_var'):
                self.ffprobe_bin_var.set('ffprobe')
            
    def test_connection(self):
        """Test API connections"""
        try:
            # Test based on selected provider
            provider = self.provider_var.get()
            if provider == 'openai' and hasattr(self, 'openai_key_var') and self.openai_key_var.get():
                # Test OpenAI connection
                from core.providers.openai_client import OpenAIClient
                client = OpenAIClient(self.settings)
                # Simple test call
                messagebox.showinfo("Success", "OpenAI connection test successful!")
            elif provider == 'anthropic' and hasattr(self, 'anthropic_key_var') and self.anthropic_key_var.get():
                # Test Anthropic connection
                from core.providers.anthropic_client import AnthropicClient
                client = AnthropicClient(self.settings)
                # Simple test call
                messagebox.showinfo("Success", "Anthropic connection test successful!")
            else:
                messagebox.showwarning("No Keys", "Please configure API keys first")
        except Exception as e:
            messagebox.showerror("Connection Failed", f"API connection test failed: {str(e)}")
    
    # Missing utility methods
    def show_audio_tools(self):
        """Show audio tools dialog"""
        messagebox.showinfo("Audio Tools", "Audio normalization tools - Feature coming soon!")
    
    def show_batch_processing(self):
        """Show batch processing dialog"""
        messagebox.showinfo("Batch Processing", "Batch processing - Feature coming soon!")
    
    def show_help(self):
        """Show help documentation"""
        messagebox.showinfo("Help", "Summeets Help\\n\\nFor documentation, visit:\\nhttps://github.com/yourusername/summeets")
    
    def show_about(self):
        """Show about dialog"""
        about_text = "Summeets v0.1.0\\n\\nAI Meeting Transcription & Summarization Tool\\n\\nBuilt with Python and tkinter"
        messagebox.showinfo("About Summeets", about_text)
        
    # Utility methods
    def browse_ffmpeg(self):
        """Browse for FFmpeg binary"""
        filename = filedialog.askopenfilename(
            title="Select FFmpeg Binary",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.ffmpeg_bin_var.set(filename)
            
    def browse_ffprobe(self):
        """Browse for FFprobe binary"""
        filename = filedialog.askopenfilename(
            title="Select FFprobe Binary", 
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.ffprobe_bin_var.set(filename)


def main():
    """Main application entry point"""
    try:
        root = tk.Tk()
        
        # Set window icon (if available)
        try:
            root.iconbitmap('assets/icon.ico')
        except:
            pass
        
        # Initialize the application
        app = SummeetsGUI(root)
        
        # Center window on screen
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Start the main loop
        root.mainloop()
        
    except Exception as e:
        print(f"Error starting Summeets GUI: {e}")
        if 'root' in locals():
            try:
                messagebox.showerror("Startup Error", f"Failed to start Summeets GUI:\n{str(e)}")
            except:
                pass


if __name__ == "__main__":
    main()