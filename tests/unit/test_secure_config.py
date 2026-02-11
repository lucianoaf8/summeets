"""Unit tests for SecureConfigManager."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.utils.secure_config import SecureConfigManager, SECURE_KEYS


@pytest.fixture
def env_file(tmp_path):
    """Create a temporary .env file path for testing."""
    return tmp_path / ".env"


@pytest.fixture
def mock_keyring_unavailable():
    """Mock keyring as unavailable."""
    with patch("src.utils.secure_config.KEYRING_AVAILABLE", False):
        yield


@pytest.fixture
def mock_keyring_available():
    """Mock keyring as available with mock keyring module."""
    mock_kr = MagicMock()
    mock_kr.get_password.return_value = None  # default: nothing stored
    with patch("src.utils.secure_config.KEYRING_AVAILABLE", True), \
         patch("src.utils.secure_config.keyring", mock_kr):
        yield mock_kr


def test_init_creates_instance(env_file):
    """SecureConfigManager initializes successfully with custom env_path."""
    manager = SecureConfigManager(env_path=env_file)
    assert manager is not None
    assert manager.env_path == env_file


def test_load_env_parses_file(env_file):
    """_load_env correctly parses .env file content."""
    env_file.write_text(
        "KEY1=value1\n"
        "KEY2=value2\n"
        "KEY3=value3\n"
    )
    manager = SecureConfigManager(env_path=env_file)
    assert manager._env_cache["KEY1"] == "value1"
    assert manager._env_cache["KEY2"] == "value2"
    assert manager._env_cache["KEY3"] == "value3"


def test_load_env_strips_comments(env_file):
    """Lines with # prefix are ignored."""
    env_file.write_text(
        "KEY1=value1\n"
        "# This is a comment\n"
        "KEY2=value2\n"
        "# Another comment\n"
    )
    manager = SecureConfigManager(env_path=env_file)
    assert "KEY1" in manager._env_cache
    assert "KEY2" in manager._env_cache
    assert len([k for k in manager._env_cache if k.startswith("#")]) == 0


def test_load_env_strips_quotes(env_file):
    """Values wrapped in quotes have quotes stripped."""
    env_file.write_text(
        'KEY1="value1"\n'
        "KEY2='value2'\n"
        "KEY3=no_quotes\n"
    )
    manager = SecureConfigManager(env_path=env_file)
    assert manager._env_cache["KEY1"] == "value1"
    assert manager._env_cache["KEY2"] == "value2"
    assert manager._env_cache["KEY3"] == "no_quotes"


def test_get_api_key_from_env(env_file, mock_keyring_unavailable):
    """With keyring unavailable, get_api_key reads from _env_cache."""
    env_file.write_text("OPENAI_API_KEY=sk-test123\n")
    manager = SecureConfigManager(env_path=env_file)
    api_key = manager.get_api_key("OPENAI_API_KEY")
    assert api_key == "sk-test123"


def test_get_api_key_unknown_key_raises(env_file, mock_keyring_unavailable):
    """get_api_key raises ValueError for unknown keys."""
    manager = SecureConfigManager(env_path=env_file)
    with pytest.raises(ValueError, match="Unknown secure key"):
        manager.get_api_key("UNKNOWN_KEY")


def test_set_api_key_without_keyring(env_file, mock_keyring_unavailable):
    """set_api_key writes to .env when keyring unavailable, returns False."""
    manager = SecureConfigManager(env_path=env_file)
    result = manager.set_api_key("OPENAI_API_KEY", "sk-newkey123")

    assert result is False
    assert manager._env_cache["OPENAI_API_KEY"] == "sk-newkey123"


def test_set_api_key_with_keyring(env_file, mock_keyring_available):
    """set_api_key uses keyring when available, returns True."""
    manager = SecureConfigManager(env_path=env_file)
    result = manager.set_api_key("OPENAI_API_KEY", "sk-keyring123")

    assert result is True
    mock_keyring_available.set_password.assert_called_once_with(
        "summeets", "OPENAI_API_KEY", "sk-keyring123"
    )


