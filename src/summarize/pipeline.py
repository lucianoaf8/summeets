"""Summarization pipeline using modular components."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from ..utils.config import SETTINGS
from ..models import SummaryTemplate
from ..tokenizer import TokenBudget, plan_fit

# Modular components
from .loader import load_transcript, segments_to_text
from .chunking import chunk_transcript
from .strategies import MapReduceStrategy, TemplateAwareStrategy, call_llm
from .refiners import chain_of_density_pass, validate_requirements_output, extract_structured_json
from .output import save_summary_outputs, create_requirements_json
from .templates import SummaryTemplates, detect_meeting_type
from .legacy_prompts import (
    get_system_prompt, get_chunk_context, get_reduce_context,
    CHUNK_PROMPT, REDUCE_PROMPT, format_chunk_text, format_partial_summaries
)

log = logging.getLogger(__name__)


def _preflight_or_raise(
    *,
    provider: str,
    model: str,
    system_prompt: Optional[str],
    user_prompt: str,
    max_output_tokens: int,
    tag: str
) -> None:
    """Token preflight with configured budgets; raise if it won't fit."""
    messages = [{"role": "user", "content": user_prompt}]
    budget = TokenBudget(
        context_window=SETTINGS.model_context_window,
        max_output_tokens=max_output_tokens,
        safety_margin=SETTINGS.token_safety_margin
    )

    input_tokens, fits = plan_fit(
        provider=provider,
        model=model,
        messages=messages,
        budget=budget,
        system=system_prompt,
        encoding=SETTINGS.openai_encoding
    )

    log.info(
        f"[token-check] {tag}: input={input_tokens} fits={fits} "
        f"(ctx={budget.context_window}, out={budget.max_output_tokens}, "
        f"margin={budget.safety_margin})"
    )

    if not fits:
        raise ValueError(
            f"Token preflight failed for {tag}. "
            f"Increase chunking or reduce prompt/content. "
            f"input={input_tokens}, ctx={budget.context_window}, "
            f"planned_out={budget.max_output_tokens}, margin={budget.safety_margin}"
        )


def legacy_map_reduce_summarize(
    chunk_segments: List[List[Dict]],
    provider: str = None,
    model: str = None,
    template_type: str = "DEFAULT"
) -> str:
    """Legacy-proven map-reduce summarization with template-specific prompts."""
    provider = provider or SETTINGS.provider
    model = model or SETTINGS.model

    system_prompt = get_system_prompt(template_type)
    chunk_context = get_chunk_context(template_type)
    reduce_context = get_reduce_context(template_type)

    log.info(f"Summarizing {len(chunk_segments)} chunks with {provider} using {template_type} template")

    # Map phase
    partial_summaries = []
    for i, chunk in enumerate(chunk_segments):
        log.info(f"Summarizing chunk {i+1}/{len(chunk_segments)}")

        chunk_text = format_chunk_text(chunk)

        if chunk_context:
            prompt = f"{chunk_context}\n\n{CHUNK_PROMPT.format(chunk=chunk_text)}"
        else:
            prompt = CHUNK_PROMPT.format(chunk=chunk_text)

        _preflight_or_raise(
            provider=provider,
            model=model,
            system_prompt=system_prompt,
            user_prompt=prompt,
            max_output_tokens=800,
            tag=f"map[{i+1}]"
        )

        summary = call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            provider=provider,
            max_tokens=800
        )
        partial_summaries.append(summary)

    # Reduce phase
    parts_text = format_partial_summaries(partial_summaries)

    if reduce_context:
        final_prompt = f"{reduce_context}\n\n{REDUCE_PROMPT.format(parts=parts_text)}"
    else:
        final_prompt = REDUCE_PROMPT.format(parts=parts_text)

    _preflight_or_raise(
        provider=provider,
        model=model,
        system_prompt=system_prompt,
        user_prompt=final_prompt,
        max_output_tokens=SETTINGS.summary_max_tokens,
        tag="reduce"
    )

    final_summary = call_llm(
        prompt=final_prompt,
        system_prompt=system_prompt,
        provider=provider,
        max_tokens=SETTINGS.summary_max_tokens
    )

    return final_summary


