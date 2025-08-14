"""
DEPRECATED: Legacy summarize.py module.

This file has been replaced by:
- core/summarize/pipeline.py - Main summarization pipeline

For new code, use:
    from core.summarize.pipeline import run
    # or 
    from core.summarize import summarize_transcript

This module provides backward compatibility only.
"""
import warnings
from pathlib import Path
from typing import Optional

# Issue deprecation warning
warnings.warn(
    "core.summarize module is deprecated. "
    "Use core.summarize.pipeline instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import new functionality for backward compatibility
from .summarize.pipeline import run as _new_run


def summarize_transcript(
    transcript_path: Path,
    provider: Optional[str] = None,
    output_dir: Optional[Path] = None
) -> Path:
    """
    DEPRECATED: Use core.summarize.pipeline.run() instead.
    
    Legacy function for backward compatibility.
    """
    warnings.warn(
        "summarize_transcript() is deprecated. Use core.summarize.pipeline.run() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    return _new_run(
        transcript_path=transcript_path,
        provider=provider,
        output_dir=output_dir
    )


def main():
    """
    DEPRECATED: Use core.summarize.pipeline directly.
    
    Legacy main function for backward compatibility.
    """
    warnings.warn(
        "core.summarize.main() is deprecated. Use core.summarize.pipeline.run() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    return _new_run()


# Backward compatibility exports
__all__ = ["summarize_transcript", "main"]