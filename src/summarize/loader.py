"""Transcript loading utilities for summarization pipeline.

This module provides functions for loading transcript files in various formats
(JSON, SRT) and converting them to standardized segment structures for processing.

Functions:
    load_transcript: Load transcript from JSON or SRT file
    segments_to_text: Convert segments to plain text
    get_transcript_duration: Calculate total transcript duration
"""
import json
import logging
from pathlib import Path
from typing import List, Dict

log = logging.getLogger(__name__)


def load_transcript(transcript_path: Path) -> List[Dict]:
    """Load transcript from JSON or SRT file.

    Args:
        transcript_path: Path to transcript file (.json or .srt)

    Returns:
        List of segment dictionaries with 'speaker', 'text', 'start', 'end' keys

    Raises:
        FileNotFoundError: If transcript file doesn't exist
        json.JSONDecodeError: If JSON parsing fails
    """
    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    suffix = transcript_path.suffix.lower()

    # Handle SRT files
    if suffix == '.srt':
        from ..transcribe.formatting import parse_srt_file
        return parse_srt_file(transcript_path)

    # Handle plain text files
    if suffix == '.txt':
        with open(transcript_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        if not content:
            log.warning("Empty transcript file: %s", transcript_path)
            return []
        # Wrap full text as a single segment
        return [{"speaker": "UNKNOWN", "text": content, "start": 0.0, "end": 0.0}]

    # Handle JSON files (default)
    with open(transcript_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # Handle both formats: direct array or {"segments": [...]}
        return data if isinstance(data, list) else data.get("segments", [])


def segments_to_text(segments: List[Dict], include_speakers: bool = True) -> str:
    """Convert segments to plain text.

    Args:
        segments: List of transcript segments
        include_speakers: Whether to include speaker labels

    Returns:
        Formatted transcript text
    """
    lines = []
    for segment in segments:
        speaker = segment.get('speaker', 'Unknown')
        text = segment.get('text', '').strip()

        if text:
            if include_speakers:
                lines.append(f"[{speaker}]: {text}")
            else:
                lines.append(text)

    return '\n'.join(lines)


def get_transcript_duration(segments: List[Dict]) -> float:
    """Calculate total transcript duration in seconds.

    Args:
        segments: List of transcript segments

    Returns:
        Duration in seconds
    """
    if not segments:
        return 0.0

    return max(s.get('end', 0) for s in segments)
