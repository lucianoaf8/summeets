from openai import OpenAI
import json
import logging
from typing import Optional
from ..utils.config import SETTINGS
from ..utils.exceptions import SummeetsError

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
        raise SummeetsError("Invalid or missing OpenAI API key")
    
    # Create new client if needed (first time or key changed)
    if _client is None or _last_api_key != current_api_key:
        try:
            _client = OpenAI(api_key=current_api_key)
            _last_api_key = current_api_key
            log.debug("OpenAI client initialized")
        except Exception as e:
            raise SummeetsError(f"Failed to initialize OpenAI client: {e}")
    
    return _client

def reset_client() -> None:
    """Reset the client cache (useful for testing or key rotation)."""
    global _client, _last_api_key
    _client = None
    _last_api_key = None

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

def summarize_text(text: str, system_prompt: str = None, max_tokens: int = None) -> str:
    """General text summarization with OpenAI."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": text})
    
    resp = client().chat.completions.create(
        model=SETTINGS.model,
        messages=messages,
        max_tokens=max_tokens or SETTINGS.summary_max_tokens,
        temperature=0.3,
    )
    return resp.choices[0].message.content

def chain_of_density_summarize(text: str, passes: int = 2) -> str:
    """Chain-of-Density iterative summarization."""
    current = text
    for pass_num in range(passes):
        log.info(f"Chain-of-Density pass {pass_num + 1}/{passes}")
        prompt = f"""Summarize this text more concisely while preserving key information.
Pass {pass_num + 1} of {passes} - make it {20 * (pass_num + 1)}% denser:

{current}"""
        current = summarize_text(prompt, max_tokens=len(current.split()) // 2)
    return current