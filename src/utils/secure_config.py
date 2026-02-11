"""
Secure configuration management using system keyring.

Provides encrypted storage for API keys using the OS-native credential store:
- Windows: Credential Manager
- macOS: Keychain
- Linux: Secret Service / libsecret

Falls back to .env file with warnings for systems without keyring support.
"""
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

from .exceptions import ConfigurationError

log = logging.getLogger(__name__)

# Service name for keyring storage
KEYRING_SERVICE = "summeets"

# Keys that should be stored securely
SECURE_KEYS = frozenset({
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "REPLICATE_API_TOKEN",
})

# Try to import keyring, gracefully degrade if unavailable
try:
    import keyring
    from keyring.errors import KeyringError, PasswordSetError, PasswordDeleteError
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    log.warning("keyring library not installed. API keys will be stored in .env (less secure).")


class SecureConfigManager:
    """
    Manages secure storage of API keys and sensitive configuration.

    Uses system keyring for secure storage with .env fallback.
    Supports migration from .env to keyring storage.
    """

    def __init__(self, env_path: Optional[Path] = None):
        """
        Initialize the secure config manager.

        Args:
            env_path: Path to .env file for non-sensitive config and fallback
        """
        self.env_path = env_path or Path(".env")
        self._env_cache: Dict[str, str] = {}
        self._load_env()

    @property
    def keyring_available(self) -> bool:
        """Check if keyring storage is available."""
        return KEYRING_AVAILABLE

    def _load_env(self) -> None:
        """Load non-sensitive values from .env file."""
        self._env_cache = {}
        if self.env_path.exists():
            try:
                with open(self.env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            key = key.strip()
                            # Strip inline comments
                            if "#" in value:
                                value = value.split("#")[0]
                            value = value.strip().strip('"').strip("'")
                            self._env_cache[key] = value
            except OSError as e:
                log.warning(f"Failed to load .env: {e}")

    def get_api_key(self, key_name: str) -> Optional[str]:
        """
        Get an API key from secure storage.

        Args:
            key_name: Name of the key (e.g., "OPENAI_API_KEY")

        Returns:
            The API key value or None if not found
        """
        if key_name not in SECURE_KEYS:
            raise ValueError(f"Unknown secure key: {key_name}")

        # Try keyring first if available
        if KEYRING_AVAILABLE:
            try:
                value = keyring.get_password(KEYRING_SERVICE, key_name)
                if value:
                    return value
            except Exception as e:
                log.debug(f"Keyring lookup failed for {key_name}: {e}")

        # Fall back to .env
        value = self._env_cache.get(key_name)
        if value:
            if KEYRING_AVAILABLE:
                log.debug(f"Found {key_name} in .env, consider migrating to keyring")
        return value

    def set_api_key(self, key_name: str, value: str) -> bool:
        """
        Store an API key securely.

        Args:
            key_name: Name of the key
            value: The API key value

        Returns:
            True if stored in keyring, False if fell back to .env
        """
        if key_name not in SECURE_KEYS:
            raise ValueError(f"Unknown secure key: {key_name}")

        if not value:
            return self.delete_api_key(key_name)

        # Try keyring first
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(KEYRING_SERVICE, key_name, value)
                # Remove from .env if it exists there (migration)
                if key_name in self._env_cache:
                    del self._env_cache[key_name]
                    self._save_env()
                log.info(f"Stored {key_name} in system keyring")
                return True
            except Exception as e:
                log.warning(f"Failed to store {key_name} in keyring: {e}")

        # Fall back to .env
        self._env_cache[key_name] = value
        self._save_env()
        log.warning(f"Stored {key_name} in .env (less secure)")
        return False

    def delete_api_key(self, key_name: str) -> bool:
        """
        Delete an API key from storage.

        Args:
            key_name: Name of the key to delete

        Returns:
            True if deleted successfully
        """
        if key_name not in SECURE_KEYS:
            raise ValueError(f"Unknown secure key: {key_name}")

        deleted = False

        # Try keyring
        if KEYRING_AVAILABLE:
            try:
                keyring.delete_password(KEYRING_SERVICE, key_name)
                deleted = True
            except Exception:
                pass  # Key might not exist in keyring

        # Also remove from .env
        if key_name in self._env_cache:
            del self._env_cache[key_name]
            self._save_env()
            deleted = True

        return deleted

    def get_setting(self, key: str, default: str = "") -> str:
        """
        Get a non-sensitive setting.

        Args:
            key: Setting name
            default: Default value if not found

        Returns:
            Setting value
        """
        # For secure keys, use get_api_key
        if key in SECURE_KEYS:
            return self.get_api_key(key) or default

        return self._env_cache.get(key, default)

    def set_setting(self, key: str, value: str) -> None:
        """
        Set a non-sensitive setting.

        Args:
            key: Setting name
            value: Setting value
        """
        # For secure keys, use set_api_key
        if key in SECURE_KEYS:
            self.set_api_key(key, value)
            return

        if value:
            self._env_cache[key] = value
        elif key in self._env_cache:
            del self._env_cache[key]
        self._save_env()

    def _save_env(self) -> None:
        """Save non-sensitive settings to .env file."""
        try:
            lines = [
                "# Summeets Configuration",
                "# API keys are stored in system keyring for security",
                "",
            ]

            # Group settings by category
            llm_settings = ["LLM_PROVIDER", "LLM_MODEL"]
            summary_settings = ["SUMMARY_MAX_OUTPUT_TOKENS", "SUMMARY_CHUNK_SECONDS",
                              "SUMMARY_COD_PASSES", "SUMMARY_TEMPLATE"]
            env_settings = ["ENVIRONMENT", "LOG_LEVEL"]

            # LLM Settings
            llm_written = False
            for key in llm_settings:
                if key in self._env_cache:
                    if not llm_written:
                        lines.append("# LLM Provider")
                        llm_written = True
                    lines.append(f"{key}={self._env_cache[key]}")

            if llm_written:
                lines.append("")

            # Summary Settings
            summary_written = False
            for key in summary_settings:
                if key in self._env_cache:
                    if not summary_written:
                        lines.append("# Summarization Settings")
                        summary_written = True
                    lines.append(f"{key}={self._env_cache[key]}")

            if summary_written:
                lines.append("")

            # Environment Settings
            env_written = False
            for key in env_settings:
                if key in self._env_cache:
                    if not env_written:
                        lines.append("# Environment")
                        env_written = True
                    lines.append(f"{key}={self._env_cache[key]}")

            if env_written:
                lines.append("")

            # API keys - only write if keyring is not available
            if not KEYRING_AVAILABLE:
                api_written = False
                for key in SECURE_KEYS:
                    if key in self._env_cache:
                        if not api_written:
                            lines.append("# API Keys (WARNING: Consider using keyring for secure storage)")
                            api_written = True
                        lines.append(f"{key}={self._env_cache[key]}")

                if api_written:
                    lines.append("")

            # Other settings
            other_keys = set(self._env_cache.keys()) - set(llm_settings) - set(summary_settings) - set(env_settings) - SECURE_KEYS
            if other_keys:
                lines.append("# Other Settings")
                for key in sorted(other_keys):
                    lines.append(f"{key}={self._env_cache[key]}")
                lines.append("")

            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            os.chmod(self.env_path, 0o600)

        except OSError as e:
            log.error(f"Failed to save .env: {e}")
            raise ConfigurationError(f"Could not save configuration: {e}")

    def migrate_to_keyring(self) -> Dict[str, bool]:
        """
        Migrate API keys from .env to keyring.

        Returns:
            Dict mapping key names to migration success status
        """
        if not KEYRING_AVAILABLE:
            log.warning("Cannot migrate: keyring not available")
            return {key: False for key in SECURE_KEYS}

        results = {}
        for key in SECURE_KEYS:
            if key in self._env_cache:
                value = self._env_cache[key]
                try:
                    keyring.set_password(KEYRING_SERVICE, key, value)
                    del self._env_cache[key]
                    results[key] = True
                    log.info(f"Migrated {key} to keyring")
                except Exception as e:
                    log.error(f"Failed to migrate {key}: {e}")
                    results[key] = False
            else:
                results[key] = True  # Not present, nothing to migrate

        # Save .env without the migrated keys
        self._save_env()

        return results

    def get_all_settings(self) -> Dict[str, str]:
        """
        Get all settings (API keys masked).

        Returns:
            Dict of all settings with API keys masked
        """
        result = dict(self._env_cache)

        # Add keyring-stored API keys (masked)
        for key in SECURE_KEYS:
            value = self.get_api_key(key)
            if value:
                result[key] = self._mask_value(value)

        return result

    @staticmethod
    def _mask_value(value: str) -> str:
        """Mask a sensitive value for display.

        Shows only provider prefix, never reveals suffix characters.
        """
        from .config import mask_api_key
        return mask_api_key(value)

    def has_api_key(self, key_name: str) -> bool:
        """Check if an API key is configured."""
        return bool(self.get_api_key(key_name))

    def get_configured_providers(self) -> list:
        """Get list of providers with configured API keys."""
        providers = []
        if self.has_api_key("OPENAI_API_KEY"):
            providers.append("openai")
        if self.has_api_key("ANTHROPIC_API_KEY"):
            providers.append("anthropic")
        return providers


# Global instance for convenience
_secure_config: Optional[SecureConfigManager] = None


def get_secure_config() -> SecureConfigManager:
    """Get the global secure config manager instance."""
    global _secure_config
    if _secure_config is None:
        _secure_config = SecureConfigManager()
    return _secure_config
