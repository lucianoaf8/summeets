"""
Transcript formatting utilities.
Handles converting raw transcription output to structured formats.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class Word:
    """Individual word with timing information."""
    start: float
    end: float
    text: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text
        }


@dataclass
class Segment:
    """Text segment with speaker attribution and word-level timing."""
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    words: Optional[List[Word]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "speaker": self.speaker,
            "words": [w.to_dict() for w in (self.words or [])]
        }


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
                text=word_data.get("word", "").strip()
            ))
        
        # Create segment
        segment = Segment(
            start=seg_data.get("start", 0.0),
            end=seg_data.get("end", 0.0),
            text=seg_data.get("text", "").strip(),
            speaker=seg_data.get("speaker"),
            words=words if words else None
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