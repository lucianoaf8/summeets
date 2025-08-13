"""Summarization pipeline migrated from summarize_meeting.py"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from ..config import SETTINGS
from ..providers import openai_client, anthropic_client

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

def map_reduce_summarize(chunks: List[str], provider: str = "openai") -> str:
    """Map-reduce summarization across chunks."""
    log.info(f"Summarizing {len(chunks)} chunks with {provider}")
    
    # Map phase - summarize each chunk
    summaries = []
    for i, chunk in enumerate(chunks):
        log.info(f"Summarizing chunk {i+1}/{len(chunks)}")
        
        if provider == "openai":
            summary = openai_client.summarize_text(
                f"Summarize this meeting transcript segment:\n\n{chunk}",
                system_prompt="You are an expert meeting summarizer. Extract key points, decisions, and action items.",
                max_tokens=500
            )
        elif provider == "anthropic":
            summary = anthropic_client.summarize_text(
                f"Summarize this meeting transcript segment:\n\n{chunk}",
                system_prompt="You are an expert meeting summarizer. Extract key points, decisions, and action items.",
                max_tokens=500
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        summaries.append(summary)
    
    # Reduce phase - combine summaries
    combined = '\n\n'.join(summaries)
    
    if provider == "openai":
        final = openai_client.summarize_text(
            f"Combine these meeting segment summaries into a cohesive final summary:\n\n{combined}",
            system_prompt="Create a comprehensive meeting summary with key points, decisions, and action items.",
            max_tokens=SETTINGS.summary_max_tokens
        )
    else:
        final = anthropic_client.summarize_text(
            f"Combine these meeting segment summaries into a cohesive final summary:\n\n{combined}",
            system_prompt="Create a comprehensive meeting summary with key points, decisions, and action items.",
            max_tokens=SETTINGS.summary_max_tokens
        )
    
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
    output_dir: Path = None
) -> Path:
    """Run the complete summarization pipeline."""
    # Use config defaults if not provided
    provider = provider or SETTINGS.provider
    model = model or SETTINGS.model
    chunk_seconds = chunk_seconds or SETTINGS.summary_chunk_seconds
    cod_passes = cod_passes or SETTINGS.summary_cod_passes
    output_dir = output_dir or SETTINGS.out_dir
    
    # Update settings if provided
    if provider:
        SETTINGS.provider = provider
    if model:
        SETTINGS.model = model
    
    log.info(f"Summarizing with {provider}/{model}")
    log.info(f"Chunk size: {chunk_seconds}s, CoD passes: {cod_passes}")
    
    # Load transcript
    segments = load_transcript(transcript_path)
    log.info(f"Loaded {len(segments)} segments")
    
    # Chunk transcript
    chunks = chunk_transcript(segments, chunk_seconds)
    log.info(f"Split into {len(chunks)} chunks")
    
    # Map-reduce summarization
    summary = map_reduce_summarize(chunks, provider)
    
    # Chain-of-Density refinement
    if cod_passes > 0:
        log.info(f"Applying {cod_passes} Chain-of-Density passes")
        summary = chain_of_density_pass(summary, provider, cod_passes)
    
    # Save outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = transcript_path.stem
    
    # Save as JSON
    summary_data = {
        "transcript": str(transcript_path),
        "provider": provider,
        "model": model,
        "chunk_seconds": chunk_seconds,
        "cod_passes": cod_passes,
        "timestamp": datetime.now().isoformat(),
        "summary": summary
    }
    
    json_path = output_dir / f"{base_name}.summary.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    # Save as Markdown
    md_path = output_dir / f"{base_name}.summary.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# Meeting Summary\n\n")
        f.write(f"**Transcript:** {transcript_path.name}\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Model:** {provider}/{model}\n\n")
        f.write(f"## Summary\n\n{summary}\n")
    
    log.info(f"Saved summary: {json_path}")
    log.info(f"Saved summary: {md_path}")
    
    return json_path