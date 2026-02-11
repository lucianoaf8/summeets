"""Common utilities shared across LLM providers.

Consolidates retry logic, validation patterns, and other shared code
to eliminate duplication between provider implementations.
"""
import re
import logging
import threading
from typing import Callable, TypeVar, Optional, Tuple

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from ..utils.config import SETTINGS

log = logging.getLogger(__name__)
T = TypeVar('T')


def create_retry_decorator(
    exception_types: Tuple,
    max_attempts: int = 3,
    min_wait: int = 2,
    max_wait: int = 30
):
    """Create a retry decorator with standard configuration.

    Args:
        exception_types: Tuple of exception types to retry on
        max_attempts: Maximum retry attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds

    Returns:
        Configured retry decorator
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exception_types),
        before_sleep=before_sleep_log(log, logging.WARNING),
        reraise=True
    )


def validate_api_key_format(
    api_key: str,
    prefix: str,
    min_length: int = 20
) -> bool:
    """Validate API key format.

    Args:
        api_key: The API key to validate
        prefix: Required prefix (e.g., 'sk-', 'sk-ant-')
        min_length: Minimum acceptable length

    Returns:
        True if key format is valid
    """
    if not api_key:
        return False
    if not api_key.startswith(prefix):
        return False
    if len(api_key) < min_length:
        return False
    # Validate character set (alphanumeric, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9_-]+$', api_key):
        return False
    return True


class ClientCache:
    """Generic client caching with lifecycle management.

    Provides thread-safe client caching with API key change detection.
    """

    def __init__(self, client_factory: Callable, key_getter: Callable[[], str]):
        """Initialize client cache.

        Args:
            client_factory: Function that creates client given API key
            key_getter: Function that returns current API key
        """
        self._client = None
        self._last_key: Optional[str] = None
        self._factory = client_factory
        self._key_getter = key_getter
        self._lock = threading.Lock()

    def get(self):
        """Get cached client, creating new one if needed.

        Thread-safe: uses a lock to prevent concurrent client creation.
        """
        current_key = self._key_getter()

        with self._lock:
            if self._client is None or self._last_key != current_key:
                self._client = self._factory(current_key)
                self._last_key = current_key
                log.debug("Client initialized/refreshed")
            return self._client

    def reset(self) -> None:
        """Reset client cache."""
        with self._lock:
            self._client = None
            self._last_key = None


def chain_of_density_base(
    text: str,
    summarize_fn: Callable[[str, str, int], str],
    passes: int = 2
) -> str:
    """Base Chain-of-Density implementation.

    Args:
        text: Text to summarize
        summarize_fn: Function with signature (text, system_prompt, max_tokens) -> str
        passes: Number of densification passes

    Returns:
        Densified summary
    """
    from ..summarize.legacy_prompts import COD_PROMPT, SYSTEM_CORE

    current = text
    for pass_num in range(passes):
        log.info(f"Chain-of-Density pass {pass_num + 1}/{passes}")
        prompt = COD_PROMPT.format(current=current)
        current = summarize_fn(prompt, SYSTEM_CORE, SETTINGS.summary_max_tokens)

    return current
