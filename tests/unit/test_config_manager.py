"""
Unit tests for configuration manager.
Tests centralized configuration access and management.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.utils.config_manager import (
    ConfigManager, config_manager,
    get_provider, get_model, get_api_key, get_output_directory,
    get_ffmpeg_binary, get_ffprobe_binary, validate_configuration,
    get_configuration_summary
)
from src.utils.exceptions import ConfigurationError


class TestConfigManager:
    """Test the ConfigManager class."""
    
    def test_initialization(self):
        """Test ConfigManager initialization."""
        manager = ConfigManager()
        
        assert manager._settings is not None
        assert isinstance(manager._overrides, dict)
        assert len(manager._overrides) == 0
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_provider_property(self, mock_settings):
        """Test provider property access."""
        mock_settings.provider = "anthropic"
        manager = ConfigManager()
        
        assert manager.provider == "anthropic"
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_provider_property_default(self, mock_settings):
        """Test provider property with default value."""
        # Simulate missing provider setting
        del mock_settings.provider
        manager = ConfigManager()
        
        assert manager.provider == "openai"  # default value
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_model_property(self, mock_settings):
        """Test model property access."""
        mock_settings.model = "gpt-4o"
        manager = ConfigManager()
        
        assert manager.model == "gpt-4o"
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_model_property_default(self, mock_settings):
        """Test model property with default value."""
        del mock_settings.model
        manager = ConfigManager()
        
        assert manager.model == "gpt-4o-mini"  # default value
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_api_key_properties(self, mock_settings):
        """Test API key properties."""
        mock_settings.openai_api_key = "sk-test-openai"
        mock_settings.anthropic_api_key = "sk-ant-test"
        mock_settings.replicate_api_token = "r8_test"
        
        manager = ConfigManager()
        
        assert manager.openai_api_key == "sk-test-openai"
        assert manager.anthropic_api_key == "sk-ant-test"
        assert manager.replicate_api_token == "r8_test"
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_path_properties(self, mock_settings):
        """Test path properties."""
        mock_settings.out_dir = "/custom/output"
        mock_settings.data_dir = "/custom/data"
        mock_settings.temp_dir = "/custom/temp"
        
        manager = ConfigManager()
        
        assert manager.output_directory == Path("/custom/output")
        assert manager.data_directory == Path("/custom/data")
        assert manager.temp_directory == Path("/custom/temp")
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_path_properties_defaults(self, mock_settings):
        """Test path properties with default values."""
        del mock_settings.out_dir
        del mock_settings.data_dir
        del mock_settings.temp_dir
        
        manager = ConfigManager()
        
        assert manager.output_directory == Path("./data/output")
        assert manager.data_directory == Path("./data")
        assert manager.temp_directory == Path("./data/temp")
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_ffmpeg_properties(self, mock_settings):
        """Test FFmpeg properties."""
        mock_settings.ffmpeg_bin = "/usr/bin/ffmpeg"
        mock_settings.ffprobe_bin = "/usr/bin/ffprobe"
        
        manager = ConfigManager()
        
        assert manager.ffmpeg_binary == "/usr/bin/ffmpeg"
        assert manager.ffprobe_binary == "/usr/bin/ffprobe"
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_summary_properties(self, mock_settings):
        """Test summary configuration properties."""
        mock_settings.summary_max_tokens = 4000
        mock_settings.summary_chunk_seconds = 900
        mock_settings.summary_cod_passes = 3
        
        manager = ConfigManager()
        
        assert manager.summary_max_tokens == 4000
        assert manager.summary_chunk_seconds == 900
        assert manager.summary_cod_passes == 3
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_transcription_properties(self, mock_settings):
        """Test transcription configuration properties."""
        mock_settings.transcription_model = "custom/model"
        
        manager = ConfigManager()
        
        assert manager.transcription_model == "custom/model"
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_get_api_key_for_provider(self, mock_settings):
        """Test getting API key for specific providers."""
        mock_settings.openai_api_key = "sk-openai"
        mock_settings.anthropic_api_key = "sk-ant"
        mock_settings.replicate_api_token = "r8_token"
        
        manager = ConfigManager()
        
        assert manager.get_api_key_for_provider("openai") == "sk-openai"
        assert manager.get_api_key_for_provider("anthropic") == "sk-ant"
        assert manager.get_api_key_for_provider("replicate") == "r8_token"
        assert manager.get_api_key_for_provider("unknown") is None
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_get_api_key_for_provider_case_insensitive(self, mock_settings):
        """Test API key retrieval is case insensitive."""
        mock_settings.openai_api_key = "sk-openai"
        
        manager = ConfigManager()
        
        assert manager.get_api_key_for_provider("OpenAI") == "sk-openai"
        assert manager.get_api_key_for_provider("OPENAI") == "sk-openai"
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_validate_provider_config_valid(self, mock_settings):
        """Test provider configuration validation with valid key."""
        mock_settings.openai_api_key = "sk-valid-key"
        
        manager = ConfigManager()
        
        assert manager.validate_provider_config("openai") is True
    
    @patch('core.utils.config_manager.SETTINGS')
    @patch('core.utils.config_manager.log')
    def test_validate_provider_config_invalid(self, mock_log, mock_settings):
        """Test provider configuration validation with invalid key."""
        mock_settings.openai_api_key = ""
        
        manager = ConfigManager()
        
        assert manager.validate_provider_config("openai") is False
        mock_log.warning.assert_called_once()
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_get_all_config(self, mock_settings):
        """Test getting all configuration values."""
        mock_settings.provider = "openai"
        mock_settings.model = "gpt-4o"
        mock_settings.openai_api_key = "sk-test-key-12345678"
        mock_settings.anthropic_api_key = ""
        mock_settings.replicate_api_token = None
        
        manager = ConfigManager()
        config = manager.get_all_config()
        
        assert config["provider"] == "openai"
        assert config["model"] == "gpt-4o"
        assert config["openai_api_key"] == "sk-t****5678"  # masked
        assert config["anthropic_api_key"] == "Not configured"
        assert config["replicate_api_token"] == "Not configured"
    
    def test_mask_api_key(self):
        """Test API key masking functionality."""
        manager = ConfigManager()
        
        # Test normal key
        masked = manager._mask_api_key("sk-test-key-12345678")
        assert masked == "sk-t****5678"
        
        # Test short key
        masked_short = manager._mask_api_key("short")
        assert masked_short == "*****"
        
        # Test empty key
        masked_empty = manager._mask_api_key("")
        assert masked_empty == "Not configured"
        
        # Test None key
        masked_none = manager._mask_api_key(None)
        assert masked_none == "Not configured"
    
    def test_overrides(self):
        """Test configuration overrides."""
        manager = ConfigManager()
        
        # Set override
        manager.set_override("provider", "test_provider")
        assert manager._get_value("provider") == "test_provider"
        
        # Clear specific override
        manager.clear_override("provider")
        assert "provider" not in manager._overrides
        
        # Set multiple overrides and clear all
        manager.set_override("provider", "test1")
        manager.set_override("model", "test2")
        manager.clear_all_overrides()
        assert len(manager._overrides) == 0
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_get_value_with_overrides(self, mock_settings):
        """Test _get_value method with overrides."""
        mock_settings.provider = "openai"
        
        manager = ConfigManager()
        
        # Normal value
        assert manager._get_value("provider") == "openai"
        
        # Override value
        manager.set_override("provider", "anthropic")
        assert manager._get_value("provider") == "anthropic"
        
        # Default value
        assert manager._get_value("nonexistent", "default") == "default"
    
    def test_get_value_missing_key(self):
        """Test _get_value with missing key and no default."""
        manager = ConfigManager()
        
        with pytest.raises(ConfigurationError, match="Configuration key not found"):
            manager._get_value("nonexistent_key")


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('core.utils.config_manager.config_manager')
    def test_get_provider(self, mock_manager):
        """Test get_provider convenience function."""
        mock_manager.provider = "anthropic"
        
        result = get_provider()
        
        assert result == "anthropic"
    
    @patch('core.utils.config_manager.config_manager')
    def test_get_model(self, mock_manager):
        """Test get_model convenience function."""
        mock_manager.model = "claude-3-haiku"
        
        result = get_model()
        
        assert result == "claude-3-haiku"
    
    @patch('core.utils.config_manager.config_manager')
    def test_get_api_key(self, mock_manager):
        """Test get_api_key convenience function."""
        mock_manager.get_api_key_for_provider.return_value = "sk-test"
        
        result = get_api_key("openai")
        
        mock_manager.get_api_key_for_provider.assert_called_once_with("openai")
        assert result == "sk-test"
    
    @patch('core.utils.config_manager.config_manager')
    def test_get_output_directory(self, mock_manager):
        """Test get_output_directory convenience function."""
        mock_manager.output_directory = Path("/test/output")
        
        result = get_output_directory()
        
        assert result == Path("/test/output")
    
    @patch('core.utils.config_manager.config_manager')
    def test_get_ffmpeg_binary(self, mock_manager):
        """Test get_ffmpeg_binary convenience function."""
        mock_manager.ffmpeg_binary = "/usr/bin/ffmpeg"
        
        result = get_ffmpeg_binary()
        
        assert result == "/usr/bin/ffmpeg"
    
    @patch('core.utils.config_manager.config_manager')
    def test_get_ffprobe_binary(self, mock_manager):
        """Test get_ffprobe_binary convenience function."""
        mock_manager.ffprobe_binary = "/usr/bin/ffprobe"
        
        result = get_ffprobe_binary()
        
        assert result == "/usr/bin/ffprobe"
    
    @patch('core.utils.config_manager.config_manager')
    def test_validate_configuration(self, mock_manager):
        """Test validate_configuration convenience function."""
        mock_manager.provider = "openai"
        mock_manager.validate_provider_config.return_value = True
        
        result = validate_configuration()
        
        mock_manager.validate_provider_config.assert_called_once_with("openai")
        assert result is True
    
    @patch('core.utils.config_manager.config_manager')
    def test_get_configuration_summary(self, mock_manager):
        """Test get_configuration_summary convenience function."""
        expected_summary = {"provider": "openai", "model": "gpt-4o"}
        mock_manager.get_all_config.return_value = expected_summary
        
        result = get_configuration_summary()
        
        mock_manager.get_all_config.assert_called_once()
        assert result == expected_summary


class TestGlobalConfigManagerInstance:
    """Test the global config_manager instance."""
    
    def test_global_instance_exists(self):
        """Test that the global config_manager instance exists."""
        assert config_manager is not None
        assert isinstance(config_manager, ConfigManager)
    
    def test_global_instance_is_singleton(self):
        """Test that imports reference the same instance."""
        from src.utils.config_manager import config_manager as imported_manager
        
        assert imported_manager is config_manager


class TestErrorHandling:
    """Test error handling in configuration management."""
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_missing_settings_attribute(self, mock_settings):
        """Test handling of missing settings attributes."""
        # Remove an attribute that should exist
        if hasattr(mock_settings, 'provider'):
            del mock_settings.provider
        
        manager = ConfigManager()
        
        # Should return default value
        assert manager._get_value('provider', 'default') == 'default'
    
    def test_configuration_error_for_missing_required_key(self):
        """Test ConfigurationError for missing required configuration."""
        manager = ConfigManager()
        
        with pytest.raises(ConfigurationError):
            manager._get_value('required_but_missing_key')
    
    @patch('core.utils.config_manager.log')
    def test_logging_for_invalid_provider(self, mock_log):
        """Test logging when validating invalid provider configuration."""
        manager = ConfigManager()
        manager.set_override('openai_api_key', '')  # Empty API key
        
        result = manager.validate_provider_config('openai')
        
        assert result is False
        mock_log.warning.assert_called_once()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_string_api_keys(self):
        """Test handling of empty string API keys."""
        manager = ConfigManager()
        manager.set_override('openai_api_key', '')
        
        api_key = manager.get_api_key_for_provider('openai')
        assert api_key == ''
        
        # Should fail validation
        assert manager.validate_provider_config('openai') is False
    
    def test_none_api_keys(self):
        """Test handling of None API keys."""
        manager = ConfigManager()
        manager.set_override('openai_api_key', None)
        
        api_key = manager.get_api_key_for_provider('openai')
        assert api_key is None
        
        # Should fail validation
        assert manager.validate_provider_config('openai') is False
    
    def test_case_variations_in_provider_names(self):
        """Test various case combinations for provider names."""
        manager = ConfigManager()
        manager.set_override('openai_api_key', 'sk-test')
        
        # Test different case variations
        assert manager.get_api_key_for_provider('openai') == 'sk-test'
        assert manager.get_api_key_for_provider('OpenAI') == 'sk-test'
        assert manager.get_api_key_for_provider('OPENAI') == 'sk-test'
        assert manager.get_api_key_for_provider('OpenAi') == 'sk-test'
    
    def test_very_long_api_key_masking(self):
        """Test masking of very long API keys."""
        manager = ConfigManager()
        long_key = "sk-" + "x" * 100 + "end"
        
        masked = manager._mask_api_key(long_key)
        
        assert masked.startswith("sk-x")
        assert masked.endswith("end")
        assert "****" in masked
        assert len(masked) < len(long_key)
    
    def test_override_with_none_value(self):
        """Test setting override with None value."""
        manager = ConfigManager()
        
        manager.set_override('test_key', None)
        assert manager._get_value('test_key') is None
        
        # Should be able to get default when override is None
        assert manager._get_value('test_key', 'default') is None
    
    @patch('core.utils.config_manager.SETTINGS')
    def test_path_property_with_string_input(self, mock_settings):
        """Test path properties convert strings to Path objects."""
        mock_settings.out_dir = "/string/path"
        
        manager = ConfigManager()
        
        result = manager.output_directory
        assert isinstance(result, Path)
        assert str(result) == "/string/path"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])