"""
Audio file selection utilities.
Handles intelligent selection of the best quality audio file from a directory.
"""
import logging
from pathlib import Path
from typing import Dict, Optional, List
from .ffmpeg_ops import ffprobe_info

log = logging.getLogger(__name__)

SUPPORTED_EXTS = {".m4a", ".mka", ".ogg", ".mp3", ".wav", ".webm", ".flac"}

# Quality preferences for audio formats (higher = better)
FORMAT_SCORES = {
    ".m4a": 100,
    ".flac": 90,
    ".wav": 80,
    ".mka": 70,
    ".ogg": 60,
    ".mp3": 50,
    ".webm": 40
}


def get_audio_files(target: Path) -> List[Path]:
    """
    Get all audio files from a path (file or directory).
    
    Args:
        target: Path to audio file or directory
        
    Returns:
        List of audio file paths
        
    Raises:
        FileNotFoundError: If target doesn't exist
        ValueError: If no audio files found
    """
    if not target.exists():
        raise FileNotFoundError(f"Path not found: {target}")
    
    if target.is_file():
        if target.suffix.lower() in SUPPORTED_EXTS:
            return [target]
        else:
            raise ValueError(f"Unsupported audio format: {target.suffix}")
    
    # Directory - find all audio files
    audio_files = []
    for file_path in target.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTS:
            audio_files.append(file_path)
    
    if not audio_files:
        raise ValueError(f"No supported audio files found in: {target}")
    
    return audio_files


def score_audio_file(file_path: Path, audio_info: Optional[Dict] = None) -> float:
    """
    Score an audio file based on quality metrics.
    
    Args:
        file_path: Path to audio file
        audio_info: Optional ffprobe info (will be fetched if not provided)
        
    Returns:
        Quality score (higher = better)
    """
    score = 0.0
    
    # Format preference
    score += FORMAT_SCORES.get(file_path.suffix.lower(), 0)
    
    # Prefer normalized files
    if "norm" in file_path.stem.lower():
        score += 1000
    
    # Quality metrics from audio info
    if audio_info:
        # Sample rate (higher is generally better)
        sample_rate = audio_info.get("sample_rate", 0)
        if sample_rate:
            score += min(sample_rate / 1000, 100)  # Cap at 100 points
        
        # Bit rate (higher is better)
        bit_rate = audio_info.get("bit_rate", 0) 
        if bit_rate:
            score += min(bit_rate / 1000, 50)  # Cap at 50 points
        
        # Duration as tiebreaker (assuming longer = more complete)
        duration = audio_info.get("duration", 0)
        if duration:
            score += min(duration / 3600, 10)  # Cap at 10 points for 1+ hour
    
    # File size as final tiebreaker
    score += file_path.stat().st_size / (1024 * 1024 * 1024)  # Size in GB
    
    return score


def pick_best_audio(target: Path) -> Path:
    """
    Select the highest quality audio file from a path.
    
    Args:
        target: Path to audio file or directory containing audio files
        
    Returns:
        Path to the best quality audio file
        
    Raises:
        FileNotFoundError: If target doesn't exist
        ValueError: If no audio files found
    """
    audio_files = get_audio_files(target)
    
    if len(audio_files) == 1:
        log.info(f"Using audio file: {audio_files[0]}")
        return audio_files[0]
    
    log.info(f"Evaluating {len(audio_files)} audio files for quality...")
    
    scored_files = []
    for file_path in audio_files:
        try:
            # Get audio metadata for scoring
            audio_info = ffprobe_info(file_path)
            score = score_audio_file(file_path, audio_info)
            scored_files.append((score, file_path))
            
            log.debug(f"Scored {file_path.name}: {score:.2f}")
            
        except Exception as e:
            log.warning(f"Failed to analyze {file_path.name}: {e}")
            # Still include with basic scoring
            score = score_audio_file(file_path)
            scored_files.append((score, file_path))
    
    # Sort by score (highest first)
    scored_files.sort(reverse=True, key=lambda x: x[0])
    
    best_file = scored_files[0][1]
    log.info(f"Selected best audio file: {best_file.name} (score: {scored_files[0][0]:.2f})")
    
    return best_file