def test_delete_api_key(env_file, mock_keyring_unavailable):
    """delete_api_key removes key from storage."""
    env_file.write_text("OPENAI_API_KEY=sk-test123\n")
    manager = SecureConfigManager(env_path=env_file)

    assert manager.get_api_key("OPENAI_API_KEY") == "sk-test123"

    result = manager.delete_api_key("OPENAI_API_KEY")
    assert result is True
    assert manager.get_api_key("OPENAI_API_KEY") is None


def test_get_setting_nonsecure(env_file, mock_keyring_unavailable):
    """get_setting for non-SECURE_KEYS reads from _env_cache."""
    env_file.write_text("LLM_PROVIDER=openai\nLLM_MODEL=gpt-4o\n")
    manager = SecureConfigManager(env_path=env_file)

    assert manager.get_setting("LLM_PROVIDER") == "openai"
    assert manager.get_setting("LLM_MODEL") == "gpt-4o"
    assert manager.get_setting("MISSING_KEY", "default") == "default"


def test_set_setting_nonsecure(env_file, mock_keyring_unavailable):
    """set_setting updates cache and saves for non-secure keys."""
    manager = SecureConfigManager(env_path=env_file)
    manager.set_setting("LLM_PROVIDER", "anthropic")

    assert manager._env_cache["LLM_PROVIDER"] == "anthropic"
    content = env_file.read_text()
    assert "LLM_PROVIDER=anthropic" in content


@pytest.mark.skipif(sys.platform == "win32", reason="chmod not applicable on Windows")
def test_save_env_sets_permissions(env_file, mock_keyring_unavailable):
    """After _save_env, file has 0o600 permissions (Unix only)."""
    manager = SecureConfigManager(env_path=env_file)
    manager.set_setting("TEST_KEY", "test_value")

    stat = env_file.stat()
    assert stat.st_mode & 0o777 == 0o600


def test_migrate_to_keyring(env_file, mock_keyring_available):
    """migrate_to_keyring moves keys from env_cache to keyring."""
    env_file.write_text(
        "OPENAI_API_KEY=sk-test123\n"
        "ANTHROPIC_API_KEY=sk-ant-test456\n"
        "LLM_PROVIDER=openai\n"
    )
    manager = SecureConfigManager(env_path=env_file)

    results = manager.migrate_to_keyring()

    # Keys that were present should have been migrated successfully
    assert results["OPENAI_API_KEY"] is True
    assert results["ANTHROPIC_API_KEY"] is True
    # REPLICATE_API_TOKEN wasn't in .env so nothing to migrate
    assert results["REPLICATE_API_TOKEN"] is True

    # keyring.set_password should have been called for the 2 present keys
    assert mock_keyring_available.set_password.call_count == 2

    # Keys should be removed from env_cache
    assert "OPENAI_API_KEY" not in manager._env_cache
    assert "ANTHROPIC_API_KEY" not in manager._env_cache
    # Non-secure key stays
    assert manager._env_cache["LLM_PROVIDER"] == "openai"


def test_get_all_settings_masks_keys(env_file, mock_keyring_unavailable):
    """API keys in get_all_settings output are masked."""
    env_file.write_text(
        "OPENAI_API_KEY=sk-proj-1234567890abcdefghij\n"
        "LLM_PROVIDER=openai\n"
    )
    manager = SecureConfigManager(env_path=env_file)

    all_settings = manager.get_all_settings()

    # API key should be masked
    assert "1234567890" not in all_settings.get("OPENAI_API_KEY", "")
    assert "configured" in all_settings.get("OPENAI_API_KEY", "").lower() or \
           "***" in all_settings.get("OPENAI_API_KEY", "")
    # Non-secure key should be plain
    assert all_settings["LLM_PROVIDER"] == "openai"


def test_has_api_key(env_file, mock_keyring_unavailable):
    """has_api_key returns True when key exists, False when missing."""
    env_file.write_text("OPENAI_API_KEY=sk-test123\n")
    manager = SecureConfigManager(env_path=env_file)

    assert manager.has_api_key("OPENAI_API_KEY") is True
    assert manager.has_api_key("ANTHROPIC_API_KEY") is False
