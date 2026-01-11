"""
TUI Constants and Configuration.

Centralizes all magic numbers, default values, and configuration
for the Textual TUI application.
"""

# =============================================================================
# FILE TYPE EXTENSIONS
# =============================================================================

VIDEO_EXTENSIONS = frozenset({
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv", ".flv"
})

AUDIO_EXTENSIONS = frozenset({
    ".m4a", ".flac", ".wav", ".mp3", ".ogg", ".mka", ".webm"
})

TRANSCRIPT_EXTENSIONS = frozenset({
    ".json", ".txt", ".srt", ".md"
})

ALL_SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | TRANSCRIPT_EXTENSIONS

# Text files that can be previewed
TEXT_EXTENSIONS = frozenset({
    ".txt", ".md", ".json", ".srt", ".log", ".py", ".js", ".ts",
    ".css", ".html", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env"
})

# Syntax highlighting styles for preview
SYNTAX_STYLES = {
    ".json": "cyan",
    ".md": "white",
    ".py": "green",
    ".js": "green",
    ".ts": "green",
}


# =============================================================================
# LLM CONFIGURATION
# =============================================================================

# Valid providers
VALID_PROVIDERS = ("openai", "anthropic")

# Default models by provider
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20241022",
}

# Provider display names
PROVIDER_DISPLAY_NAMES = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
}

# Available templates
TEMPLATE_OPTIONS = [
    ("auto-detect", "Auto-detect template"),
    ("default", "Default"),
    ("sop", "SOP"),
    ("decision", "Decision Log"),
    ("brainstorm", "Brainstorm"),
    ("requirements", "Requirements"),
]


# =============================================================================
# PROCESSING DEFAULTS
# =============================================================================

# Summarization settings
DEFAULT_CHUNK_SECONDS = 1800  # 30 minutes
DEFAULT_COD_PASSES = 2
DEFAULT_MAX_TOKENS = 3000

# Audio processing
DEFAULT_AUDIO_FORMAT = "m4a"
DEFAULT_AUDIO_QUALITY = "high"

# Worker pool
DEFAULT_MAX_WORKERS = 4


# =============================================================================
# UI LAYOUT
# =============================================================================

# Panel widths (percentages)
LEFT_PANEL_WIDTH = 28
CENTER_PANEL_WIDTH = 44
RIGHT_PANEL_WIDTH = 28

# Stage indicator dimensions
STAGE_INDICATOR_MIN_WIDTH = 16
STAGE_INDICATOR_HEIGHT = 5

# File info panel
FILE_INFO_MIN_HEIGHT = 8


# =============================================================================
# COLORS (CSS-compatible)
# =============================================================================

# Base colors
COLOR_BACKGROUND = "#0a0e1a"
COLOR_SURFACE = "#0f172a"
COLOR_SURFACE_LIGHT = "#1e293b"
COLOR_BORDER = "#1e3a5f"
COLOR_BORDER_LIGHT = "#334155"

# Text colors
COLOR_TEXT_PRIMARY = "#e2e8f0"
COLOR_TEXT_SECONDARY = "#94a3b8"
COLOR_TEXT_DIM = "#64748b"

# Accent colors
COLOR_ACCENT_PRIMARY = "#38bdf8"  # Cyan
COLOR_ACCENT_SECONDARY = "#818cf8"  # Purple
COLOR_ACCENT_SUCCESS = "#22c55e"  # Green
COLOR_ACCENT_WARNING = "#fbbf24"  # Yellow
COLOR_ACCENT_DANGER = "#ef4444"  # Red

# File type colors
COLOR_VIDEO = COLOR_ACCENT_PRIMARY
COLOR_AUDIO = COLOR_ACCENT_SUCCESS
COLOR_TRANSCRIPT = COLOR_ACCENT_WARNING


# =============================================================================
# STATUS ICONS
# =============================================================================

STATUS_ICONS = {
    "pending": "○  ─ ─",
    "active": "◉  ▶▶▶",
    "complete": "●  ✓ ✓",
    "error": "◉  ✗ ✗",
}

FILE_TYPE_ICONS = {
    "video": "🎬",
    "audio": "🔊",
    "transcript": "📝",
    "unknown": "📄",
}


# =============================================================================
# KEYBOARD BINDINGS
# =============================================================================

KEY_QUIT = "q"
KEY_RUN = "r"
KEY_CONFIG = "c"
KEY_CANCEL = "escape"
KEY_REFRESH = "f5"


# =============================================================================
# TIMEOUTS (seconds)
# =============================================================================

WORKFLOW_TIMEOUT = 3600  # 1 hour max
TASK_UPDATE_INTERVAL = 0.5  # Status update frequency


# =============================================================================
# API KEY PATTERNS
# =============================================================================

# Patterns for masking/validation
API_KEY_PATTERNS = {
    "openai": "sk-",
    "anthropic": "sk-ant-",
    "replicate": "r8_",
}

# Minimum visible chars when masking
MASK_VISIBLE_CHARS = 4


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def load_env_file(env_path) -> dict:
    """
    Load values from .env file.

    Args:
        env_path: Path to .env file

    Returns:
        Dictionary of key-value pairs
    """
    from pathlib import Path
    env_values = {}
    path = Path(env_path) if not hasattr(env_path, 'exists') else env_path

    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        if "#" in value:
                            value = value.split("#")[0]
                        value = value.strip().strip('"').strip("'")
                        env_values[key] = value
        except Exception:
            pass
    return env_values


def mask_api_key(value: str, visible_chars: int = MASK_VISIBLE_CHARS) -> str:
    """
    Mask a sensitive value showing only first and last N chars.

    Args:
        value: Value to mask
        visible_chars: Number of chars to show at start and end

    Returns:
        Masked string
    """
    if len(value) <= visible_chars * 3:
        return "*" * len(value)
    return value[:visible_chars] + "*" * (len(value) - visible_chars * 2) + value[-visible_chars:]


# =============================================================================
# STAGE CONFIGURATION
# =============================================================================

PIPELINE_STAGES = [
    {"id": "extract_audio", "name": "Extract", "icon": "🎬"},
    {"id": "process_audio", "name": "Process", "icon": "🔊"},
    {"id": "transcribe", "name": "Transcribe", "icon": "📝"},
    {"id": "summarize", "name": "Summarize", "icon": "📋"},
]

# Stage ID mappings for compatibility
STAGE_ID_ALIASES = {
    "extract": "extract_audio",
    "process": "process_audio",
}
