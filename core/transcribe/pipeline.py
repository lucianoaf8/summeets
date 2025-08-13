"""Transcription pipeline migrated from meeting_transcribe.py"""
import os
import sys
import json
import time
import tempfile
import subprocess
import re
import logging
import datetime
import math
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict

from tenacity import retry, stop_after_attempt, wait_fixed
from alive_progress import alive_bar, config_handler

from ..config import SETTINGS
from ..audio.ffmpeg_ops import ensure_wav16k_mono

# Console encoding guard for Windows
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

log = logging.getLogger(__name__)

# Configuration
SUPPORTED_EXTS = {".m4a",".mka",".ogg",".mp3",".wav",".webm",".flac"}
MAX_UPLOAD_MB = float(os.getenv("MAX_UPLOAD_MB", "24"))
BITRATE_TRY_K = [96, 64, 48, 32, 24, 16]

REPLICATE_MODEL = os.getenv("REPLICATE_MODEL", "thomasmol/whisper-diarization")
REPLICATE_MODEL_VERSION = os.getenv("REPLICATE_MODEL_VERSION", "").strip()

# Transcript paragraphization defaults
TRANSCRIPT_JOIN_SEC = 90.0
TRANSCRIPT_GAP_MERGE = 1.0
TRANSCRIPT_MIN_SEC = 1.0
TRANSCRIPT_MIN_CHARS = 30
TRANSCRIPT_MAX_CHARS = 900
WRAP_WIDTH = 72
WRAP_MAX_LINES = 3
PRE_SPLIT_MAX_SEC = 0.0

# Progress bar config (ASCII-safe)
config_handler.set_global(spinner="classic", bar="filling", length=32, force_tty=None)

@dataclass
class Word:
    start: float
    end: float
    text: str

@dataclass
class Segment:
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    words: Optional[List[Word]] = None

def run_cmd(cmd: list) -> Tuple[int, str, str]:
    log.debug(f"RUN: {' '.join(cmd)}")
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    log.debug(f"EXIT {p.returncode}: out={len(out or '')}, err={len(err or '')}")
    return p.returncode, out, err

def pick_best_audio(dirpath: Path) -> Optional[Path]:
    """Select highest quality audio from directory."""
    audio_files = [f for f in dirpath.iterdir() if f.suffix.lower() in SUPPORTED_EXTS]
    if not audio_files:
        return None
    
    scored = []
    for f in audio_files:
        score = 0
        # Prefer normalized files
        if "norm" in f.stem.lower():
            score += 1000
        # Format preferences
        ext_scores = {".m4a": 100, ".flac": 90, ".wav": 80, ".mka": 70, ".ogg": 60, ".mp3": 50, ".webm": 40}
        score += ext_scores.get(f.suffix.lower(), 0)
        # File size as tiebreaker
        score += f.stat().st_size / 1e9
        scored.append((score, f))
    
    scored.sort(reverse=True)
    return scored[0][1]

def compress_audio_for_upload(input_path: Path, max_mb: float = MAX_UPLOAD_MB) -> Path:
    """Compress audio to fit upload size limit."""
    size_mb = input_path.stat().st_size / 1024 / 1024
    if size_mb <= max_mb:
        return input_path
    
    log.info(f"Compressing {size_mb:.1f}MB to fit under {max_mb}MB upload limit...")
    
    # Try different bitrates
    for bitrate_k in BITRATE_TRY_K:
        with tempfile.NamedTemporaryFile(suffix=".opus", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        cmd = [
            SETTINGS.ffmpeg_bin, "-hide_banner", "-loglevel", "error",
            "-i", str(input_path),
            "-c:a", "libopus", "-b:a", f"{bitrate_k}k",
            "-vn", str(tmp_path)
        ]
        
        code, _, err = run_cmd(cmd)
        if code != 0:
            log.warning(f"Compression at {bitrate_k}k failed: {err}")
            if tmp_path.exists():
                tmp_path.unlink()
            continue
        
        new_size_mb = tmp_path.stat().st_size / 1024 / 1024
        if new_size_mb <= max_mb:
            log.info(f"Compressed to {new_size_mb:.1f}MB at {bitrate_k}k")
            return tmp_path
        else:
            log.debug(f"{bitrate_k}k -> {new_size_mb:.1f}MB (too large)")
            tmp_path.unlink()
    
    raise RuntimeError(f"Could not compress audio under {max_mb}MB")

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def replicate_predict(audio_path: Path) -> Dict:
    """Run Replicate prediction with retry logic."""
    try:
        import replicate
    except ImportError:
        raise ImportError("Please install replicate: pip install replicate")
    
    # Determine model version
    if REPLICATE_MODEL_VERSION:
        model_ref = f"{REPLICATE_MODEL}:{REPLICATE_MODEL_VERSION}"
    else:
        model = replicate.models.get(REPLICATE_MODEL)
        latest = model.latest_version
        model_ref = f"{REPLICATE_MODEL}:{latest.id}"
        log.info(f"Using latest version: {latest.id}")
    
    # Create prediction
    prediction = replicate.predictions.create(
        version=model_ref,
        input={"file": open(audio_path, "rb")}
    )
    
    log.info(f"Prediction ID: {prediction.id}")
    
    # Poll for completion with progress bar
    with alive_bar(title="Transcribing", unknown="classic", spinner="classic") as bar:
        while prediction.status not in ["succeeded", "failed", "canceled"]:
            time.sleep(2)
            prediction.reload()
            bar()
    
    if prediction.status != "succeeded":
        raise RuntimeError(f"Prediction {prediction.status}: {prediction.error}")
    
    return prediction.output

def transcribe_audio(audio_path: Path) -> List[Segment]:
    """Main transcription function."""
    # Ensure proper format
    audio_path = ensure_wav16k_mono(audio_path)
    
    # Compress if needed
    compressed_path = compress_audio_for_upload(audio_path)
    
    try:
        # Run transcription
        output = replicate_predict(compressed_path)
        
        # Parse segments
        segments = []
        for seg_data in output.get("segments", []):
            words = []
            for w in seg_data.get("words", []):
                words.append(Word(
                    start=w["start"],
                    end=w["end"],
                    text=w["word"]
                ))
            
            segments.append(Segment(
                start=seg_data["start"],
                end=seg_data["end"],
                text=seg_data["text"],
                speaker=seg_data.get("speaker"),
                words=words
            ))
        
        return segments
    finally:
        # Cleanup compressed file if different
        if compressed_path != audio_path and compressed_path.exists():
            compressed_path.unlink()

def run(audio_path: Path = None, output_dir: Path = None) -> Path:
    """Run the complete transcription pipeline."""
    if not audio_path:
        # Prompt for path
        user_input = input("\nEnter audio file or folder path: ").strip().strip('"')
        audio_path = Path(user_input).resolve()
    
    if audio_path.is_dir():
        audio_path = pick_best_audio(audio_path)
        if not audio_path:
            raise ValueError(f"No audio files found in {audio_path}")
    
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    output_dir = output_dir or SETTINGS.out_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    log.info(f"Transcribing: {audio_path}")
    
    # Run transcription
    segments = transcribe_audio(audio_path)
    
    # Save output
    base_name = audio_path.stem
    json_path = output_dir / f"{base_name}.json"
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([{
            "start": s.start,
            "end": s.end,
            "text": s.text,
            "speaker": s.speaker,
            "words": [{"start": w.start, "end": w.end, "text": w.text} for w in (s.words or [])]
        } for s in segments], f, indent=2, ensure_ascii=False)
    
    log.info(f"Saved transcript: {json_path}")
    return json_path