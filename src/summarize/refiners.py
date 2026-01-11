"""Post-processing refiners for summarization output.

Provides refinement operations for improving summary quality:
- Chain-of-Density: Iterative summary densification
- Requirements validation: Detect and fix generic template output
- JSON extraction: Structure unstructured summary text

Functions:
    chain_of_density_pass: Apply CoD refinement
    validate_requirements_output: Validate requirements summaries
    extract_structured_json: Extract structured data from summary
"""
import logging
from typing import Optional

from ..utils.config import SETTINGS
from ..providers import openai_client, anthropic_client

log = logging.getLogger(__name__)


def chain_of_density_pass(
    text: str,
    provider: str = None,
    passes: int = 2
) -> str:
    """Apply Chain-of-Density summarization refinement.

    Iteratively densifies summary while preserving key information.

    Args:
        text: Summary text to refine
        provider: LLM provider (defaults to config)
        passes: Number of densification passes

    Returns:
        Refined summary text
    """
    provider = provider or SETTINGS.provider

    if passes <= 0:
        return text

    log.info(f"Applying {passes} Chain-of-Density passes")

    if provider == "openai":
        return openai_client.chain_of_density_summarize(text, passes)
    elif provider == "anthropic":
        return anthropic_client.chain_of_density_summarize(text, passes)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def validate_requirements_output(
    summary: str,
    transcript_text: str,
    provider: str = None
) -> str:
    """Validate requirements output isn't generic.

    Checks for template/boilerplate patterns and re-extracts if needed.

    Args:
        summary: Generated requirements summary
        transcript_text: Original transcript for re-extraction
        provider: LLM provider

    Returns:
        Validated (possibly regenerated) summary
    """
    provider = provider or SETTINGS.provider

    generic_patterns = [
        "REQ-F-001", "REQ-NF-001",
        "As a manager, I want",
        "Acceptance Criteria:",
        "Priority: Must",
        "Stakeholder: Regional Service Team Lead",
    ]

    if any(pattern in summary for pattern in generic_patterns):
        log.warning("Detected generic requirements template - re-extracting")

        strict_prompt = (
            f"This transcript contains a real conversation:\n\n{transcript_text}\n\n"
            "Extract ONLY the actual requirements discussed. No generic templates, "
            "no user story format, no requirement IDs. Just what was really talked about. "
            "Start with: 'Based on this conversation, the actual requirements discussed were:'"
        )

        if provider == "anthropic":
            return anthropic_client.summarize_text(
                strict_prompt,
                system_prompt="Extract only real conversation content. No templates.",
                max_tokens=3000
            )
        elif provider == "openai":
            return openai_client.summarize_text(
                strict_prompt,
                system_prompt="Extract only real conversation content. No templates.",
                max_tokens=3000
            )

    return summary


def extract_structured_json(
    summary: str,
    provider: str,
    model: str
) -> str:
    """Extract structured JSON from summary.

    Args:
        summary: Summary text to structure
        provider: LLM provider
        model: Model identifier

    Returns:
        JSON string with structured data
    """
    json_instructions = (
        "Extract JSON for the following keys ONLY:\n"
        "executive_summary, decisions, action_items, risks, open_questions, "
        "timeline, stakeholders, next_steps, glossary.\n"
        "Base your JSON strictly on this final summary. Do not invent fields or content.\n\n"
        f"Final summary:\n{summary}"
    )

    log.info("Extracting structured JSON data")

    if provider == "openai":
        return openai_client.structured_json_summarize(json_instructions)
    else:
        return anthropic_client.summarize_text(
            "Return only minified JSON for this content. No commentary. "
            "Include keys: executive_summary, decisions, action_items, risks, "
            "open_questions, timeline, stakeholders, next_steps, glossary.\n\n"
            + json_instructions,
            system_prompt="Return only minified JSON. No extra text.",
            max_tokens=SETTINGS.summary_max_tokens
        )
