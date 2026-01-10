Below is a **drop-in, production** token counting utility for **OpenAI (tiktoken)** and  **Anthropic (Messages Count Tokens API)** , plus minimal hooks to wire it into your pipeline without breaking anything.

---

# 1) New module: `C:\Projects\summeets\core\tokenizer.py`

```python
# core/tokenizer.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal, Any, Tuple

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

    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic(api_key=key)

    # The API expects the same structure you will send at inference time.
    resp = client.messages.count_tokens(
        model=model,
        messages=messages,
        system=system,
        tools=tools,
        documents=documents,
    )
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
```

---

# 2) Minimal integration in `pipeline.py` (preflight per chunk)

Add this helper near the top of `pipeline.py`:

```python
# pipeline.py
from ..tokenizer import TokenBudget, plan_fit, count_openai_text_tokens
```

Before you call a provider for each chunk, **pre-build the exact messages** you’ll send and check them:

Inside `legacy_map_reduce_summarize(...)` map phase, replace the provider call block with:

```python
        # Preflight token count against context window
        # Build the same structure you send to the API
        messages = [{"role": "user", "content": prompt}]
        system_prompt = SYSTEM_CORE

        # Token budget comes from SETTINGS; keep a margin to avoid edge cases
        budget = TokenBudget(
            context_window=SETTINGS.model_context_window,   # e.g., 128000
            max_output_tokens=800,                          # matches your max_tokens below
            safety_margin=SETTINGS.token_safety_margin      # e.g., 512
        )

        input_tokens, fits = plan_fit(
            provider=provider,
            model=SETTINGS.model,
            messages=messages,
            budget=budget,
            system=system_prompt,
            encoding=SETTINGS.openai_encoding  # e.g., "o200k_base" for OpenAI; ignored for Anthropic
        )

        log.info(f"[token-check] chunk {i+1}: input={input_tokens} fits={fits} "
                 f"(ctx={budget.context_window}, out={budget.max_output_tokens}, margin={budget.safety_margin})")

        if not fits:
            # Your current chunk_seconds was too big; fail fast and advise caller to re-run with smaller chunks.
            # You can also auto-rechunk here if you prefer.
            raise ValueError(
                f"Chunk {i+1} would exceed context window. "
                f"Increase chunk granularity (lower chunk_seconds) or reduce prompt size."
            )

        # Proceed with actual call only after preflight passes
        if provider == "openai":
            summary = openai_client.summarize_text(
                prompt,
                system_prompt=system_prompt,
                max_tokens=800
            )
        else:
            summary = anthropic_client.summarize_text(
                prompt,
                system_prompt=system_prompt,
                max_tokens=800
            )
```

Repeat the same pattern once more for the **reduce phase** just before the final call:

```python
    final_messages = [{"role": "user", "content": final_prompt}]
    budget = TokenBudget(
        context_window=SETTINGS.model_context_window,
        max_output_tokens=SETTINGS.summary_max_tokens,
        safety_margin=SETTINGS.token_safety_margin
    )
    input_tokens, fits = plan_fit(
        provider=provider,
        model=SETTINGS.model,
        messages=final_messages,
        budget=budget,
        system=SYSTEM_CORE,
        encoding=SETTINGS.openai_encoding
    )
    log.info(f"[token-check] reduce: input={input_tokens} fits={fits}")
    if not fits:
        raise ValueError("Reduce phase would exceed context window; lower chunk_seconds or reduce partial size.")
```

Do the same in `template_aware_summarize(...)` for its per-chunk calls and final combine call.

Finally, preflight your **JSON extraction** prompt the same way before calling `openai_client.structured_json_summarize(...)` or `anthropic_client.summarize_text(...)`.

---

# 3) Add a tiny settings surface (no breaking changes)

In your `SETTINGS` (wherever defined), add:

```python
# e.g., core/utils/config.py (not shown in your snippets)
model_context_window: int = 128000     # set per model
token_safety_margin: int = 512         # small headroom
openai_encoding: str = "o200k_base"    # encode for 4o/mini; change if you target older models
```

You can override these per run.

---

# 4) Optional: a CLI to dry-run counts on a transcript before summarizing

`C:\Projects\summeets\tools\tokens_check.py`

