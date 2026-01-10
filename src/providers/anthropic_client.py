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

log = logging.getLogger(__name__)

_client: Optional[Anthropic] = None
_last_api_key: Optional[str] = None


def _validate_api_key(api_key: str) -> bool:
    """Validate Anthropic API key format."""
    if not api_key:
        return False
    if not api_key.startswith('sk-ant-'):
        return False
    if len(api_key) < 30:  # Minimum reasonable length
        return False
    return True


def client() -> Anthropic:
    """Get Anthropic client with proper lifecycle management and validation."""
    global _client, _last_api_key

    current_api_key = SETTINGS.anthropic_api_key

    # Validate API key
    if not _validate_api_key(current_api_key):
        raise AnthropicError("Invalid or missing Anthropic API key")

    # Create new client if needed (first time or key changed)
    if _client is None or _last_api_key != current_api_key:
        try:
            _client = Anthropic(api_key=current_api_key)
            _last_api_key = current_api_key
            log.debug("Anthropic client initialized")
        except Exception as e:
            raise AnthropicError(f"Failed to initialize Anthropic client: {e}", cause=e)

    return _client


def reset_client() -> None:
    """Reset the client cache (useful for testing or key rotation)."""
    global _client, _last_api_key
    _client = None
    _last_api_key = None


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
    thinking_budget: int = 4000
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
        message_params["thinking"] = {
            "type": "enabled",
            "budget_tokens": thinking_budget
        }

    try:
        msg = client().messages.create(**message_params)
        return msg.content[0].text
    except APIError as e:
        raise AnthropicError(f"Anthropic API error: {e}", cause=e)


def chain_of_density_summarize(text: str, passes: int = 2) -> str:
    """Chain-of-Density iterative summarization using proven legacy methodology."""
    from ..summarize.legacy_prompts import COD_PROMPT, SYSTEM_CORE

    current = text
    for pass_num in range(passes):
        log.info(f"Chain-of-Density pass {pass_num + 1}/{passes}")
        prompt = COD_PROMPT.format(current=current)
        current = summarize_text(
            prompt,
            system_prompt=SYSTEM_CORE,
            max_tokens=SETTINGS.summary_max_tokens
        )
    return current


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
        thinking_budget = kwargs.get('thinking_budget', 4000)
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
