import subprocess
import shlex
import logging
from pathlib import Path
from ..config import SETTINGS

log = logging.getLogger(__name__)

def _run(cmd: str) -> None:
    log.debug("RUN: %s", cmd)
    proc = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {proc.stderr.strip()}")

def probe(input_path: str) -> str:
    cmd = f'{shlex.quote(SETTINGS.ffprobe_bin)} -hide_banner -i {shlex.quote(input_path)}'
    proc = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
    return proc.stdout + proc.stderr

def normalize_loudness(input_path: str, output_path: str) -> None:
    """EBU R128 loudness normalization. Filter documented in ffmpeg-filters."""
    cmd = (
        f'{shlex.quote(SETTINGS.ffmpeg_bin)} -hide_banner -loglevel error '
        f'-i {shlex.quote(input_path)} -af loudnorm -c:v copy {shlex.quote(output_path)}'
    )
    _run(cmd)

def extract_audio_copy(input_path: str, output_path: str, stream_index: int = 0) -> None:
    """-vn, -map, -c:a copy per ffmpeg docs."""
    cmd = (
        f'{shlex.quote(SETTINGS.ffmpeg_bin)} -hide_banner -loglevel error '
        f'-i {shlex.quote(input_path)} -map 0:a:{stream_index} -vn -c:a copy {shlex.quote(output_path)}'
    )
    _run(cmd)

def extract_audio_reencode(input_path: str, output_path: str, codec: str = "aac") -> None:
    if codec == "aac":
        # CBR AAC example (-b:a)
        cmd = (
            f'{shlex.quote(SETTINGS.ffmpeg_bin)} -hide_banner -loglevel error '
            f'-i {shlex.quote(input_path)} -map 0:a:0 -vn -c:a aac -b:a 160k {shlex.quote(output_path)}'
        )
    elif codec == "mp3":
        # libmp3lame VBR quality via -q (wrapper around LAME -V)
        cmd = (
            f'{shlex.quote(SETTINGS.ffmpeg_bin)} -hide_banner -loglevel error '
            f'-i {shlex.quote(input_path)} -map 0:a:0 -vn -c:a libmp3lame -q:a 2 {shlex.quote(output_path)}'
        )
    elif codec == "wav":
        cmd = (
            f'{shlex.quote(SETTINGS.ffmpeg_bin)} -hide_banner -loglevel error '
            f'-i {shlex.quote(input_path)} -map 0:a:0 -vn -c:a pcm_s16le -ar 48000 {shlex.quote(output_path)}'
        )
    else:
        raise ValueError("codec must be one of: aac|mp3|wav")
    _run(cmd)

def ensure_wav16k_mono(input_path: Path) -> Path:
    """Convert audio to 16kHz mono WAV for optimal transcription."""
    output_path = input_path.parent / f"{input_path.stem}_16k.wav"
    if output_path.exists():
        log.info(f"Using existing 16kHz WAV: {output_path}")
        return output_path
    
    try:
        cmd = (
            f'{shlex.quote(SETTINGS.ffmpeg_bin)} -hide_banner -loglevel error '
            f'-i {shlex.quote(str(input_path))} -ar 16000 -ac 1 -c:a pcm_s16le '
            f'{shlex.quote(str(output_path))}'
        )
        _run(cmd)
        log.info(f"Converted to 16kHz mono WAV: {output_path}")
        return output_path
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        log.warning(f"FFmpeg conversion failed: {e}. Using original file.")
        return input_path