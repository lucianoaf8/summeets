"""Transcript chunking utilities for summarization pipeline.

Provides strategies for splitting transcripts into manageable chunks
for LLM processing, including time-based and speaker-turn-based chunking.

Functions:
    chunk_transcript: Split by time duration
    chunk_by_speaker_turns: Split by speaker turn count
    format_chunk_text: Format chunk for LLM input
"""
import logging
from typing import List, Dict

log = logging.getLogger(__name__)


def chunk_transcript(
    segments: List[Dict],
    chunk_seconds: int = 1800
) -> List[List[Dict]]:
    """Split transcript into time-based chunks.

    Args:
        segments: List of transcript segments
        chunk_seconds: Maximum duration per chunk (default 30 minutes)

    Returns:
        List of segment lists, each representing a chunk
    """
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

    log.debug(f"Created {len(chunks)} chunks from {len(segments)} segments")
    return chunks


def chunk_by_speaker_turns(
    segments: List[Dict],
    max_turns: int = 50
) -> List[List[Dict]]:
    """Split transcript by speaker turn count.

    Args:
        segments: List of transcript segments
        max_turns: Maximum speaker turns per chunk

    Returns:
        List of segment lists
    """
    if max_turns <= 0:
        return [segments]

    chunks = []
    current_chunk = []
    turn_count = 0
    prev_speaker = None

    for segment in segments:
        speaker = segment.get('speaker', 'Unknown')

        # Count speaker changes
        if speaker != prev_speaker:
            turn_count += 1
            prev_speaker = speaker

        current_chunk.append(segment)

        if turn_count >= max_turns:
            chunks.append(current_chunk)
            current_chunk = []
            turn_count = 0
            prev_speaker = None

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def format_chunk_text(chunk: List[Dict], with_timestamps: bool = True) -> str:
    """Format chunk segments into text for LLM processing.

    Args:
        chunk: List of transcript segments
        with_timestamps: Whether to include timestamp markers

    Returns:
        Formatted text string
    """
    lines = []
    for segment in chunk:
        speaker = segment.get('speaker', 'Unknown')
        text = segment.get('text', '').strip()
        start = segment.get('start', 0)

        if text:
            if with_timestamps:
                timestamp = _format_timestamp(start)
                lines.append(f"[{timestamp}] [{speaker}]: {text}")
            else:
                lines.append(f"[{speaker}]: {text}")

    return '\n'.join(lines)


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
