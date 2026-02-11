"""Anthropic provider implementation."""
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError
import logging
from typing import Optional

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from ..utils.config import SETTINGS
from ..utils.exceptions import SummeetsError, AnthropicError
from .base import LLMProvider, ProviderRegistry
from .common import ClientCache, validate_api_key_format, chain_of_density_base

log = logging.getLogger(__name__)

_cache = ClientCache(
    client_factory=lambda key: Anthropic(api_key=key),
    key_getter=lambda: SETTINGS.anthropic_api_key,
)


def _validate_api_key(api_key: str) -> bool:
    """Validate Anthropic API key format (sk-ant- prefix, min 30 chars)."""
    if not api_key:
        return False
    return validate_api_key_format(api_key, 'sk-ant-', 30)


def client() -> Anthropic:
    """Get Anthropic client with proper lifecycle management and validation."""
    current_api_key = SETTINGS.anthropic_api_key

    if not _validate_api_key(current_api_key):
        raise AnthropicError("Invalid or missing Anthropic API key")

    try:
        return _cache.get()
    except Exception as e:
        raise AnthropicError(f"Failed to initialize Anthropic client: {e}", cause=e)


def reset_client() -> None:
    """Reset the client cache (useful for testing or key rotation)."""
    _cache.reset()


# Retry decorator for API calls
_retry_decorator = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((APIConnectionError, RateLimitError)),
    before_sleep=before_sleep_log(log, logging.WARNING),
    reraise=True
)


@_retry_decorator
def summarize_chunks(chunks: list[str], sys_prompt: str, max_out_tokens: int) -> list[str]:
    """Messages API; use dated model IDs like claude-3-5-sonnet-20241022."""
    out = []
    for ch in chunks:
        try:
            msg = client().messages.create(
                model=SETTINGS.model,
                max_tokens=max_out_tokens,
                system=sys_prompt,
                messages=[{"role": "user", "content": ch}],
            )
            if not msg.content:
                raise AnthropicError("Anthropic returned empty content array")
            out.append(msg.content[0].text)
        except APIError as e:
            raise AnthropicError(f"Anthropic API error: {e}", cause=e)
    return out


@_retry_decorator
def summarize_text(
    text: str,
    system_prompt: str = None,
    max_tokens: int = None,
    enable_thinking: bool = False,
    thinking_budget: int = None
) -> str:
    """General text summarization with Anthropic."""
    system = system_prompt or "You are a helpful assistant that summarizes meetings."

    # Prepare message parameters
    # Note: temperature must be 1 when extended thinking is enabled
    message_params = {
        "model": SETTINGS.model,
        "max_tokens": max_tokens or SETTINGS.summary_max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": text}],
        "temperature": 1 if enable_thinking else 0.3,
    }

    # Add thinking parameters if enabled
    if enable_thinking:
        budget = thinking_budget or SETTINGS.thinking_budget_default
        message_params["thinking"] = {
            "type": "enabled",
            "budget_tokens": budget
        }

    try:
        msg = client().messages.create(**message_params)
        if not msg.content:
            raise AnthropicError("Anthropic returned empty content array")
        # With extended thinking, text blocks may not be first; find the text block
        for block in msg.content:
            if hasattr(block, 'text'):
                return block.text
        raise AnthropicError("Anthropic response contained no text content")
    except APIError as e:
        raise AnthropicError(f"Anthropic API error: {e}", cause=e)


def chain_of_density_summarize(text: str, passes: int = 2) -> str:
    """Chain-of-Density iterative summarization using proven legacy methodology."""
    return chain_of_density_base(text, summarize_text, passes)


# Provider class implementation for the unified interface
class AnthropicProvider(LLMProvider):
    """Anthropic provider implementation of LLMProvider interface."""

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return SETTINGS.model

    def summarize_text(
        self,
        text: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        # Extract Anthropic-specific options
        enable_thinking = kwargs.get('enable_thinking', False)
        thinking_budget = kwargs.get('thinking_budget', SETTINGS.thinking_budget_default)
        return summarize_text(
            text,
            system_prompt,
            max_tokens,
            enable_thinking=enable_thinking,
            thinking_budget=thinking_budget
        )

    def chain_of_density_summarize(self, text: str, passes: int = 2) -> str:
        return chain_of_density_summarize(text, passes)

    def validate_api_key(self) -> bool:
        return _validate_api_key(SETTINGS.anthropic_api_key)


# Register the provider
ProviderRegistry.register("anthropic", AnthropicProvider)
