"""
Transcript formatting utilities.
Handles converting raw transcription output to structured formats.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

from ..models import Word, Segment

log = logging.getLogger(__name__)


def parse_replicate_output(output: Dict) -> List[Segment]:
    """
    Parse Replicate transcription output into structured segments.
    
    Args:
        output: Raw output from Replicate API
        
    Returns:
        List of parsed segments
    """
    segments = []
    
    for seg_data in output.get("segments", []):
        # Parse words
        words = []
        for word_data in seg_data.get("words", []):
            words.append(Word(
                start=word_data.get("start", 0.0),
                end=word_data.get("end", 0.0),
                text=word_data.get("word", "").strip(),
                confidence=word_data.get("confidence")
            ))
        
        # Create segment
        segment = Segment(
            start=seg_data.get("start", 0.0),
            end=seg_data.get("end", 0.0),
            text=seg_data.get("text", "").strip(),
            speaker=seg_data.get("speaker"),
            words=words if words else None,
            confidence=seg_data.get("confidence")
        )
        
        segments.append(segment)
    
    log.info(f"Parsed {len(segments)} segments from transcription")
    return segments


def save_json_transcript(segments: List[Segment], output_path: Path) -> None:
    """
    Save segments as JSON transcript.
    
    Args:
        segments: List of transcript segments
        output_path: Output file path
    """
    transcript_data = [seg.to_dict() for seg in segments]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, indent=2, ensure_ascii=False)
    
    log.info(f"Saved JSON transcript: {output_path}")


def save_text_transcript(segments: List[Segment], output_path: Path) -> None:
    """
    Save segments as readable text transcript.
    
    Args:
        segments: List of transcript segments
        output_path: Output file path
    """
    lines = []
    
    for segment in segments:
        speaker_label = segment.speaker or "Unknown"
        timestamp = format_timestamp(segment.start)
        lines.append(f"[{timestamp}] {speaker_label}: {segment.text}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    log.info(f"Saved text transcript: {output_path}")


def save_srt_transcript(segments: List[Segment], output_path: Path) -> None:
    """
    Save segments as SRT subtitle file.
    
    Args:
        segments: List of transcript segments
        output_path: Output file path
    """
    lines = []
    
    for i, segment in enumerate(segments, 1):
        start_time = format_srt_timestamp(segment.start)
        end_time = format_srt_timestamp(segment.end)
        speaker_text = f"[{segment.speaker}] " if segment.speaker else ""
        
        lines.extend([
            str(i),
            f"{start_time} --> {end_time}",
            f"{speaker_text}{segment.text}",
            ""
        ])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    log.info(f"Saved SRT transcript: {output_path}")


def parse_srt_file(srt_path: Path) -> List[Dict]:
    """
    Parse SRT or WebVTT file into segment dictionaries.

    Args:
        srt_path: Path to SRT/WebVTT file

    Returns:
        List of segment dictionaries
    """
    segments = []

    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if it's WebVTT format
    is_webvtt = content.strip().startswith('WEBVTT')

    if is_webvtt:
        # WebVTT format - single newlines between cues
        lines = content.strip().split('\n')
        i = 0

        # Skip header and initial blank lines
        while i < len(lines) and (lines[i].startswith('WEBVTT') or not lines[i].strip()):
            i += 1

        while i < len(lines):
            # Look for timestamp line
            if '-->' in lines[i]:
                try:
                    timestamp_line = lines[i]
                    # Parse timestamps
                    start_str, end_str = timestamp_line.split(' --> ')
                    start_seconds = _parse_srt_timestamp(start_str.strip())
                    end_seconds = _parse_srt_timestamp(end_str.strip())

                    # Next line(s) contain text
                    i += 1
                    text_parts = []
                    while i < len(lines) and lines[i].strip() and '-->' not in lines[i]:
                        text_parts.append(lines[i].strip())
                        i += 1

                    text = ' '.join(text_parts)

                    # Extract speaker if present (format: "Name: text" or "[Name] text")
                    speaker = None
                    if ':' in text and text.index(':') < 30:  # Speaker name typically short
                        parts = text.split(':', 1)
                        speaker = parts[0].strip()
                        text = parts[1].strip()
                    elif text.startswith('[') and ']' in text:
                        bracket_end = text.index(']')
                        speaker = text[1:bracket_end]
                        text = text[bracket_end+1:].strip()

                    if text:  # Only add if there's actual text
                        segments.append({
                            'start': start_seconds,
                            'end': end_seconds,
                            'text': text,
                            'speaker': speaker
                        })
                except (ValueError, IndexError) as e:
                    log.warning(f"Failed to parse WebVTT cue: {e}")
            i += 1
    else:
        # Standard SRT format - double newlines between blocks
        blocks = content.strip().split('\n\n')

        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue

            try:
                # Line 0: index (skip)
                # Line 1: timestamp
                # Line 2+: text
                timestamp_line = lines[1]
                text_lines = lines[2:]

                # Parse timestamps
                start_str, end_str = timestamp_line.split(' --> ')
                start_seconds = _parse_srt_timestamp(start_str.strip())
                end_seconds = _parse_srt_timestamp(end_str.strip())

                # Combine text lines
                text = ' '.join(text_lines)

                # Extract speaker if present
                speaker = None
                if text.startswith('[') and ']' in text:
                    bracket_end = text.index(']')
                    speaker = text[1:bracket_end]
                    text = text[bracket_end+1:].strip()

                segments.append({
                    'start': start_seconds,
                    'end': end_seconds,
                    'text': text,
                    'speaker': speaker
                })
            except (ValueError, IndexError) as e:
                log.warning(f"Failed to parse SRT block: {e}")
                continue

    log.info(f"Parsed {len(segments)} segments from {'WebVTT' if is_webvtt else 'SRT'} file")
    return segments


def _parse_srt_timestamp(timestamp_str: str) -> float:
    """Parse SRT timestamp (HH:MM:SS,mmm) to seconds."""
    # Replace comma with dot for milliseconds
    timestamp_str = timestamp_str.replace(',', '.')

    # Split into time parts
    time_parts = timestamp_str.split(':')
    hours = int(time_parts[0])
    mins = int(time_parts[1])
    secs = float(time_parts[2])

    return hours * 3600 + mins * 60 + secs


def format_transcript_output(
    segments: List[Segment],
    base_path: Path,
    formats: Optional[List[str]] = None
) -> Dict[str, Path]:
    """
    Save transcript in multiple formats.
    
    Args:
        segments: List of transcript segments
        base_path: Base path for output files (without extension)
        formats: List of formats to save ("json", "txt", "srt")
        
    Returns:
        Dictionary mapping format names to output file paths
    """
    if not formats:
        formats = ["json", "txt", "srt"]
    
    output_paths = {}
    
    if "json" in formats:
        json_path = base_path.with_suffix(".json")
        save_json_transcript(segments, json_path)
        output_paths["json"] = json_path
    
    if "txt" in formats:
        txt_path = base_path.with_suffix(".txt")
        save_text_transcript(segments, txt_path)
        output_paths["txt"] = txt_path
    
    if "srt" in formats:
        srt_path = base_path.with_suffix(".srt")
        save_srt_transcript(segments, srt_path)
        output_paths["srt"] = srt_path
    
    return output_paths


def format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS timestamp."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def format_srt_timestamp(seconds: float) -> str:
    """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"