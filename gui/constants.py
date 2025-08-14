#!/usr/bin/env python3
"""
GUI Constants for Summeets - Centralized configuration values
"""

# Window dimensions and sizing
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 600

# UI element dimensions
PROGRESS_BAR_LENGTH = 400
LOG_TEXT_HEIGHT = 12
FILE_INFO_HEIGHT = 8
LISTBOX_HEIGHT = 6

# Timing and delays
QUEUE_CHECK_INTERVAL_MS = 100
WORKER_SLEEP_DURATION = 1.5
MOCK_TASK_DELAY = 1.2
SUBPROCESS_TIMEOUT_SECONDS = 5

# UI padding and spacing
DEFAULT_PADX = 5
DEFAULT_PADY = 2
SECTION_PADX = 10
SECTION_PADY = 5
NOTEBOOK_PADX = 10
NOTEBOOK_PADY = 5

# Configuration modal dimensions
CONFIG_MODAL_WIDTH = 600
CONFIG_MODAL_HEIGHT = 500
CONFIG_MODAL_OFFSET_X = 150
CONFIG_MODAL_OFFSET_Y = 100

# Color scheme
COLORS = {
    'bg': '#ffffff',
    'bg_secondary': '#f8f9fa',
    'primary': '#2563eb',
    'primary_hover': '#1d4ed8',
    'success': '#16a34a',
    'warning': '#d97706',
    'danger': '#dc2626',
    'text': '#1f2937',
    'text_secondary': '#6b7280',
    'border': '#e5e7eb',
    'accent': '#8b5cf6'
}

# File formats
SUPPORTED_AUDIO_FORMATS = ['.m4a', '.flac', '.wav', '.mp3', '.ogg']
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.mkv', '.avi', '.mov', '.webm']
ALL_MEDIA_FORMATS = SUPPORTED_AUDIO_FORMATS + SUPPORTED_VIDEO_FORMATS

# File dialog types
MEDIA_FILE_TYPES = [
    ("Media files", "*.m4a *.flac *.wav *.mp3 *.ogg *.mp4 *.mkv *.avi *.mov *.webm"),
    ("Audio files", "*.m4a *.flac *.wav *.mp3 *.ogg"),
    ("Video files", "*.mp4 *.mkv *.avi *.mov *.webm"),
    ("All files", "*.*")
]

EXPORT_JSON_TYPES = [("JSON files", "*.json"), ("All files", "*.*")]
EXPORT_SRT_TYPES = [("SRT files", "*.srt"), ("All files", "*.*")]
EXPORT_MD_TYPES = [("Markdown files", "*.md"), ("All files", "*.*")]
EXECUTABLE_TYPES = [("Executable files", "*.exe"), ("All files", "*.*")]

# Configuration defaults
DEFAULT_LLM_PROVIDER = 'openai'
DEFAULT_LLM_MODEL = 'gpt-4o-mini'
DEFAULT_MAX_OUTPUT_TOKENS = 3000
DEFAULT_CHUNK_SECONDS = 1800
DEFAULT_COD_PASSES = 2
DEFAULT_FFMPEG_BIN = 'ffmpeg'
DEFAULT_FFPROBE_BIN = 'ffprobe'

# OpenAI models
OPENAI_MODELS = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo']

# Anthropic models  
ANTHROPIC_MODELS = [
    'claude-3-5-sonnet-20241022', 
    'claude-3-sonnet-20240229', 
    'claude-3-haiku-20240307'
]

# Provider options
LLM_PROVIDERS = ['openai', 'anthropic']

# Processing options
NORMALIZE_AUDIO_DEFAULT = True
EXTRACT_AUDIO_DEFAULT = True
AUDIO_OUTPUT_DEFAULT = "Best"

# Token limits
MIN_OUTPUT_TOKENS = 1000
MAX_OUTPUT_TOKENS = 8000
TOKEN_INCREMENT = 500

# Chunk duration limits
MIN_CHUNK_SECONDS = 900
MAX_CHUNK_SECONDS = 3600
CHUNK_INCREMENT = 300

# Chain-of-Density passes limits
MIN_COD_PASSES = 1
MAX_COD_PASSES = 5
COD_INCREMENT = 1

# Text display settings
DEFAULT_WRAP_LENGTH = 600
ENTRY_WIDTH = 50
SPINBOX_WIDTH = 10
COMBO_WIDTH_PROVIDER = 10
COMBO_WIDTH_MODEL = 15

# Font settings
TITLE_FONT = ('Segoe UI', 16, 'bold')
HEADING_FONT = ('Segoe UI', 11, 'bold')  
SECONDARY_FONT = ('Segoe UI', 9)
INFO_FONT = ('Segoe UI', 8)
DEFAULT_FONT = ('TkDefaultFont', 10, 'bold')
LISTBOX_FONT = ('TkDefaultFont', 9)

# Status messages
STATUS_READY = "Ready to process"
STATUS_ERROR = "Error occurred"
STATUS_COMPLETE = "Processing complete"
STATUS_NO_FILE = "No file selected"

# Initial task lists
DEFAULT_INITIAL_TASKS = [
    "Select a media file to begin",
    "Configure processing options", 
    "Choose AI provider and model",
    "Start processing"
]

VIDEO_PROCESSING_TASKS = [
    "Extract audio from video",
    "Normalize audio levels",
    "Transcribe with speaker diarization", 
    "Generate summary with AI",
    "Export results"
]

# Application info
APP_NAME = "Summeets"
APP_VERSION = "v0.1.0"
APP_DESCRIPTION = "AI Meeting Transcription & Summarization Tool"
APP_TECH_STACK = "Built with Python and tkinter"

# External URLs
OPENAI_KEYS_URL = "https://platform.openai.com/api-keys"
ANTHROPIC_KEYS_URL = "https://console.anthropic.com/"
REPLICATE_TOKENS_URL = "https://replicate.com/account/api-tokens"
DOCS_URL = "https://github.com/yourusername/summeets"

# Tab names and icons
TAB_INPUT = "📂 Input"
TAB_PROCESSING = "⚙️ Processing"  
TAB_RESULTS = "📄 Results"
TAB_CONFIG = "⚙️ Configuration"

# Button text and icons
BTN_OPEN_FILE = "📁 Open File"
BTN_TRANSCRIBE = "🎤 Transcribe"
BTN_SUMMARIZE = "📝 Summarize"
BTN_PROCESS_ALL = "⚡ Process All"
BTN_TRANSCRIBE_ONLY = "🎤 Transcribe Only"
BTN_SUMMARIZE_ONLY = "📝 Summarize Only"

# Progress indicators
PROGRESS_INDICATOR = "●"
PROGRESS_FORMAT = "{:.0f}%"

# Time format
TIME_FORMAT = "{:02d}:{:02d}:{:02d}"
TIMESTAMP_FORMAT = "%H:%M:%S"
SRT_TIME_FORMAT = "{:02d}:{:02d}:{:02d},{:03d}"