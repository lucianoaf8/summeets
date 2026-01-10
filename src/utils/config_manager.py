"""
DEPRECATED: This module is deprecated. Import from config.py instead.

Centralized configuration management.
This module now re-exports from config.py for backward compatibility.
"""
import warnings
import logging
from typing import Optional, Any, Dict
from pathlib import Path

# Re-export from config.py
from .config import SETTINGS, get_configuration_summary, validate_provider_config, mask_api_key

log = logging.getLogger(__name__)


def _deprecation_warning():
    """Emit deprecation warning for this module."""
    warnings.warn(
        "config_manager module is deprecated. Import from src.utils.config instead.",
        DeprecationWarning,
        stacklevel=3
    )


class ConfigManager:
    """
    DEPRECATED: Use SETTINGS from config.py directly.

    Centralized configuration manager providing controlled access to settings.
    """

    def __init__(self):
        _deprecation_warning()
        self._settings = SETTINGS
        self._overrides = {}

    # Provider settings
    @property
    def provider(self) -> str:
        """Get the current LLM provider."""
        return self._get_value('provider', 'openai')

    @property
    def model(self) -> str:
        """Get the current model name."""
        return self._get_value('model', 'gpt-4o-mini')

    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key."""
        return self._get_value('openai_api_key')

    @property
    def anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key."""
        return self._get_value('anthropic_api_key')

    @property
    def replicate_api_token(self) -> Optional[str]:
        """Get Replicate API token."""
        return self._get_value('replicate_api_token')

    # File paths and directories
    @property
    def output_directory(self) -> Path:
        """Get the output directory."""
        return Path(self._get_value('out_dir', './data/output'))

    @property
    def data_directory(self) -> Path:
        """Get the data directory."""
        return Path(self._get_value('data_dir', './data'))

    @property
    def temp_directory(self) -> Path:
        """Get the temporary files directory."""
        return Path(self._get_value('temp_dir', './data/temp'))

    # Audio processing settings
    @property
    def ffmpeg_binary(self) -> str:
        """Get FFmpeg binary path."""
        return self._get_value('ffmpeg_bin', 'ffmpeg')

    @property
    def ffprobe_binary(self) -> str:
        """Get FFprobe binary path."""
        return self._get_value('ffprobe_bin', 'ffprobe')

    # Summary settings
    @property
    def summary_max_tokens(self) -> int:
        """Get maximum tokens for summaries."""
        return self._get_value('summary_max_tokens', 3000)

    @property
    def summary_chunk_seconds(self) -> int:
        """Get chunk size for summarization in seconds."""
        return self._get_value('summary_chunk_seconds', 1800)

    @property
    def summary_cod_passes(self) -> int:
        """Get number of Chain-of-Density passes."""
        return self._get_value('summary_cod_passes', 2)

    # Transcription settings
    @property
    def transcription_model(self) -> str:
        """Get transcription model name."""
        return self._get_value('transcription_model', 'thomasmol/whisper-diarization')

    # Utility methods
    def get_api_key_for_provider(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider."""
        key_map = {
            'openai': self.openai_api_key,
            'anthropic': self.anthropic_api_key,
            'replicate': self.replicate_api_token
        }
        return key_map.get(provider.lower())

    def validate_provider_config(self, provider: str) -> bool:
        """Validate that required configuration is available for a provider."""
        return validate_provider_config(provider)

    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as a dictionary for display purposes."""
        return get_configuration_summary()

    def set_override(self, key: str, value: Any) -> None:
        """Set a temporary override for a configuration value."""
        self._overrides[key] = value
        log.debug(f"Set configuration override: {key}")

    def clear_override(self, key: str) -> None:
        """Clear a configuration override."""
        if key in self._overrides:
            del self._overrides[key]
            log.debug(f"Cleared configuration override: {key}")

    def clear_all_overrides(self) -> None:
        """Clear all configuration overrides."""
        self._overrides.clear()
        log.debug("Cleared all configuration overrides")

    def _get_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with override support."""
        # Check overrides first
        if key in self._overrides:
            return self._overrides[key]

        # Get from settings
        try:
            return getattr(self._settings, key, default)
        except AttributeError:
            if default is not None:
                return default
            from .exceptions import ConfigurationError
            raise ConfigurationError(f"Configuration key not found: {key}")

    def _mask_api_key(self, api_key: Optional[str]) -> str:
        """Mask an API key for safe display."""
        return mask_api_key(api_key)


# Global configuration manager instance (deprecated)
config_manager = ConfigManager()


# Convenience functions for common operations (deprecated - use config.py)
def get_provider() -> str:
    """DEPRECATED: Use SETTINGS.provider directly."""
    _deprecation_warning()
    return SETTINGS.provider


def get_model() -> str:
    """DEPRECATED: Use SETTINGS.model directly."""
    _deprecation_warning()
    return SETTINGS.model


def get_api_key(provider: str) -> Optional[str]:
    """DEPRECATED: Use SETTINGS.<provider>_api_key directly."""
    _deprecation_warning()
    key_map = {
        'openai': SETTINGS.openai_api_key,
        'anthropic': SETTINGS.anthropic_api_key,
        'replicate': SETTINGS.replicate_api_token
    }
    return key_map.get(provider.lower())


def get_output_directory() -> Path:
    """DEPRECATED: Use SETTINGS.out_dir directly."""
    _deprecation_warning()
    return SETTINGS.out_dir


def get_ffmpeg_binary() -> str:
    """DEPRECATED: Use SETTINGS.ffmpeg_bin directly."""
    _deprecation_warning()
    return SETTINGS.ffmpeg_bin


def get_ffprobe_binary() -> str:
    """DEPRECATED: Use SETTINGS.ffprobe_bin directly."""
    _deprecation_warning()
    return SETTINGS.ffprobe_bin


def validate_configuration() -> bool:
    """DEPRECATED: Use validate_provider_config from config.py."""
    _deprecation_warning()
    return validate_provider_config(SETTINGS.provider)
