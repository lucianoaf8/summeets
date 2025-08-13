from anthropic import Anthropic
import logging
from ..config import SETTINGS

log = logging.getLogger(__name__)

_client = None

def client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=SETTINGS.anthropic_api_key)
    return _client

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