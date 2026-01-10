# C:\Projects\summeets\core\summarize\pipeline.py
"""Summarization pipeline migrated from summarize_meeting.py (token-aware)."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from ..utils.config import SETTINGS
from ..providers import openai_client, anthropic_client
from ..models import SummaryTemplate
from .templates import SummaryTemplates, detect_meeting_type, format_sop_output

# token preflight
from ..tokenizer import TokenBudget, plan_fit

log = logging.getLogger(__name__)


def validate_requirements_output(summary: str, transcript_text: str) -> str:
    """Validate that requirements output isn't generic."""
    
    # Check for generic indicators
    generic_patterns = [
        "REQ-F-001", "REQ-NF-001",  # Generic requirement IDs
        "As a manager, I want",      # Generic user stories
        "Acceptance Criteria:",      # Template language
        "Priority: Must",            # Template metadata
        "Stakeholder: Regional Service Team Lead",  # Template stakeholders
    ]
    
    if any(pattern in summary for pattern in generic_patterns):
        log.warning("Detected generic requirements template - attempting re-extraction")
        
        # Re-prompt with stronger instructions
        strict_prompt = (
            f"This transcript contains a real conversation:\n\n{transcript_text}\n\n"
            "Extract ONLY the actual requirements discussed. No generic templates, "
            "no user story format, no requirement IDs. Just what was really talked about. "
            "Start with: 'Based on this conversation, the actual requirements discussed were:'"
        )
        
        # Re-call LLM with stricter prompt
        if SETTINGS.provider == "anthropic":
            return anthropic_client.summarize_text(
                strict_prompt,
                system_prompt="Extract only real conversation content. No templates.",
                max_tokens=3000
            )
        elif SETTINGS.provider == "openai":
            return openai_client.summarize_text(
                strict_prompt,
                system_prompt="Extract only real conversation content. No templates.",
                max_tokens=3000
            )
    
    return summary