```python
# tools/tokens_check.py
import argparse
import json
from pathlib import Path
from summeets.core.tokenizer import TokenBudget, plan_fit
from summeets.core.summarize.legacy_prompts import SYSTEM_CORE, CHUNK_PROMPT, REDUCE_PROMPT
from summeets.core.summarize.legacy_prompts import format_chunk_text, format_partial_summaries

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True, type=Path)
    ap.add_argument("--provider", choices=["openai","anthropic"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--encoding", default="o200k_base")
    ap.add_argument("--ctx", type=int, required=True, help="context window tokens")
    ap.add_argument("--out", type=int, default=800, help="planned max_output_tokens")
    ap.add_argument("--margin", type=int, default=512)
    ap.add_argument("--chunk-seconds", type=int, default=1800)
    args = ap.parse_args()

    segments = json.loads(Path(args.transcript).read_text(encoding="utf-8"))

    # naive time-based chunking like pipeline
    chunks = []
    cur = []
    start = None
    for s in segments:
        if start is None:
            start = s.get("start", 0)
        cur.append(s)
        if s.get("end", 0) - start >= args.chunk_seconds:
            chunks.append(cur); cur=[]; start=None
    if cur:
        chunks.append(cur)

    budget = TokenBudget(args.ctx, args.out, args.margin)

    # map phase checks
    for i, chunk in enumerate(chunks, 1):
        chunk_text = format_chunk_text(chunk)
        prompt = CHUNK_PROMPT.format(chunk=chunk_text)
        messages = [{"role": "user", "content": prompt}]
        n, fits = plan_fit(args.provider, args.model, messages, budget, system=SYSTEM_CORE, encoding=args.encoding)
        print(f"map[{i}] tokens={n}, fits={fits}")

    # reduce phase check (using synthesized partials)
    partials = []
    for chunk in chunks:
        partials.append("PLACEHOLDER_PARTIAL_SUMMARY")  # we just need structure for sizing
    parts_text = format_partial_summaries(partials)
    final_prompt = REDUCE_PROMPT.format(parts=parts_text)
    messages = [{"role": "user", "content": final_prompt}]
    n, fits = plan_fit(args.provider, args.model, messages, budget, system=SYSTEM_CORE, encoding=args.encoding)
    print(f"reduce tokens={n}, fits={fits}")

if __name__ == "__main__":
    main()
```

---

# 5) Accuracy notes

* **OpenAI:** there is **no** official pre-count endpoint. The reliable path is `tiktoken` using the **same encoding** the target model uses and encoding the **exact message structure** you’ll send. For 4o/mini family use `o200k_base`; for older GPT-3.5/4 use `cl100k_base`. References: tiktoken repo and OpenAI cookbook/tokenizer. ([GitHub](https://github.com/openai/tiktoken?utm_source=chatgpt.com "tiktoken is a fast BPE tokeniser for use with OpenAI's models."), [OpenAI Cookbook](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken?utm_source=chatgpt.com "How to count tokens with Tiktoken"), [OpenAI Platform](https://platform.openai.com/tokenizer?utm_source=chatgpt.com "Tokenizer - OpenAI API"))
* **Anthropic:** use `messages.count_tokens` on the exact payload; this is authoritative and includes tools, images, PDFs. References: Anthropic API docs and token-counting guide, SDK. ([Anthropic](https://docs.anthropic.com/en/api/messages-count-tokens?utm_source=chatgpt.com "Count Message tokens"), [GitHub](https://github.com/anthropics/anthropic-sdk-python?utm_source=chatgpt.com "anthropics/anthropic-sdk-python"))

---

# 6) Risks, gaps, edge cases

* If you add **non-text parts** (images, tools) to OpenAI payloads, your local approximation should insert **placeholders** of similar size or you’ll undercount. There’s no official OpenAI pre-count for those.
* Set `SETTINGS.model_context_window` correctly per model. Don’t hardcode universal values.
* After each real API call, you should still **log the provider-reported usage** and compare to preflight for drift tracking.

---

# 7) Install

```powershell
# from an activated venv
pip install tiktoken anthropic
```

---

# 8) Docs (official)

* **OpenAI tokenizer & tiktoken** : tokenizer tool and cookbook example; tiktoken library. ([OpenAI Platform](https://platform.openai.com/tokenizer?utm_source=chatgpt.com "Tokenizer - OpenAI API"), [OpenAI Cookbook](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken?utm_source=chatgpt.com "How to count tokens with Tiktoken"), [GitHub](https://github.com/openai/tiktoken?utm_source=chatgpt.com "tiktoken is a fast BPE tokeniser for use with OpenAI's models."))
* **Anthropic token counting** : Messages Count Tokens API and user guide; Python SDK. ([Anthropic](https://docs.anthropic.com/en/api/messages-count-tokens?utm_source=chatgpt.com "Count Message tokens"), [GitHub](https://github.com/anthropics/anthropic-sdk-python?utm_source=chatgpt.com "anthropics/anthropic-sdk-python"))

This keeps your pipeline honest: preflight every prompt, fail fast when a chunk would blow the window, or auto-rechunk if you prefer.
