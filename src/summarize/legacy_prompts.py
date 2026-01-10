"""
Proven prompts from legacy summarize_meeting.py implementation.
These prompts have been tested and produce high-quality, comprehensive summaries.

Updated to support template-specific differentiation.
"""

from typing import Optional

try:
    from .system_prompts import get_system_prompt, get_chunk_context, get_reduce_context
except ImportError:
    # Fallback if system_prompts not available
    def get_system_prompt(template_type: str = "DEFAULT") -> str:
        return SYSTEM_CORE
    def get_chunk_context(template_type: str = "DEFAULT") -> str:
        return ""
    def get_reduce_context(template_type: str = "DEFAULT") -> str:
        return ""


# Core system prompt - sets the tone and audience (backward compatibility)
SYSTEM_CORE = (
    "You are a surgical meeting summarizer. Write with extreme recall and structure. "
    "Never invent facts. Include timestamps when possible.\n"
    "Audience: busy executives and the delivery team.\n"
)

# Map phase - detailed chunk summarization with required sections
CHUNK_PROMPT = (
    "Summarize this transcript chunk into the following sections. Be exhaustive but concise. "
    "Preserve numbers, owners, and dates. Include timestamp ranges in [mm:ss] where possible.\n\n"
    "Required sections:\n"
    "1) Key Points\n"
    "2) Decisions\n"
    "3) Action Items [owner | item | due | status]\n"
    "4) Risks/Blockers\n"
    "5) Open Questions\n"
    "6) Notable Quotes [timestamp | speaker | quote]\n\n"
    "Transcript chunk:\n{chunk}\n"
)

# Reduce phase - combine partial summaries into final structured report
REDUCE_PROMPT = (
    "You are given ordered partial summaries from consecutive chunks of the same meeting. "
    "Merge them into a single, deduplicated, contradiction-resolved report with the sections:\n"
    "## Executive Summary (≤10 bullets)\n"
    "## Decisions\n"
    "## Action Items (owner | item | due | status)\n"
    "## Risks/Blockers\n"
    "## Open Questions\n"
    "## Timeline of Key Moments [timestamp | what happened]\n"
    "## Stakeholders & Responsibilities\n"
    "## Next Steps\n"
    "## Glossary (if any abbreviations)\n\n"
    "Partial summaries:\n{parts}\n"
)

# Chain-of-Density refinement - proper CoD methodology
COD_PROMPT = (
    "Enhance this summary by increasing entity density. Add missing salient entities "
    "(people, numbers, dates, decisions, action items) from the original content without "
    "adding length. Preserve all existing sections and structure.\n\n"
    "Rules:\n"
    "- Output ONLY the enhanced summary\n"
    "- Do NOT explain your changes\n"
    "- Do NOT add commentary about the refinement process\n"
    "- Only use information already present in the summary\n"
    "- Maintain identical section headers and organization\n\n"
    "Summary to enhance:\n{current}\n\n"
    "Enhanced summary:"
)

# Structured JSON schema for OpenAI structured outputs
STRUCTURED_JSON_SPEC = {
    "name": "MeetingSummary",
    "schema": {
        "type": "object",
        "properties": {
            "executive_summary": {"type": "array", "items": {"type": "string"}},
            "decisions": {"type": "array", "items": {"type": "string"}},
            "action_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "item": {"type": "string"},
                        "due": {"type": "string"},
                        "status": {"type": "string"},
                        "timestamp": {"type": "string"},
                    },
                    "required": ["owner", "item", "due", "status", "timestamp"],
                    "additionalProperties": False,
                },
            },
            "risks": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
            "timeline": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "string"},
                        "event": {"type": "string"},
                    },
                    "required": ["event"],
                    "additionalProperties": False,
                },
            },
            "stakeholders": {"type": "array", "items": {"type": "string"}},
            "next_steps": {"type": "array", "items": {"type": "string"}},
            "glossary": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["executive_summary", "decisions", "action_items", "risks", "open_questions"],
        "additionalProperties": False,
    },
    "strict": True,
}

def format_chunk_text(chunk_segments: list) -> str:
    """Format chunk segments with timestamps like legacy implementation."""
    return "\n".join(
        f"[{seg.get('start', 0):.2f}s] {seg.get('speaker', 'Speaker')}: {seg.get('text', '')}"
        for seg in chunk_segments
    )

def format_partial_summaries(partials: list) -> str:
    """Format partial summaries for reduce phase."""
    return "\n\n".join(f"### Part {i}\n{p}" for i, p in enumerate(partials, 1))