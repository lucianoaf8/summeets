"""OpenAI provider implementation."""
from openai import OpenAI, APIError, APIConnectionError, RateLimitError
import json
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
from ..utils.exceptions import SummeetsError, OpenAIError
from .base import LLMProvider, ProviderRegistry

log = logging.getLogger(__name__)

_client: Optional[OpenAI] = None
_last_api_key: Optional[str] = None


def _validate_api_key(api_key: str) -> bool:
    """Validate OpenAI API key format."""
    if not api_key:
        return False
    if not api_key.startswith('sk-'):
        return False
    if len(api_key) < 20:  # Minimum reasonable length
        return False
    return True


def client() -> OpenAI:
    """Get OpenAI client with proper lifecycle management and validation."""
    global _client, _last_api_key

    current_api_key = SETTINGS.openai_api_key

    # Validate API key
    if not _validate_api_key(current_api_key):
        raise OpenAIError("Invalid or missing OpenAI API key")

    # Create new client if needed (first time or key changed)
    if _client is None or _last_api_key != current_api_key:
        try:
            _client = OpenAI(api_key=current_api_key)
            _last_api_key = current_api_key
            log.debug("OpenAI client initialized")
        except Exception as e:
            raise OpenAIError(f"Failed to initialize OpenAI client: {e}", cause=e)

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
def summarize_chunks(chunks: list[str], schema: dict, max_out_tokens: int) -> list[str]:
    """Structured Outputs with json_schema response_format."""
    out = []
    for ch in chunks:
        resp = client().chat.completions.create(
            model=SETTINGS.model,
            messages=[{"role": "user", "content": ch}],
            response_format={"type": "json_schema", "json_schema": {"name": "summary", "schema": schema}},
            max_tokens=max_out_tokens,
        )
        out.append(resp.choices[0].message.content)
    return out


@_retry_decorator
def summarize_text(text: str, system_prompt: str = None, max_tokens: int = None) -> str:
    """General text summarization with OpenAI."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": text})

    try:
        resp = client().chat.completions.create(
            model=SETTINGS.model,
            messages=messages,
            max_tokens=max_tokens or SETTINGS.summary_max_tokens,
            temperature=0.3,
        )
        return resp.choices[0].message.content
    except APIError as e:
        raise OpenAIError(f"OpenAI API error: {e}", cause=e)


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


@_retry_decorator
def structured_json_summarize(content: str) -> str:
    """
    Generate structured JSON summary using OpenAI structured outputs.
    Primary: OpenAI structured outputs with response_format=json_schema.
    Fallback A: JSON mode with prompt-enforced structure.
    Fallback B: Regular chat with JSON instructions.
    """
    from ..summarize.legacy_prompts import STRUCTURED_JSON_SPEC

    # Try Structured Outputs first (preferred)
    try:
        resp = client().chat.completions.create(
            model=SETTINGS.model,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_schema", "json_schema": STRUCTURED_JSON_SPEC},
            max_tokens=SETTINGS.summary_max_tokens,
            temperature=0.0,
        )
        return resp.choices[0].message.content
    except TypeError:
        # Older SDK without 'response_format' support
        log.warning("Structured outputs not supported, falling back to JSON mode")
        pass
    except Exception as e:
        # Some models/versions may not accept response_format
        log.warning(f"Structured outputs failed: {e}, falling back to JSON mode")
        pass

    # Fallback A: JSON mode with prompt enforcement
    try:
        prompt = (
            "Return only minified JSON. No prose. Strictly include keys: "
            "executive_summary, decisions, action_items, risks, open_questions, timeline, stakeholders, next_steps, glossary.\n\n"
            + content
        )
        resp = client().chat.completions.create(
            model=SETTINGS.model,
            messages=[
                {"role": "system", "content": "Return only minified JSON. No extra text."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=SETTINGS.summary_max_tokens,
            temperature=0.0,
        )
        return resp.choices[0].message.content
    except Exception as e:
        log.warning(f"JSON mode failed: {e}, falling back to regular chat")

    # Fallback B: Regular chat with JSON instructions
    prompt = (
        "Return only minified JSON for this content. No commentary. "
        "Include keys: executive_summary, decisions, action_items, risks, open_questions, timeline, stakeholders, next_steps, glossary.\n\n"
        + content
    )
    return summarize_text(
        prompt,
        system_prompt="Return only minified JSON. No extra text.",
        max_tokens=SETTINGS.summary_max_tokens
    )


# Provider class implementation for the unified interface
class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation of LLMProvider interface."""

    @property
    def name(self) -> str:
        return "openai"

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
        return summarize_text(text, system_prompt, max_tokens)

    def chain_of_density_summarize(self, text: str, passes: int = 2) -> str:
        return chain_of_density_summarize(text, passes)

    def validate_api_key(self) -> bool:
        return _validate_api_key(SETTINGS.openai_api_key)


# Register the provider
ProviderRegistry.register("openai", OpenAIProvider)
