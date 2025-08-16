"""Summarization pipeline migrated from summarize_meeting.py"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from ..utils.config import SETTINGS
from ..providers import openai_client, anthropic_client
from ..models import SummaryTemplate
from .templates import SummaryTemplates, detect_meeting_type, format_sop_output

log = logging.getLogger(__name__)

def load_transcript(transcript_path: Path) -> List[Dict]:
    """Load transcript from JSON file."""
    with open(transcript_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def chunk_transcript(segments: List[Dict], chunk_seconds: int = 1800) -> List[str]:
    """Split transcript into time-based chunks for summarization."""
    chunks = []
    current_chunk = []
    current_duration = 0
    
    for segment in segments:
        segment_duration = segment.get('end', 0) - segment.get('start', 0)
        
        if current_duration + segment_duration > chunk_seconds and current_chunk:
            # Save current chunk
            chunk_text = '\n'.join([
                f"[{s.get('speaker', 'Unknown')}]: {s.get('text', '')}"
                for s in current_chunk
            ])
            chunks.append(chunk_text)
            current_chunk = []
            current_duration = 0
        
        current_chunk.append(segment)
        current_duration += segment_duration
    
    # Add remaining
    if current_chunk:
        chunk_text = '\n'.join([
            f"[{s.get('speaker', 'Unknown')}]: {s.get('text', '')}"
            for s in current_chunk
        ])
        chunks.append(chunk_text)
    
    return chunks

def map_reduce_summarize(
    chunks: List[str], 
    provider: str = "openai", 
    template: SummaryTemplate = SummaryTemplate.DEFAULT
) -> str:
    """Map-reduce summarization across chunks using specified template."""
    log.info(f"Summarizing {len(chunks)} chunks with {provider} using {template} template")
    
    # Get template configuration
    template_config = SummaryTemplates.get_template(template)
    
    # Map phase - summarize each chunk
    summaries = []
    for i, chunk in enumerate(chunks):
        log.info(f"Summarizing chunk {i+1}/{len(chunks)}")
        
        # Use template-specific system prompt for chunks
        chunk_system_prompt = (
            f"{template_config.system_prompt} "
            f"Summarize this segment focusing on content relevant to a {template_config.name.lower()}."
        )
        
        if provider == "openai":
            summary = openai_client.summarize_text(
                f"Summarize this meeting transcript segment:\n\n{chunk}",
                system_prompt=chunk_system_prompt,
                max_tokens=500
            )
        elif provider == "anthropic":
            summary = anthropic_client.summarize_text(
                f"Summarize this meeting transcript segment:\n\n{chunk}",
                system_prompt=chunk_system_prompt,
                max_tokens=500
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        summaries.append(summary)
    
    # Reduce phase - combine summaries using template
    combined = '\n\n'.join(summaries)
    final_prompt = template_config.user_prompt_template.format(transcript=combined)
    
    if provider == "openai":
        final = openai_client.summarize_text(
            final_prompt,
            system_prompt=template_config.system_prompt,
            max_tokens=template_config.max_tokens
        )
    else:
        final = anthropic_client.summarize_text(
            final_prompt,
            system_prompt=template_config.system_prompt,
            max_tokens=template_config.max_tokens
        )
    
    # Apply template-specific formatting
    if template == SummaryTemplate.SOP:
        final = format_sop_output(final, template_config)
    
    return final

def chain_of_density_pass(text: str, provider: str = "openai", passes: int = 2) -> str:
    """Apply Chain-of-Density summarization."""
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
) -> Path:
    """Run the complete summarization pipeline."""
    # Use config defaults if not provided
    provider = provider or SETTINGS.provider
    model = model or SETTINGS.model
    chunk_seconds = chunk_seconds or SETTINGS.summary_chunk_seconds
    cod_passes = cod_passes or SETTINGS.summary_cod_passes
    output_dir = output_dir or SETTINGS.out_dir
    template = template or SummaryTemplate(SETTINGS.summary_template)
    auto_detect_template = auto_detect_template if auto_detect_template is not None else SETTINGS.summary_auto_detect
    
    # Update settings if provided
    if provider:
        SETTINGS.provider = provider
    if model:
        SETTINGS.model = model
    
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
    
    # Chunk transcript
    chunks = chunk_transcript(segments, chunk_seconds)
    log.info(f"Split into {len(chunks)} chunks")
    
    # Map-reduce summarization with template
    summary = map_reduce_summarize(chunks, provider, detected_template)
    
    # Chain-of-Density refinement
    if cod_passes > 0:
        log.info(f"Applying {cod_passes} Chain-of-Density passes")
        summary = chain_of_density_pass(summary, provider, cod_passes)
    
    # Save outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = transcript_path.stem
    
    # Get template info for metadata
    template_config = SummaryTemplates.get_template(detected_template)
    
    # Save as JSON
    summary_data = {
        "transcript": str(transcript_path),
        "provider": provider,
        "model": model,
        "chunk_seconds": chunk_seconds,
        "cod_passes": cod_passes,
        "template": detected_template.value,
        "template_name": template_config.name,
        "auto_detected": auto_detect_template and detected_template != template,
        "timestamp": datetime.now().isoformat(),
        "summary": summary
    }
    
    json_path = output_dir / f"{base_name}.summary.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
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
    
    return json_path