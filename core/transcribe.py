"""
DEPRECATED: Legacy transcribe.py module.

This file has been refactored into a modular architecture:
- core/transcribe/pipeline.py - Main transcription pipeline
- core/audio/ - Audio processing utilities
- core/transcription/ - Transcription API and formatting

For new code, use:
    from core.transcribe.new_pipeline import run
    # or
    from core.transcribe.new_pipeline import TranscriptionPipeline

This module provides backward compatibility only.
"""
import warnings
from pathlib import Path
from typing import Optional

# Issue deprecation warning
warnings.warn(
    "core.transcribe module is deprecated. "
    "Use core.transcribe.new_pipeline instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import and expose new functionality for backward compatibility
from .transcribe.pipeline import run as _new_run, TranscriptionPipeline


def transcribe_audio(
    audio_path: Optional[Path] = None,
    output_dir: Optional[Path] = None
) -> Path:
    """
    DEPRECATED: Use core.transcribe.new_pipeline.run() instead.
    
    Legacy function for backward compatibility.
    """
    warnings.warn(
        "transcribe_audio() is deprecated. Use core.transcribe.new_pipeline.run() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    return _new_run(audio_path, output_dir)


def main():
    """
    DEPRECATED: Use core.transcribe.new_pipeline directly.
    
    Legacy main function for backward compatibility.
    """
    warnings.warn(
        "core.transcribe.main() is deprecated. Use core.transcribe.new_pipeline.run() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    return _new_run()


# Backward compatibility exports
__all__ = ["transcribe_audio", "main", "TranscriptionPipeline"]