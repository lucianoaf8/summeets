from anthropic import Anthropic
import logging
from typing import Optional
from ..utils.config import SETTINGS
from ..utils.exceptions import SummeetsError

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
        raise SummeetsError("Invalid or missing Anthropic API key")
    
    # Create new client if needed (first time or key changed)
    if _client is None or _last_api_key != current_api_key:
        try:
            _client = Anthropic(api_key=current_api_key)
            _last_api_key = current_api_key
            log.debug("Anthropic client initialized")
        except Exception as e:
            raise SummeetsError(f"Failed to initialize Anthropic client: {e}")
    
    return _client

def reset_client() -> None:
    """Reset the client cache (useful for testing or key rotation)."""
    global _client, _last_api_key
    _client = None
    _last_api_key = None

def summarize_chunks(chunks: list[str], sys_prompt: str, max_out_tokens: int) -> list[str]:
    """Messages API; use dated model IDs like claude-3-5-sonnet-20241022."""
    out = []
    for ch in chunks:
        msg = client().messages.create(
            model=SETTINGS.model,
            max_tokens=max_out_tokens,
            system=sys_prompt,
            messages=[{"role": "user", "content": ch}],
        )
        out.append(msg.content[0].text)
    return out

def summarize_text(text: str, system_prompt: str = None, max_tokens: int = None) -> str:
    """General text summarization with Anthropic."""
    system = system_prompt or "You are a helpful assistant that summarizes meetings."
    
    msg = client().messages.create(
        model=SETTINGS.model,
        max_tokens=max_tokens or SETTINGS.summary_max_tokens,
        system=system,
        messages=[{"role": "user", "content": text}],
        temperature=0.3,
    )
    return msg.content[0].text

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