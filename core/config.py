"""
Application configuration using Pydantic Settings.
Manages environment variables and default settings for Summeets.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    
    All settings can be overridden with environment variables using the aliases
    or the field names in uppercase (e.g., PROVIDER, LLM_PROVIDER).
    """
    # LLM Configuration
    provider: str = Field("openai", alias="LLM_PROVIDER")
    model: str = Field("gpt-4o-mini", alias="LLM_MODEL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    replicate_api_token: str | None = Field(default=None, alias="REPLICATE_API_TOKEN")
    
    # Summarization Settings
    summary_max_tokens: int = Field(3000, alias="SUMMARY_MAX_OUTPUT_TOKENS")
    summary_chunk_seconds: int = Field(1800, alias="SUMMARY_CHUNK_SECONDS")
    summary_cod_passes: int = Field(2, alias="SUMMARY_COD_PASSES")
    
    # Audio Processing
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    max_upload_mb: float = Field(24.0, alias="MAX_UPLOAD_MB")
    
    # Data Organization
    data_dir: Path = Path("data")
    input_dir: Path = Field(default_factory=lambda: Path("data/input"))
    output_dir: Path = Field(default_factory=lambda: Path("data/output"))
    temp_dir: Path = Field(default_factory=lambda: Path("data/temp"))
    jobs_dir: Path = Field(default_factory=lambda: Path("data/jobs"))
    
    # Legacy support
    out_dir: Path = Field(default_factory=lambda: Path("data/output"))
    
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

# Global settings instance - automatically loads from environment and .env file
SETTINGS = Settings()