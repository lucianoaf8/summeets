# C:\Projects\summeets\core\utils\config.py
"""
Application configuration using Pydantic Settings.
Manages environment variables and default settings for Summeets.
"""
from __future__ import annotations

import shutil
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from pathlib import Path


# Allowed FFmpeg binary names for security validation
ALLOWED_FFMPEG_BINARIES = frozenset({
    "ffmpeg", "ffmpeg.exe",
    "ffprobe", "ffprobe.exe",
})

# Allowed paths where FFmpeg binaries can be located (in addition to PATH)
ALLOWED_FFMPEG_PATHS = frozenset({
    # Common Windows locations
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffprobe.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
    # Common Unix locations
    "/usr/bin/ffmpeg",
    "/usr/bin/ffprobe",
    "/usr/local/bin/ffmpeg",
    "/usr/local/bin/ffprobe",
    "/opt/homebrew/bin/ffmpeg",
    "/opt/homebrew/bin/ffprobe",
})


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.

    All settings can be overridden with environment variables using the aliases
    or the field names in uppercase (e.g., PROVIDER, LLM_PROVIDER).
    """
    # LLM Configuration
    provider: str = Field("anthropic", alias="LLM_PROVIDER")
    model: str = Field("claude-3-5-sonnet-20241022", alias="LLM_MODEL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    replicate_api_token: str | None = Field(default=None, alias="REPLICATE_API_TOKEN")

    # Tokenization / Context
    model_context_window: int = Field(128000, alias="LLM_CONTEXT_WINDOW")
    token_safety_margin: int = Field(512, alias="LLM_TOKEN_SAFETY_MARGIN")
    openai_encoding: str = Field("o200k_base", alias="OPENAI_TIKTOKEN_ENCODING")

    # Summarization Settings
    summary_max_tokens: int = Field(3000, alias="SUMMARY_MAX_OUTPUT_TOKENS")
    summary_chunk_seconds: int = Field(1800, alias="SUMMARY_CHUNK_SECONDS")
    summary_cod_passes: int = Field(2, alias="SUMMARY_COD_PASSES")
    summary_template: str = Field("default", alias="SUMMARY_TEMPLATE")
    summary_auto_detect: bool = Field(True, alias="SUMMARY_AUTO_DETECT_TEMPLATE")

    # Extended Thinking Settings
    thinking_budget_default: int = Field(4000, alias="THINKING_BUDGET_DEFAULT")
    thinking_budget_extended: int = Field(6000, alias="THINKING_BUDGET_EXTENDED")

    # Audio Processing
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    max_upload_mb: float = Field(24.0, alias="MAX_UPLOAD_MB")
    audio_quality_high_bitrate: str = Field("192k", alias="AUDIO_HIGH_BITRATE")
    audio_quality_medium_bitrate: str = Field("128k", alias="AUDIO_MEDIUM_BITRATE")
    audio_quality_low_bitrate: str = Field("64k", alias="AUDIO_LOW_BITRATE")

    # Data Organization - New Structure
    data_dir: Path = Path("data")
    video_dir: Path = Field(default_factory=lambda: Path("data/video"))
    audio_dir: Path = Field(default_factory=lambda: Path("data/audio"))
    transcript_dir: Path = Field(default_factory=lambda: Path("data/transcript"))
    temp_dir: Path = Field(default_factory=lambda: Path("data/temp"))
    jobs_dir: Path = Field(default_factory=lambda: Path("data/jobs"))

    # Legacy support (for backward compatibility)
    input_dir: Path = Field(default_factory=lambda: Path("data/input"))
    output_dir: Path = Field(default_factory=lambda: Path("data/output"))
    # DEPRECATED: Use output_dir instead. out_dir is kept for backward compatibility only.
    out_dir: Path = Field(default_factory=lambda: Path("data/output"))

    # Environment Settings
    environment: str = Field("development", alias="ENVIRONMENT")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # Job Management
    max_concurrent_jobs: int = Field(3, alias="MAX_CONCURRENT_JOBS")
    job_history_days: int = Field(30, alias="JOB_HISTORY_DAYS")
    temp_cleanup_hours: int = Field(24, alias="TEMP_CLEANUP_HOURS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator('ffmpeg_bin', 'ffprobe_bin', mode='after')
    @classmethod
    def validate_ffmpeg_binary(cls, v: str) -> str:
        """
        Validate FFmpeg binary path for security.

        Prevents command injection by validating the binary is either:
        1. A simple binary name that will be found in PATH
        2. A known safe absolute path
        """
        if not v:
            raise ValueError("FFmpeg binary path cannot be empty")

        # Check if it's just a binary name (will use PATH lookup)
        if v in ALLOWED_FFMPEG_BINARIES:
            # Verify the binary exists in PATH
            if shutil.which(v) is not None:
                return v
            # Binary name is valid but not found - allow with warning
            return v

        # Check if it's a known safe absolute path
        if v in ALLOWED_FFMPEG_PATHS:
            return v

        # Check if it looks like a path
        if '/' in v or '\\' in v:
            # It's a path - check against allowlist
            # Also try resolving to catch symlinks
            try:
                resolved = str(Path(v).resolve())
                if resolved in ALLOWED_FFMPEG_PATHS or v in ALLOWED_FFMPEG_PATHS:
                    return v
            except (OSError, ValueError):
                pass

            raise ValueError(
                f"FFmpeg binary path '{v}' is not in the allowed paths list. "
                f"Use a simple binary name like 'ffmpeg' or add the path to ALLOWED_FFMPEG_PATHS."
            )

        # Unknown binary name - reject
        raise ValueError(
            f"Unknown FFmpeg binary name '{v}'. "
            f"Allowed binary names: {', '.join(sorted(ALLOWED_FFMPEG_BINARIES))}"
        )


def _validate_ffmpeg_path(path: str, binary_type: str) -> str:
    """
    Validate an FFmpeg binary path.

    Args:
        path: Path to validate
        binary_type: 'ffmpeg' or 'ffprobe' for error messages

    Returns:
        Validated path

    Raises:
        ValueError: If path is invalid or unsafe
    """
    if not path:
        raise ValueError(f"{binary_type} path cannot be empty")

    # Simple binary name - validate and allow PATH lookup
    if path in ALLOWED_FFMPEG_BINARIES:
        return path

    # Known safe path
    if path in ALLOWED_FFMPEG_PATHS:
        return path

    # Reject anything else with paths
    if '/' in path or '\\' in path:
        raise ValueError(
            f"Unsafe {binary_type} path: '{path}'. "
            f"Use 'ffmpeg'/'ffprobe' or add to ALLOWED_FFMPEG_PATHS."
        )

    raise ValueError(f"Unknown {binary_type} binary: '{path}'")


# Global settings instance - automatically loads from environment and .env file
SETTINGS = Settings()


def mask_api_key(api_key: str | None) -> str:
    """
    Mask an API key for safe display.

    Shows only the provider prefix (e.g. ``sk-``, ``sk-ant-``, ``r8_``)
    followed by ``***configured***``.  Never reveals suffix characters.

    Args:
        api_key: API key to mask

    Returns:
        Masked API key string
    """
    if not api_key:
        return "Not configured"

    # Identify known provider prefixes
    for prefix in ("sk-ant-", "sk-proj-", "sk-", "r8_"):
        if api_key.startswith(prefix):
            return f"{prefix}***configured***"

    # Unknown format – show nothing
    return "***configured***"


def get_configuration_summary() -> dict:
    """
    Get a summary of all configuration for display.

    Returns:
        Dictionary with all configuration values (sensitive values masked)
    """
    return {
        'provider': SETTINGS.provider,
        'model': SETTINGS.model,
        'output_directory': str(SETTINGS.output_dir),
        'data_directory': str(SETTINGS.data_dir),
        'temp_directory': str(SETTINGS.temp_dir),
        'ffmpeg_binary': SETTINGS.ffmpeg_bin,
        'ffprobe_binary': SETTINGS.ffprobe_bin,
        'summary_max_tokens': SETTINGS.summary_max_tokens,
        'summary_chunk_seconds': SETTINGS.summary_chunk_seconds,
        'summary_cod_passes': SETTINGS.summary_cod_passes,
        'transcription_model': 'thomasmol/whisper-diarization',  # Default transcription model
        'openai_api_key': mask_api_key(SETTINGS.openai_api_key),
        'anthropic_api_key': mask_api_key(SETTINGS.anthropic_api_key),
        'replicate_api_token': mask_api_key(SETTINGS.replicate_api_token)
    }


def validate_provider_config(provider: str) -> bool:
    """
    Validate that required configuration is available for a provider.

    Args:
        provider: Provider name to validate

    Returns:
        True if configuration is valid, False otherwise
    """
    import logging
    log = logging.getLogger(__name__)

    key_map = {
        'openai': SETTINGS.openai_api_key,
        'anthropic': SETTINGS.anthropic_api_key,
        'replicate': SETTINGS.replicate_api_token
    }
    api_key = key_map.get(provider.lower())

    if not api_key:
        log.warning(f"No API key configured for provider: {provider}")
        return False

    return True