def template_aware_summarize(
    chunk_segments: List[List[Dict]],
    provider: str,
    model: str,
    template_config
) -> str:
    """Template-aware summarization using TemplateAwareStrategy."""
    strategy = TemplateAwareStrategy(template_config)
    return strategy.summarize(chunk_segments, provider, model)


def run(
    transcript_path: Path,
    provider: str = None,
    model: str = None,
    chunk_seconds: int = None,
    cod_passes: int = None,
    output_dir: Path = None,
    template: SummaryTemplate = None,
    auto_detect_template: bool = None
) -> tuple[Path, Path]:
    """Run the complete summarization pipeline.

    Args:
        transcript_path: Path to transcript file
        provider: LLM provider (openai/anthropic)
        model: Model identifier
        chunk_seconds: Chunk duration in seconds
        cod_passes: Chain-of-Density passes
        output_dir: Output directory (deprecated, uses data structure)
        template: Summary template to use
        auto_detect_template: Whether to auto-detect template

    Returns:
        Tuple of (json_path, md_path)
    """
    # Apply defaults
    provider = provider or SETTINGS.provider
    model = model or SETTINGS.model
    chunk_seconds = chunk_seconds or SETTINGS.summary_chunk_seconds
    cod_passes = cod_passes or SETTINGS.summary_cod_passes
    template = template or SummaryTemplate(SETTINGS.summary_template)
    auto_detect = auto_detect_template if auto_detect_template is not None else SETTINGS.summary_auto_detect

    # Load transcript
    segments = load_transcript(transcript_path)
    log.info(f"Loaded {len(segments)} segments")

    # Auto-detect template if enabled
    detected_template = template
    if auto_detect:
        full_text = segments_to_text(segments)
        detected_template = detect_meeting_type(full_text)
        log.info(f"Auto-detected template: {detected_template}")

    log.info(f"Summarizing with {provider}/{model}")
    log.info(f"Template: {detected_template}, Chunk: {chunk_seconds}s, CoD: {cod_passes}")

    template_config = SummaryTemplates.get_template(detected_template)

    # Chunk transcript
    chunk_segments = chunk_transcript(segments, chunk_seconds)
    log.info(f"Split into {len(chunk_segments)} chunks")

    # Select summarization strategy
    if detected_template == SummaryTemplate.REQUIREMENTS:
        summary = template_aware_summarize(chunk_segments, provider, model, template_config)
    else:
        summary = legacy_map_reduce_summarize(
            chunk_segments,
            provider,
            model=model,
            template_type=detected_template.value.upper()
        )

    # Chain-of-Density refinement (skip for structured templates)
    if cod_passes > 0 and detected_template not in [SummaryTemplate.REQUIREMENTS, SummaryTemplate.SOP]:
        summary = chain_of_density_pass(summary, provider, cod_passes)
    elif detected_template in [SummaryTemplate.REQUIREMENTS, SummaryTemplate.SOP]:
        log.info(f"Skipping CoD for {detected_template} (preserving structure)")

    # Generate JSON content
    if detected_template == SummaryTemplate.REQUIREMENTS:
        json_content = create_requirements_json(
            transcript_path, provider, model,
            detected_template, template_config, summary
        )
    else:
        json_content = extract_structured_json(summary, provider, model)

    # Save outputs
    json_path, md_path = save_summary_outputs(
        transcript_path=transcript_path,
        summary=summary,
        json_content=json_content,
        template=detected_template,
        template_config=template_config,
        provider=provider,
        model=model,
        chunk_seconds=chunk_seconds,
        cod_passes=cod_passes,
        auto_detected=auto_detect and detected_template != template
    )

    log.info(f"Summary saved: {json_path}, {md_path}")
    return json_path, md_path
