"""Transcription pipeline for summeets."""

from .pipeline import run as _run_pipeline, TranscriptionPipeline
from pathlib import Path
from typing import Tuple

def transcribe_audio(audio_path: Path = None, output_dir: Path = None) -> Tuple[Path, Path, Path]:
    """
    Wrapper for CLI/GUI compatibility.
    Returns (json_path, srt_path, audit_path).
    
    Args:
        audio_path: Path to audio file or directory
        output_dir: Output directory (optional)
    
    Returns:
        Tuple of (json_path, srt_path, audit_path)
    """
    # Use the pipeline with both parameters
    json_path = _run_pipeline(audio_path, output_dir)
    
    # Generate expected companion files (even if not implemented yet)
    if json_path and json_path.exists():
        base_path = json_path.with_suffix('')
        srt_path = base_path.with_suffix('.srt')
        audit_path = base_path.with_suffix('.audit.json')
        
        # Create placeholder SRT file if it doesn't exist
        if not srt_path.exists():
            _create_placeholder_srt(json_path, srt_path)
        
        # Create placeholder audit file if it doesn't exist  
        if not audit_path.exists():
            _create_placeholder_audit(json_path, audit_path)
    else:
        srt_path = json_path
        audit_path = json_path
        
    return json_path, srt_path, audit_path


def _create_placeholder_srt(json_path: Path, srt_path: Path) -> None:
    """Create a basic SRT file from JSON transcript."""
    try:
        import json
        with open(json_path, 'r', encoding='utf-8') as f:
            segments = json.load(f)
        
        srt_lines = []
        for i, segment in enumerate(segments, 1):
            start_time = _format_srt_time(segment.get('start', 0))
            end_time = _format_srt_time(segment.get('end', 0))
            text = segment.get('text', '')
            speaker = segment.get('speaker', '')
            
            if speaker:
                text = f"[{speaker}] {text}"
            
            srt_lines.extend([
                str(i),
                f"{start_time} --> {end_time}",
                text,
                ""
            ])
        
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_lines))
            
    except Exception:
        # If SRT creation fails, create empty file
        srt_path.touch()


def _create_placeholder_audit(json_path: Path, audit_path: Path) -> None:
    """Create a basic audit file."""
    try:
        import json
        from datetime import datetime
        
        audit_data = {
            "source_file": str(json_path),
            "created_at": datetime.now().isoformat(),
            "segments_count": 0,
            "total_duration": 0,
            "speakers": []
        }
        
        # Try to extract basic info from transcript
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                segments = json.load(f)
            
            audit_data["segments_count"] = len(segments)
            
            if segments:
                audit_data["total_duration"] = segments[-1].get('end', 0)
                speakers = set()
                for segment in segments:
                    if segment.get('speaker'):
                        speakers.add(segment['speaker'])
                audit_data["speakers"] = list(speakers)
        except Exception:
            pass
        
        with open(audit_path, 'w', encoding='utf-8') as f:
            json.dump(audit_data, f, indent=2)
            
    except Exception:
        # If audit creation fails, create empty file
        audit_path.touch()


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

# Also export the original function
run = _run_pipeline

__all__ = ["transcribe_audio", "run", "TranscriptionPipeline"]