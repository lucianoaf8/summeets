"""Summarization pipeline for summeets."""

from .pipeline import run as _run_pipeline
from .templates import SummaryTemplates, detect_meeting_type
from ..models import SummaryTemplate
from pathlib import Path
from typing import Tuple, Optional

def summarize_transcript(
    transcript_path: Path,
    provider: str = None,
    model: str = None,
    chunk_seconds: int = None,
    cod_passes: int = None,
    output_dir: Path = None,
    max_output_tokens: int = None,
    template: SummaryTemplate = None,
    auto_detect_template: bool = None,
    **kwargs  # Accept additional parameters for forward compatibility
) -> Tuple[Path, Path]:
    """
    Wrapper for CLI/GUI compatibility.
    Returns (md_path, json_path).
    
    Args:
        transcript_path: Path to transcript JSON file
        provider: LLM provider name
        model: Model name
        chunk_seconds: Chunk size for processing
        cod_passes: Chain-of-Density passes
        output_dir: Output directory
        max_output_tokens: Maximum output tokens (applied via settings)
        template: Summary template to use
        auto_detect_template: Whether to auto-detect template type
        **kwargs: Additional parameters for forward compatibility
    """
    # Handle max_output_tokens by temporarily updating settings
    original_max_tokens = None
    if max_output_tokens is not None:
        from ..utils.config import SETTINGS
        original_max_tokens = SETTINGS.summary_max_tokens
        SETTINGS.summary_max_tokens = max_output_tokens
    
    try:
        json_path = _run_pipeline(
            transcript_path, 
            provider=provider,
            model=model,
            chunk_seconds=chunk_seconds,
            cod_passes=cod_passes,
            output_dir=output_dir,
            template=template,
            auto_detect_template=auto_detect_template
        )
    finally:
        # Restore original setting
        if original_max_tokens is not None:
            from ..utils.config import SETTINGS
            SETTINGS.summary_max_tokens = original_max_tokens
    # The pipeline saves both MD and JSON, construct MD path
    md_path = json_path.with_suffix('.md') if json_path else None
    # Actually, the pipeline uses .summary.md extension
    base_name = transcript_path.stem
    output_dir = output_dir or Path("out")
    md_path = output_dir / f"{base_name}.summary.md"
    
    return md_path, json_path

# Also export the original function
run = _run_pipeline

__all__ = ["summarize_transcript", "run", "SummaryTemplates", "SummaryTemplate", "detect_meeting_type"]