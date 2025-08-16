"""
Centralized configuration management.
Provides a clean interface for accessing configuration values.
"""
import logging
from typing import Optional, Any, Dict
from pathlib import Path

from .config import SETTINGS
from .exceptions import ConfigurationError

log = logging.getLogger(__name__)


class ConfigManager:
    """
    Centralized configuration manager providing controlled access to settings.
    """
    
    def __init__(self):
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
        """
        Get API key for a specific provider.
        
        Args:
            provider: Provider name ('openai', 'anthropic', 'replicate')
            
        Returns:
            API key if available, None otherwise
        """
        key_map = {
            'openai': self.openai_api_key,
            'anthropic': self.anthropic_api_key,
            'replicate': self.replicate_api_token
        }
        return key_map.get(provider.lower())
    
    def validate_provider_config(self, provider: str) -> bool:
        """
        Validate that required configuration is available for a provider.
        
        Args:
            provider: Provider name to validate
            
        Returns:
            True if configuration is valid, False otherwise
        """
        api_key = self.get_api_key_for_provider(provider)
        if not api_key:
            log.warning(f"No API key configured for provider: {provider}")
            return False
        
        return True
    
    def get_all_config(self) -> Dict[str, Any]:
        """
        Get all configuration as a dictionary for display purposes.
        
        Returns:
            Dictionary with all configuration values (sensitive values masked)
        """
        return {
            'provider': self.provider,
            'model': self.model,
            'output_directory': str(self.output_directory),
            'data_directory': str(self.data_directory),
            'temp_directory': str(self.temp_directory),
            'ffmpeg_binary': self.ffmpeg_binary,
            'ffprobe_binary': self.ffprobe_binary,
            'summary_max_tokens': self.summary_max_tokens,
            'summary_chunk_seconds': self.summary_chunk_seconds,
            'summary_cod_passes': self.summary_cod_passes,
            'transcription_model': self.transcription_model,
            'openai_api_key': self._mask_api_key(self.openai_api_key),
            'anthropic_api_key': self._mask_api_key(self.anthropic_api_key),
            'replicate_api_token': self._mask_api_key(self.replicate_api_token)
        }
    
    def set_override(self, key: str, value: Any) -> None:
        """
        Set a temporary override for a configuration value.
        
        Args:
            key: Configuration key
            value: Override value
        """
        self._overrides[key] = value
        log.debug(f"Set configuration override: {key}")
    
    def clear_override(self, key: str) -> None:
        """
        Clear a configuration override.
        
        Args:
            key: Configuration key to clear
        """
        if key in self._overrides:
            del self._overrides[key]
            log.debug(f"Cleared configuration override: {key}")
    
    def clear_all_overrides(self) -> None:
        """Clear all configuration overrides."""
        self._overrides.clear()
        log.debug("Cleared all configuration overrides")
    
    def _get_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value with override support.
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        # Check overrides first
        if key in self._overrides:
            return self._overrides[key]
        
        # Get from settings
        try:
            return getattr(self._settings, key, default)
        except AttributeError:
            if default is not None:
                return default
            raise ConfigurationError(f"Configuration key not found: {key}")
    
    def _mask_api_key(self, api_key: Optional[str]) -> str:
        """
        Mask an API key for safe display.
        
        Args:
            api_key: API key to mask
            
        Returns:
            Masked API key string
        """
        if not api_key:
            return "Not configured"
        
        if len(api_key) <= 8:
            return "*" * len(api_key)
        
        return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]


# Global configuration manager instance
config_manager = ConfigManager()


# Convenience functions for common operations
def get_provider() -> str:
    """Get the current LLM provider."""
    return config_manager.provider


def get_model() -> str:
    """Get the current model name."""
    return config_manager.model


def get_api_key(provider: str) -> Optional[str]:
    """Get API key for a provider."""
    return config_manager.get_api_key_for_provider(provider)


def get_output_directory() -> Path:
    """Get the output directory."""
    return config_manager.output_directory


def get_ffmpeg_binary() -> str:
    """Get FFmpeg binary path."""
    return config_manager.ffmpeg_binary


def get_ffprobe_binary() -> str:
    """Get FFprobe binary path."""
    return config_manager.ffprobe_binary


def validate_configuration() -> bool:
    """
    Validate that all required configuration is available.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    provider = get_provider()
    return config_manager.validate_provider_config(provider)


def get_configuration_summary() -> Dict[str, Any]:
    """Get a summary of all configuration for display."""
    return config_manager.get_all_config()