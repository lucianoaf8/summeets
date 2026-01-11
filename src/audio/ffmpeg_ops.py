"""FFmpeg operations for audio and video processing.

All commands use list-based subprocess calls for security (no shell injection).
"""
import subprocess
import logging
import json
from pathlib import Path
from typing import Dict, Tuple, List

from ..utils.config import SETTINGS
from ..utils.exceptions import sanitize_path

log = logging.getLogger(__name__)


def _parse_frame_rate(rate_str: str) -> float:
    """Safely parse frame rate string like '25/1' to float."""
    try:
        if '/' in rate_str:
            numerator, denominator = rate_str.split('/')
            return float(numerator) / float(denominator)
        else:
            return float(rate_str)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _run_cmd(cmd: List[str]) -> None:
    """
    Run an FFmpeg command using list-based subprocess (secure).

    Args:
        cmd: Command as list of strings (no shell interpretation)

    Raises:
        RuntimeError: If command fails
    """
    log.debug("RUN: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {proc.stderr.strip()}")


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    """
    Run a command and return the result.

    Args:
        cmd: Command as list of strings

    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    log.debug(f"RUN: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = proc.communicate()
    log.debug(f"EXIT {proc.returncode}: out={len(out or '')}, err={len(err or '')}")
    return proc.returncode, out, err


def probe(input_path: str) -> str:
    """Probe media file with ffprobe."""
    cmd = [SETTINGS.ffprobe_bin, "-hide_banner", "-i", input_path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.stdout + proc.stderr


def normalize_loudness(input_path: str, output_path: str) -> None:
    """EBU R128 loudness normalization. Filter documented in ffmpeg-filters."""
    cmd = [
        SETTINGS.ffmpeg_bin, "-hide_banner", "-loglevel", "error",
        "-i", input_path,
        "-af", "loudnorm",
        "-c:v", "copy",
        output_path
    ]
    _run_cmd(cmd)


def extract_audio_copy(input_path: str, output_path: str, stream_index: int = 0) -> None:
    """-vn, -map, -c:a copy per ffmpeg docs."""
    cmd = [
        SETTINGS.ffmpeg_bin, "-hide_banner", "-loglevel", "error",
        "-i", input_path,
        "-map", f"0:a:{stream_index}",
        "-vn",
        "-c:a", "copy",
        output_path
    ]
    _run_cmd(cmd)


def extract_audio_reencode(input_path: str, output_path: str, codec: str = "aac") -> None:
    """Re-encode audio to specified codec."""
    if codec == "aac":
        cmd = [
            SETTINGS.ffmpeg_bin, "-hide_banner", "-loglevel", "error",
            "-i", input_path,
            "-map", "0:a:0",
            "-vn",
            "-c:a", "aac", "-b:a", "160k",
            output_path
        ]
    elif codec == "mp3":
        cmd = [
            SETTINGS.ffmpeg_bin, "-hide_banner", "-loglevel", "error",
            "-i", input_path,
            "-map", "0:a:0",
            "-vn",
            "-c:a", "libmp3lame", "-q:a", "2",
            output_path
        ]
    elif codec == "wav":
        cmd = [
            SETTINGS.ffmpeg_bin, "-hide_banner", "-loglevel", "error",
            "-i", input_path,
            "-map", "0:a:0",
            "-vn",
            "-c:a", "pcm_s16le", "-ar", "48000",
            output_path
        ]
    else:
        raise ValueError("codec must be one of: aac|mp3|wav")

    _run_cmd(cmd)


def ensure_wav16k_mono(input_path: Path) -> Path:
    """Convert audio to 16kHz mono WAV for optimal transcription."""
    from ..utils.fsio import get_data_manager
    data_manager = get_data_manager()
    base_name = input_path.stem.replace("_extracted", "").replace("_volume", "").replace("_normalized", "")
    output_path = data_manager.get_audio_path(f"{base_name}_16k", "wav")

    if output_path.exists():
        log.info(f"Using existing 16kHz WAV: {output_path}")
        return output_path

    try:
        cmd = [
            SETTINGS.ffmpeg_bin, "-hide_banner", "-loglevel", "error",
            "-i", str(input_path),
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(output_path)
        ]
        _run_cmd(cmd)
        log.info(f"Converted to 16kHz mono WAV: {output_path}")
        return output_path
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        log.warning(f"FFmpeg conversion failed: {e}. Using original file.")
        return input_path


def ffprobe_info(path: Path) -> Dict:
    """
    Get audio file information using ffprobe.

    Args:
        path: Path to audio file

    Returns:
        Dictionary with audio metadata
    """
    cmd = [
        SETTINGS.ffprobe_bin,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path)
    ]

    returncode, stdout, stderr = run_cmd(cmd)

    if returncode != 0:
        log.warning(f"ffprobe failed for {sanitize_path(path)}: {stderr}")
        return {}

    try:
        data = json.loads(stdout)

        # Extract audio stream info
        audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
        if not audio_streams:
            return {}

        stream = audio_streams[0]  # Use first audio stream
        format_info = data.get("format", {})

        return {
            "duration": float(format_info.get("duration", 0)),
            "bit_rate": int(format_info.get("bit_rate", 0)),
            "sample_rate": int(stream.get("sample_rate", 0)),
            "channels": int(stream.get("channels", 0)),
            "codec": stream.get("codec_name", ""),
            "size": int(format_info.get("size", 0))
        }

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        log.warning(f"Failed to parse ffprobe output for {sanitize_path(path)}: {e}")
        return {}


def probe_video_info(path: Path) -> Dict:
    """
    Get video file information using ffprobe.

    Args:
        path: Path to video file

    Returns:
        Dictionary with video and audio metadata
    """
    cmd = [
        SETTINGS.ffprobe_bin,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path)
    ]

    returncode, stdout, stderr = run_cmd(cmd)

    if returncode != 0:
        log.warning(f"ffprobe failed for {sanitize_path(path)}: {stderr}")
        return {}

    try:
        data = json.loads(stdout)

        # Extract stream info
        video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
        audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
        format_info = data.get("format", {})

        result = {
            "duration": float(format_info.get("duration", 0)),
            "bit_rate": int(format_info.get("bit_rate", 0)),
            "size": int(format_info.get("size", 0)),
            "format_name": format_info.get("format_name", ""),
            "video_streams": len(video_streams),
            "audio_streams": len(audio_streams)
        }

        # Add video stream info if available
        if video_streams:
            video = video_streams[0]
            result.update({
                "video_codec": video.get("codec_name", ""),
                "width": int(video.get("width", 0)),
                "height": int(video.get("height", 0)),
                "fps": _parse_frame_rate(video.get("r_frame_rate", "0/1"))
            })

        # Add audio stream info if available
        if audio_streams:
            audio = audio_streams[0]
            result.update({
                "audio_codec": audio.get("codec_name", ""),
                "sample_rate": int(audio.get("sample_rate", 0)),
                "channels": int(audio.get("channels", 0))
            })

        return result

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        log.warning(f"Failed to parse ffprobe output for {sanitize_path(path)}: {e}")
        return {}


def extract_audio_from_video(
    video_path: Path,
    output_path: Path,
    format: str = "m4a",
    quality: str = "high",
    normalize: bool = True
) -> Path:
    """
    Extract audio from video file with specified format and quality.

    Args:
        video_path: Path to input video file
        output_path: Path for output audio file
        format: Output audio format (m4a, mp3, wav, flac)
        quality: Audio quality (high, medium, low)
        normalize: Whether to normalize audio loudness

    Returns:
        Path to extracted audio file

    Raises:
        RuntimeError: If extraction fails
        ValueError: If format is unsupported
    """
    # Validate format
    supported_formats = {"m4a", "mp3", "wav", "flac"}
    if format not in supported_formats:
        raise ValueError(f"Unsupported format: {format}. Supported: {supported_formats}")

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build FFmpeg command as list (secure)
    cmd: List[str] = [
        SETTINGS.ffmpeg_bin,
        "-hide_banner", "-loglevel", "error",
        "-i", str(video_path),
        "-vn"  # No video
    ]

    # Configure audio codec and quality based on format
    if format == "m4a":
        if quality == "high":
            cmd.extend(["-c:a", "aac", "-b:a", SETTINGS.audio_quality_high_bitrate])
        elif quality == "medium":
            cmd.extend(["-c:a", "aac", "-b:a", SETTINGS.audio_quality_medium_bitrate])
        else:  # low
            cmd.extend(["-c:a", "aac", "-b:a", SETTINGS.audio_quality_low_bitrate])

    elif format == "mp3":
        if quality == "high":
            cmd.extend(["-c:a", "libmp3lame", "-q:a", "0"])
        elif quality == "medium":
            cmd.extend(["-c:a", "libmp3lame", "-q:a", "2"])
        else:  # low
            cmd.extend(["-c:a", "libmp3lame", "-q:a", "4"])

    elif format == "wav":
        cmd.extend(["-c:a", "pcm_s16le", "-ar", "48000"])

    elif format == "flac":
        if quality == "high":
            cmd.extend(["-c:a", "flac", "-compression_level", "8"])
        elif quality == "medium":
            cmd.extend(["-c:a", "flac", "-compression_level", "5"])
        else:  # low
            cmd.extend(["-c:a", "flac", "-compression_level", "1"])

    # Add normalization filter if requested
    if normalize and format != "wav":  # Skip normalization for WAV to preserve quality
        cmd.extend(["-af", "loudnorm"])

    # Add output path
    cmd.append(str(output_path))

    # Execute command
    try:
        _run_cmd(cmd)
        log.info(f"Extracted audio: {sanitize_path(video_path)} -> {sanitize_path(output_path)}")
        return output_path
    except RuntimeError as e:
        log.error(f"Failed to extract audio from {sanitize_path(video_path)}: {e}")
        raise


def increase_audio_volume(input_path: Path, output_path: Path, gain_db: float = 10.0) -> Path:
    """
    Increase audio volume by specified gain.

    Args:
        input_path: Input audio file
        output_path: Output audio file
        gain_db: Gain in decibels (positive to increase, negative to decrease)

    Returns:
        Path to processed audio file
    """
    cmd = [
        SETTINGS.ffmpeg_bin, "-hide_banner", "-loglevel", "error",
        "-i", str(input_path),
        "-af", f"volume={gain_db}dB",
        str(output_path)
    ]

    try:
        _run_cmd(cmd)
        log.info(f"Adjusted volume by {gain_db}dB: {sanitize_path(input_path)} -> {sanitize_path(output_path)}")
        return output_path
    except RuntimeError as e:
        log.error(f"Failed to adjust volume for {sanitize_path(input_path)}: {e}")
        raise


def convert_audio_format(
    input_path: Path,
    output_path: Path,
    format: str,
    quality: str = "medium"
) -> Path:
    """
    Convert audio to different format.

    Args:
        input_path: Input audio file
        output_path: Output audio file
        format: Target format (m4a, mp3, ogg, flac)
        quality: Quality setting (high, medium, low)

    Returns:
        Path to converted audio file
    """
    # Build command as list (secure)
    cmd: List[str] = [
        SETTINGS.ffmpeg_bin,
        "-hide_banner", "-loglevel", "error",
        "-i", str(input_path)
    ]

    if format == "m4a":
        if quality == "high":
            cmd.extend(["-c:a", "aac", "-b:a", SETTINGS.audio_quality_high_bitrate])
        elif quality == "medium":
            cmd.extend(["-c:a", "aac", "-b:a", SETTINGS.audio_quality_medium_bitrate])
        else:
            cmd.extend(["-c:a", "aac", "-b:a", SETTINGS.audio_quality_low_bitrate])

    elif format == "mp3":
        if quality == "high":
            cmd.extend(["-c:a", "libmp3lame", "-q:a", "0"])
        elif quality == "medium":
            cmd.extend(["-c:a", "libmp3lame", "-q:a", "2"])
        else:
            cmd.extend(["-c:a", "libmp3lame", "-q:a", "4"])

    elif format == "ogg":
        if quality == "high":
            cmd.extend(["-c:a", "libvorbis", "-q:a", "6"])
        elif quality == "medium":
            cmd.extend(["-c:a", "libvorbis", "-q:a", "4"])
        else:
            cmd.extend(["-c:a", "libvorbis", "-q:a", "2"])

    elif format == "flac":
        if quality == "high":
            cmd.extend(["-c:a", "flac", "-compression_level", "8"])
        elif quality == "medium":
            cmd.extend(["-c:a", "flac", "-compression_level", "5"])
        else:
            cmd.extend(["-c:a", "flac", "-compression_level", "1"])

    else:
        raise ValueError(f"Unsupported format: {format}")

    cmd.append(str(output_path))

    try:
        _run_cmd(cmd)
        log.info(f"Converted audio format: {sanitize_path(input_path)} -> {sanitize_path(output_path)}")
        return output_path
    except RuntimeError as e:
        log.error(f"Failed to convert {sanitize_path(input_path)} to {format}: {e}")
        raise
