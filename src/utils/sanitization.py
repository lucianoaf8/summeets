"""Input sanitization for LLM prompts.

Protects against prompt injection attacks by detecting and removing
potentially harmful patterns from user-provided content.
"""
import re
import logging
from typing import Optional

log = logging.getLogger(__name__)

# Patterns that may indicate prompt injection attempts
INJECTION_PATTERNS = [
    # Instruction override attempts
    r'ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|context)',
    r'disregard\s+(all\s+)?(previous|prior|above)',
    r'forget\s+(everything|all|what)',
    r'new\s+instructions?:?\s*',
    r'override\s+(mode|instructions?)',

    # Role confusion attempts
    r'system:\s*',
    r'assistant:\s*',
    r'user:\s*',
    r'human:\s*',
    r'\[INST\]',
    r'\[/INST\]',
    r'<<SYS>>',
    r'<</SYS>>',

    # Jailbreak patterns
    r'do\s+anything\s+now',
    r'DAN\s+mode',
    r'developer\s+mode',
    r'jailbreak',
]

# Special tokens used by various LLMs
SPECIAL_TOKENS = [
    '<|im_start|>',
    '<|im_end|>',
    '<|system|>',
    '<|user|>',
    '<|assistant|>',
    '<|endoftext|>',
    '<s>',
    '</s>',
    '[INST]',
    '[/INST]',
]

# Compiled regex patterns for performance
_compiled_patterns = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def sanitize_prompt_input(text: str, strict: bool = False) -> str:
    """
    Sanitize user input before including in LLM prompts.

    Removes or escapes potentially harmful injection patterns while
    preserving legitimate content.

    Args:
        text: Input text to sanitize
        strict: If True, removes more aggressively (may affect legit content)

    Returns:
        Sanitized text safe for prompt inclusion
    """
    if not text:
        return ""

    result = text
    patterns_found = []

    # Remove detected injection patterns
    for pattern in _compiled_patterns:
        if pattern.search(result):
            patterns_found.append(pattern.pattern)
            result = pattern.sub('', result)

    # Remove special LLM tokens
    for token in SPECIAL_TOKENS:
        if token in result:
            patterns_found.append(f"token:{token}")
            result = result.replace(token, '')

    # Remove angle bracket sequences that look like XML/special tags
    # This catches things like <|any|> patterns
    result = re.sub(r'<\|[^|>]+\|>', '', result)

    # In strict mode, also remove common delimiter abuse
    if strict:
        # Remove excessive whitespace/newlines (potential delimiter injection)
        result = re.sub(r'\n{4,}', '\n\n\n', result)
        result = re.sub(r'={5,}', '====', result)
        result = re.sub(r'-{5,}', '----', result)
        result = re.sub(r'#{5,}', '####', result)

    if patterns_found:
        log.warning(
            f"Removed {len(patterns_found)} potential injection patterns: "
            f"{patterns_found[:3]}{'...' if len(patterns_found) > 3 else ''}"
        )

    return result.strip()


def sanitize_transcript_for_summary(transcript: str) -> str:
    """
    Sanitize transcript content before summarization.

    Specifically designed for meeting transcripts where content should
    be preserved but injection attempts blocked.

    Args:
        transcript: Raw transcript text

    Returns:
        Sanitized transcript safe for LLM processing
    """
    if not transcript:
        return ""

    # Remove any XML/HTML-like tags (not expected in transcripts)
    cleaned = re.sub(r'<[^>]+>', '', transcript)

    # Remove control characters except newlines and tabs
    cleaned = ''.join(
        c for c in cleaned
        if c in '\n\t' or (ord(c) >= 32 and ord(c) != 127)
    )

    # Apply standard sanitization (non-strict to preserve natural speech)
    return sanitize_prompt_input(cleaned, strict=False)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe display in prompts.

    Prevents path traversal and injection via filenames.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for prompt inclusion
    """
    if not filename:
        return ""

    # Remove path separators
    cleaned = filename.replace('/', '_').replace('\\', '_')

    # Remove null bytes and other control chars
    cleaned = ''.join(c for c in cleaned if ord(c) >= 32 and ord(c) != 127)

    # Remove quotes that could break prompt formatting
    cleaned = cleaned.replace('"', '').replace("'", '')

    # Limit length
    if len(cleaned) > 255:
        cleaned = cleaned[:252] + '...'

    return cleaned


def detect_injection_attempt(text: str) -> Optional[str]:
    """
    Detect if text contains potential injection patterns.

    Returns the first detected pattern type or None if clean.
    Useful for logging/alerting without modifying content.

    Args:
        text: Text to analyze

    Returns:
        Pattern description if injection detected, None otherwise
    """
    if not text:
        return None

    for pattern in _compiled_patterns:
        match = pattern.search(text)
        if match:
            return f"pattern:{pattern.pattern[:50]}"

    for token in SPECIAL_TOKENS:
        if token in text:
            return f"token:{token}"

    return None
