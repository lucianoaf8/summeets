"""
Audio compression utilities for upload optimization.
Handles compressing audio files to fit within size limits.
"""
import logging
import tempfile
from pathlib import Path
from typing import Optional

from ..config import SETTINGS
from .ffmpeg_ops import run_cmd

log = logging.getLogger(__name__)

# Default compression settings
DEFAULT_MAX_MB = 24.0
BITRATE_OPTIONS = [96, 64, 48, 32, 24, 16]  # kbps options to try


class CompressionError(Exception):
    """Raised when audio compression fails."""
    pass


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in megabytes."""
    return file_path.stat().st_size / (1024 * 1024)


def compress_audio_for_upload(
    input_path: Path, 
    max_mb: float = DEFAULT_MAX_MB,
    bitrate_options: Optional[list] = None
) -> Path:
    """
    Compress audio file to fit within upload size limit.
    
    Args:
        input_path: Path to input audio file
        max_mb: Maximum file size in megabytes
        bitrate_options: List of bitrates to try (kbps)
        
    Returns:
        Path to compressed file (may be same as input if no compression needed)
        
    Raises:
        CompressionError: If compression fails or file cannot be compressed enough
        FileNotFoundError: If input file doesn't exist
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    current_size_mb = get_file_size_mb(input_path)
    
    if current_size_mb <= max_mb:
        log.info(f"File size ({current_size_mb:.1f}MB) is within limit ({max_mb}MB)")
        return input_path
    
    log.info(f"Compressing {current_size_mb:.1f}MB file to fit under {max_mb}MB limit...")
    
    bitrates = bitrate_options or BITRATE_OPTIONS
    
    for bitrate_k in bitrates:
        try:
            compressed_path = _compress_with_bitrate(input_path, bitrate_k)
            compressed_size_mb = get_file_size_mb(compressed_path)
            
            if compressed_size_mb <= max_mb:
                log.info(f"Successfully compressed to {compressed_size_mb:.1f}MB at {bitrate_k}k")
                return compressed_path
            else:
                log.debug(f"Compression at {bitrate_k}k -> {compressed_size_mb:.1f}MB (still too large)")
                # Clean up failed attempt
                if compressed_path.exists():
                    compressed_path.unlink()
                    
        except Exception as e:
            log.warning(f"Compression failed at {bitrate_k}k: {e}")
            continue
    
    raise CompressionError(f"Could not compress audio under {max_mb}MB limit")


def _compress_with_bitrate(input_path: Path, bitrate_k: int) -> Path:
    """
    Compress audio file with specified bitrate.
    
    Args:
        input_path: Input audio file
        bitrate_k: Target bitrate in kbps
        
    Returns:
        Path to compressed file
        
    Raises:
        CompressionError: If compression command fails
    """
    # Create temporary output file
    with tempfile.NamedTemporaryFile(suffix=".opus", delete=False) as tmp:
        output_path = Path(tmp.name)
    
    # Build ffmpeg command
    cmd = [
        SETTINGS.ffmpeg_bin, 
        "-hide_banner", 
        "-loglevel", "error",
        "-i", str(input_path),
        "-c:a", "libopus",
        "-b:a", f"{bitrate_k}k",
        "-vn",  # No video
        str(output_path)
    ]
    
    # Run compression
    returncode, stdout, stderr = run_cmd(cmd)
    
    if returncode != 0:
        # Clean up failed output
        if output_path.exists():
            output_path.unlink()
        raise CompressionError(f"FFmpeg compression failed: {stderr}")
    
    return output_path


def cleanup_temp_file(file_path: Path, original_path: Path) -> None:
    """
    Safely clean up temporary compressed file.
    
    Args:
        file_path: Path to file to clean up
        original_path: Original file path (won't be deleted)
    """
    try:
        if file_path != original_path and file_path.exists():
            file_path.unlink()
            log.debug(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        log.warning(f"Failed to clean up temporary file {file_path}: {e}")