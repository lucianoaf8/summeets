# core/tokenizer.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal, Any, Tuple
from .utils.config import SETTINGS

# OpenAI side (local, offline, deterministic)
try:
    import tiktoken
except Exception:
    tiktoken = None  # fail soft if not needed

# Anthropic side (authoritative server-side count for real payloads)
try:
    import anthropic
except Exception:
    anthropic = None


Provider = Literal["openai", "anthropic"]

# Sensible defaults; override via function args or your SETTINGS
_OPENAI_DEFAULT_ENCODING = "o200k_base"  # 4o/mini family; pass a different encoding if needed


@dataclass(frozen=True)
class TokenBudget:
    context_window: int
    max_output_tokens: int
    safety_margin: int = 0  # optional headroom to avoid edge overruns

    def fits(self, input_tokens: int) -> bool:
        return input_tokens + self.max_output_tokens + self.safety_margin <= self.context_window


def get_openai_encoding(encoding: Optional[str] = None):
    """
    Return a tiktoken encoding. You can pass 'o200k_base', 'cl100k_base', etc.
    """
    if tiktoken is None:
        raise RuntimeError("tiktoken not installed. `pip install tiktoken`")

    enc_name = encoding or _OPENAI_DEFAULT_ENCODING
    return tiktoken.get_encoding(enc_name)


def count_openai_text_tokens(
    text: str,
    encoding: Optional[str] = None
) -> int:
    """
    Deterministic local count using tiktoken for OpenAI models.
    Accurate for text content; for Chat, use `count_openai_chat_like`.
    """
    enc = get_openai_encoding(encoding)
    return len(enc.encode(text))


def count_openai_chat_like(
    messages: List[Dict[str, Any]],
    encoding: Optional[str] = None,
    join_roles: bool = True
) -> int:
    """
    Practical preflight for Chat payloads on OpenAI:
    - There is no official pre-count API. We approximate by encoding exactly
      what you'll send: role + content text segments.
    - This is robust enough in practice to keep you within window.
    - If you add tools/images/etc, you must reflect them in the same way here.

    messages: [{"role": "system"|"user"|"assistant", "content": str|List[...]}]
    """
    enc = get_openai_encoding(encoding)

    def _norm_content(c: Any) -> str:
        if isinstance(c, str):
            return c
        # If content is a list of parts (text, images, etc.), concatenate text parts.
        # Non-text parts should be represented as placeholders similar to your send path.
        if isinstance(c, list):
            buf = []
            for p in c:
                if isinstance(p, dict) and p.get("type") == "text":
                    buf.append(p.get("text", ""))
                else:
                    # placeholder for non-text parts to avoid zero-count surprises
                    buf.append(f"[{p.get('type','nontext')}]")
            return "\n".join(buf)
        return str(c)

    parts = []
    for m in messages:
        role = m.get("role", "")
        content = _norm_content(m.get("content", ""))
        parts.append(f"{role}:\n{content}" if join_roles else content)

    payload_text = "\n\n".join(parts)
    return len(enc.encode(payload_text))


def count_anthropic_message_tokens(
    model: str,
    messages: List[Dict[str, Any]],
    system: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    documents: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
) -> int:
    """
    Exact, authoritative token count for Claude messages. Mirrors server behavior.
    Requires `anthropic` package and a valid API key in env or argument.
    """
    if anthropic is None:
        raise RuntimeError("anthropic SDK not installed. `pip install anthropic`")

    key = api_key or SETTINGS.anthropic_api_key
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic(api_key=key)

    # The API expects the same structure you will send at inference time.
    # Note: documents parameter is not supported in count_tokens
    kwargs = {
        "model": model,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools
    
    resp = client.messages.count_tokens(**kwargs)
    # The Python SDK returns fields such as `input_tokens`
    # For completeness, return the sum if present, else try total-like fields.
    if hasattr(resp, "input_tokens"):
        return int(resp.input_tokens)
    # fallback (SDKs may evolve)
    return int(getattr(resp, "total_tokens", 0) or getattr(resp, "tokens", 0))


def plan_fit(
    provider: Provider,
    model: str,
    messages: List[Dict[str, Any]],
    budget: TokenBudget,
    *,
    system: Optional[str] = None,
    encoding: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    documents: Optional[List[Dict[str, Any]]] = None,
    anthropic_api_key: Optional[str] = None,
) -> Tuple[int, bool]:
    """
    Return (input_tokens, fits) for a given provider/model/messages under a TokenBudget.
    """
    if provider == "anthropic":
        input_tokens = count_anthropic_message_tokens(
            model=model,
            messages=messages,
            system=system,
            tools=tools,
            documents=documents,
            api_key=anthropic_api_key,
        )
    elif provider == "openai":
        # NOTE: OpenAI has no official pre-count endpoint; we approximate locally.
        # Build the same message structure you actually send.
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)
        input_tokens = count_openai_chat_like(msgs, encoding=encoding)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    return input_tokens, budget.fits(input_tokens)