def load_transcript(transcript_path: Path) -> List[Dict]:
    """Load transcript from JSON or SRT file."""
    # Handle SRT files
    if transcript_path.suffix.lower() == '.srt':
        from ..transcribe.formatting import parse_srt_file
        return parse_srt_file(transcript_path)

    # Handle JSON files
    with open(transcript_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # Handle both formats: direct array or {"segments": [...]}
        return data if isinstance(data, list) else data.get("segments", [])


def chunk_transcript(segments: List[Dict], chunk_seconds: int = 1800) -> List[List[Dict]]:
    """Split transcript into time-based chunks, returning segment lists for timestamp formatting."""
    if chunk_seconds <= 0:
        return [segments]

    chunks = []
    current_chunk = []
    current_start = None

    for segment in segments:
        if current_start is None:
            current_start = segment.get('start', 0)

        current_chunk.append(segment)

        # Check if we've exceeded the time limit
        segment_end = segment.get('end', 0)
        if segment_end - current_start >= chunk_seconds:
            chunks.append(current_chunk)
            current_chunk = []
            current_start = None

    # Add remaining segments
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _preflight_or_raise(*, provider: str, model: str, system_prompt: Optional[str],
                        user_prompt: str, max_output_tokens: int, tag: str):
    """Token preflight with configured budgets; raise if it won't fit."""
    messages = [{"role": "user", "content": user_prompt}]
    budget = TokenBudget(
        context_window=model_context_window,
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
    log.info(f"[token-check] {tag}: input={input_tokens} fits={fits} "
             f"(ctx={budget.context_window}, out={budget.max_output_tokens}, margin={budget.safety_margin})")
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
    from .legacy_prompts import (
        SYSTEM_CORE, CHUNK_PROMPT, REDUCE_PROMPT,
        format_chunk_text, format_partial_summaries,
        get_system_prompt, get_chunk_context, get_reduce_context
    )

    provider = provider or SETTINGS.provider
    model = model or model

    # Get template-specific prompts
    system_prompt = get_system_prompt(template_type)
    chunk_context = get_chunk_context(template_type)
    reduce_context = get_reduce_context(template_type)

    log.info(f"Summarizing {len(chunk_segments)} chunks with {provider} using {template_type} template prompts")

    # Map phase - summarize each chunk with template-specific guidance
    partial_summaries = []
    for i, chunk in enumerate(chunk_segments):
        log.info(f"Summarizing chunk {i+1}/{len(chunk_segments)}")

        # Format chunk with timestamps
        chunk_text = format_chunk_text(chunk)

        # Build template-aware prompt
        if chunk_context:
            prompt = f"{chunk_context}\n\n{CHUNK_PROMPT.format(chunk=chunk_text)}"
        else:
            prompt = CHUNK_PROMPT.format(chunk=chunk_text)

        # Token preflight
        _preflight_or_raise(
            provider=provider,
            model=model,
            system_prompt=system_prompt,
            user_prompt=prompt,
            max_output_tokens=800,
            tag=f"map[{i+1}]"
        )

        # Call provider
        if provider == "openai":
            summary = openai_client.summarize_text(
                prompt,
                system_prompt=system_prompt,
                max_tokens=800  # Larger for detailed sections
            )
        elif provider == "anthropic":
            summary = anthropic_client.summarize_text(
                prompt,
                system_prompt=system_prompt,
                max_tokens=800
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

        partial_summaries.append(summary)

    # Reduce phase - combine into final structured report with template-specific guidance
    parts_text = format_partial_summaries(partial_summaries)

    # Build template-aware reduce prompt
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

    if provider == "openai":
        final_summary = openai_client.summarize_text(
            final_prompt,
            system_prompt=system_prompt,
            max_tokens=SETTINGS.summary_max_tokens
        )
    else:
        final_summary = anthropic_client.summarize_text(
            final_prompt,
            system_prompt=system_prompt,
            max_tokens=SETTINGS.summary_max_tokens
        )

    return final_summary


def template_aware_summarize(
    chunk_segments: List[List[Dict]],
    provider: str,
    model: str,
    template_config
) -> str:
    """Template-aware summarization that uses template-specific prompts instead of legacy ones."""
    log.info(f"Using template-aware summarization with {template_config.name}")

    # For requirements template, process all chunks with template prompts
    if len(chunk_segments) == 1:
        # Single chunk - use template prompts directly
        chunk = chunk_segments[0]
        
        # Better transcript formatting for requirements extraction
        chunk_text = []
        for segment in chunk:
            speaker = segment.get('speaker', 'Unknown')
            text = segment.get('text', '').strip()
            
            if text:  # Only include non-empty segments
                chunk_text.append(f"[{speaker}]: {text}")

        transcript_content = '\n'.join(chunk_text)
        
        # Add simple header for context
        formatted_transcript = f"MEETING TRANSCRIPT:\n\n{transcript_content}"

        # Use template prompts
        prompt = template_config.user_prompt_template.format(transcript=formatted_transcript)

        # Token preflight
        _preflight_or_raise(
            provider=provider,
            model=model,
            system_prompt=template_config.system_prompt,
            user_prompt=prompt,
            max_output_tokens=template_config.max_tokens,
            tag="template-single"
        )

        if provider == "openai":
            summary = openai_client.summarize_text(
                prompt,
                system_prompt=template_config.system_prompt,
                max_tokens=template_config.max_tokens
            )
        elif provider == "anthropic":
            # Enable extended thinking for requirements template only if model supports it
            # Extended thinking requires Claude 3.7 Sonnet or later
            model_supports_thinking = "claude-3-7" in model or "claude-4" in model
            enable_thinking = (
                template_config.name == "Requirements Extraction v3"
                and model_supports_thinking
            )
            summary = anthropic_client.summarize_text(
                prompt,
                system_prompt=template_config.system_prompt,
                max_tokens=template_config.max_tokens,
                enable_thinking=enable_thinking,
                thinking_budget=6000 if enable_thinking else 0
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

        # Validate output for requirements template (disabled - was over-constraining)
        # if template_config.name == "Requirements Extraction":
        #     summary = validate_requirements_output(summary, transcript_content)

        return summary
    else:
        # Multiple chunks - use template-aware map-reduce
        partial_summaries = []
        for i, chunk in enumerate(chunk_segments):
            log.info(f"Processing chunk {i+1}/{len(chunk_segments)} with template prompts")

            # Better transcript formatting for requirements extraction
            chunk_text = []
            for segment in chunk:
                speaker = segment.get('speaker', 'Unknown')
                text = segment.get('text', '').strip()
                
                if text:  # Only include non-empty segments
                    chunk_text.append(f"[{speaker}]: {text}")

            transcript_content = '\n'.join(chunk_text)

            # Use template prompts for each chunk
            prompt = (
                "Extract requirements from this transcript chunk using the same "
                "structure as the full analysis:\n\n" + transcript_content
            )

            _preflight_or_raise(
                provider=provider,
                model=model,
                system_prompt=template_config.system_prompt,
                user_prompt=prompt,
                max_output_tokens=800,
                tag=f"template-map[{i+1}]"
            )

            if provider == "openai":
                summary = openai_client.summarize_text(
                    prompt,
                    system_prompt=template_config.system_prompt,
                    max_tokens=800
                )
            elif provider == "anthropic":
                # Enable extended thinking for requirements template chunks only if model supports it
                # Extended thinking requires Claude 3.7 Sonnet or later
                model_supports_thinking = "claude-3-7" in model or "claude-4" in model
                enable_thinking = (
                    template_config.name == "Requirements Extraction v3"
                    and model_supports_thinking
                )
                # Note: max_tokens must be > thinking_budget, so use 4000 to accommodate 3000 thinking budget
                chunk_max_tokens = 4000 if enable_thinking else 800
                summary = anthropic_client.summarize_text(
                    prompt,
                    system_prompt=template_config.system_prompt,
                    max_tokens=chunk_max_tokens,
                    enable_thinking=enable_thinking,
                    thinking_budget=3000 if enable_thinking else 0
                )
            else:
                raise ValueError(f"Unknown provider: {provider}")

            partial_summaries.append(summary)

        # Combine partial summaries using template structure
        combined_prompt = (
            "Combine these partial requirements extractions into a final structured analysis. "
            "Merge and deduplicate requirements while maintaining the structure:\n\n"
            "Partial extractions:\n" + "\n\n---\n\n".join(partial_summaries)
        )

        _preflight_or_raise(
            provider=provider,
            model=model,
            system_prompt=template_config.system_prompt,
            user_prompt=combined_prompt,
            max_output_tokens=template_config.max_tokens,
            tag="template-reduce"
        )

        if provider == "openai":
            final_summary = openai_client.summarize_text(
                combined_prompt,
                system_prompt=template_config.system_prompt,
                max_tokens=template_config.max_tokens
            )
        else:
            # Enable extended thinking for requirements template reduce step only if model supports it
            # Extended thinking requires Claude 3.7 Sonnet or later
            model_supports_thinking = "claude-3-7" in model or "claude-4" in model
            enable_thinking = (
                template_config.name == "Requirements Extraction v3"
                and model_supports_thinking
            )
            # Use smaller thinking budget to ensure max_tokens > thinking_budget
            final_summary = anthropic_client.summarize_text(
                combined_prompt,
                system_prompt=template_config.system_prompt,
                max_tokens=template_config.max_tokens,
                enable_thinking=enable_thinking,
                thinking_budget=6000 if enable_thinking else 0
            )

        # Validate output for requirements template (disabled - was over-constraining)
        # if template_config.name == "Requirements Extraction":
        #     # For multi-chunk, create combined transcript for validation
        #     all_chunks_text = []
        #     for chunk in chunk_segments:
        #         for segment in chunk:
        #             speaker = segment.get('speaker', 'Unknown')
        #             text = segment.get('text', '').strip()
        #             timestamp = segment.get('start', 0)
        #             if text:
        #                 all_chunks_text.append(f"[{speaker} at {timestamp:.1f}s]: {text}")
        #     combined_transcript = '\n'.join(all_chunks_text)
        #     final_summary = validate_requirements_output(final_summary, combined_transcript)

        return final_summary


def chain_of_density_pass(text: str, provider: str = None, passes: int = 2) -> str:
    """Apply Chain-of-Density summarization."""
    provider = provider or SETTINGS.provider
    if provider == "openai":
        return openai_client.chain_of_density_summarize(text, passes)
    elif provider == "anthropic":
        return anthropic_client.chain_of_density_summarize(text, passes)
    else:
        raise ValueError(f"Unknown provider: {provider}")


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
    """Run the complete summarization pipeline."""
    # Use config defaults if not provided (immutable - never mutate SETTINGS)
    provider = provider or SETTINGS.provider
    model = model or model
    chunk_seconds = chunk_seconds or SETTINGS.summary_chunk_seconds
    cod_passes = cod_passes or SETTINGS.summary_cod_passes
    output_dir = output_dir or SETTINGS.out_dir
    template = template or SummaryTemplate(SETTINGS.summary_template)
    auto_detect_template = auto_detect_template if auto_detect_template is not None else SETTINGS.summary_auto_detect

    # Load transcript
    segments = load_transcript(transcript_path)
    log.info(f"Loaded {len(segments)} segments")

    # Auto-detect template if enabled
    detected_template = template
    if auto_detect_template:
        # Create full transcript text for analysis
        full_text = '\n'.join([
            f"[{s.get('speaker', 'Unknown')}]: {s.get('text', '')}"
            for s in segments
        ])
        detected_template = detect_meeting_type(full_text)
        log.info(f"Auto-detected template: {detected_template}")

    log.info(f"Summarizing with {provider}/{model}")
    log.info(f"Template: {detected_template}, Chunk size: {chunk_seconds}s, CoD passes: {cod_passes}")

    # Get template info for use in summarization
    template_config = SummaryTemplates.get_template(detected_template)

    # Chunk transcript (returns segment lists for timestamp formatting)
    chunk_segments = chunk_transcript(segments, chunk_seconds)
    log.info(f"Split into {len(chunk_segments)} chunks")

    # Use template-specific summarization for requirements template
    if detected_template == SummaryTemplate.REQUIREMENTS:
        summary = template_aware_summarize(chunk_segments, provider, model, template_config)
    else:
        # Legacy map-reduce summarization with template-specific prompts
        summary = legacy_map_reduce_summarize(
            chunk_segments,
            provider,
            model=model,
            template_type=detected_template.value.upper()
        )

    # Chain-of-Density refinement (skip for structured templates)
    if cod_passes > 0 and detected_template not in [SummaryTemplate.REQUIREMENTS, SummaryTemplate.SOP]:
        log.info(f"Applying {cod_passes} Chain-of-Density passes")
        summary = chain_of_density_pass(summary, provider, cod_passes)
    elif detected_template in [SummaryTemplate.REQUIREMENTS, SummaryTemplate.SOP]:
        log.info(f"Skipping Chain-of-Density for {detected_template} template (preserving structure)")

    # Skip JSON extraction for requirements template - it's not relevant
    if detected_template != SummaryTemplate.REQUIREMENTS:
        # JSON extraction using structured outputs (legacy approach)
        log.info("Extracting structured JSON data")
        json_instructions = (
            "Extract JSON for the following keys ONLY:\n"
            "executive_summary, decisions, action_items, risks, open_questions, timeline, stakeholders, next_steps, glossary.\n"
            "Base your JSON strictly on this final summary. Do not invent fields or content.\n\n"
            f"Final summary:\n{summary}"
        )

        # Token preflight for JSON extraction
        if provider == "openai":
            system_prompt = None  # structured_json_summarize likely wraps system prompt internally; keep input minimal
        else:
            system_prompt = "Return only minified JSON. No extra text."

        _preflight_or_raise(
            provider=provider,
            model=model,
            system_prompt=system_prompt,
            user_prompt=(
                "Return only minified JSON for this content. Include keys: "
                "executive_summary, decisions, action_items, risks, open_questions, timeline, stakeholders, next_steps, glossary.\n\n"
                + json_instructions
                if provider == "anthropic" else json_instructions
            ),
            max_output_tokens=SETTINGS.summary_max_tokens,
            tag="json-extract"
        )

        if provider == "openai":
            structured_json = openai_client.structured_json_summarize(json_instructions)
        else:
            # For Anthropic, use best-effort JSON formatting
            structured_json = anthropic_client.summarize_text(
                "Return only minified JSON for this content. No commentary. "
                "Include keys: executive_summary, decisions, action_items, risks, open_questions, timeline, stakeholders, next_steps, glossary.\n\n"
                + json_instructions,
                system_prompt="Return only minified JSON. No extra text.",
                max_tokens=SETTINGS.summary_max_tokens
            )
    else:
        log.info("Skipping JSON extraction for requirements template")
        # For requirements, create a simple structured JSON from the markdown content
        structured_json = json.dumps({
            "transcript": str(transcript_path),
            "provider": provider,
            "model": model,
            "template": detected_template.value,
            "template_name": template_config.name,
            "timestamp": datetime.now().isoformat(),
            "requirements_summary": summary
        }, indent=2)

    # Create new folder structure: data/summary/<filename>/<template>
    base_name = transcript_path.stem

    # Create output directory with new structure
    from ..utils.fsio import get_data_manager
    data_mgr = get_data_manager()
    summary_base_dir = data_mgr.base_dir / "summary"
    output_dir = summary_base_dir / base_name / detected_template.value
    output_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"Output directory: {output_dir}")

    # Save structured JSON with validation (legacy approach)
    json_path = output_dir / f"{base_name}.summary.json"
    try:
        # Validate JSON structure
        json.loads(structured_json)
        # Save validated structured JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(structured_json)
        log.info("Saved validated structured JSON")
    except json.JSONDecodeError as e:
        log.warning(f"JSON validation failed: {e}, saving best-effort JSON")
        # Fallback: save whatever we got for debugging
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(structured_json)
    except Exception as e:
        log.error(f"Failed to save JSON: {e}")
        # Ultimate fallback: save metadata with summary
        fallback_data = {
            "transcript": str(transcript_path),
            "provider": provider,
            "model": model,
            "chunk_seconds": chunk_seconds,
            "cod_passes": cod_passes,
            "template": detected_template.value,
            "template_name": template_config.name,
            "auto_detected": auto_detect_template and detected_template != template,
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "json_extraction_error": str(e)
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(fallback_data, f, indent=2, ensure_ascii=False)

    # Save as Markdown with template-specific formatting
    md_path = output_dir / f"{base_name}.summary.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        if detected_template == SummaryTemplate.SOP:
            # SOP template gets special header
            formatted_summary = summary.replace("{timestamp}", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            f.write(formatted_summary)
        else:
            # Standard format for other templates
            f.write(f"# {template_config.name}\n\n")
            f.write(f"**Transcript:** {transcript_path.name}\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Model:** {provider}/{model}\n")
            f.write(f"**Template:** {template_config.name}")
            if auto_detect_template and detected_template != template:
                f.write(f" (auto-detected)")
            f.write(f"\n\n")
            f.write(f"{summary}\n")

    log.info(f"Saved summary: {json_path}")
    log.info(f"Saved summary: {md_path}")

    return json_path, md_path
