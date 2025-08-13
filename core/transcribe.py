#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Transcription module for Summeets
Handles audio transcription using Replicate's Whisper + diarization model
"""

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
from typing import List, Optional, Tuple, Dict, Any

# Console encoding guard for Windows
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed
from alive_progress import alive_bar, config_handler

# ------------------ Config ------------------
SUPPORTED_EXTS = {".m4a",".mka",".ogg",".mp3",".wav",".webm",".flac"}
MAX_UPLOAD_MB = float(os.getenv("MAX_UPLOAD_MB", "24"))
BITRATE_TRY_K = [96, 64, 48, 32, 24, 16]

REPLICATE_MODEL = os.getenv("REPLICATE_MODEL", "thomasmol/whisper-diarization")
REPLICATE_MODEL_VERSION = os.getenv("REPLICATE_MODEL_VERSION", "").strip()

# Transcript paragraphization defaults
TRANSCRIPT_JOIN_SEC = 90.0   # allow long single-speaker paragraphs
TRANSCRIPT_GAP_MERGE = 1.0   # seconds of silence still considered continuous
TRANSCRIPT_MIN_SEC = 1.0     # merge tiny cues
TRANSCRIPT_MIN_CHARS = 30
TRANSCRIPT_MAX_CHARS = 900
WRAP_WIDTH = 72              # wrap width for transcript output
WRAP_MAX_LINES = 3
PRE_SPLIT_MAX_SEC = 0.0      # 0 disables pre-splitting; we paragraphize instead

# Progress bar config (ASCII-safe)
config_handler.set_global(spinner="classic", bar="filling", length=32, force_tty=None)

# ------------------ Data ------------------
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

# ------------------ Logging ------------------
def setup_logger(name: str = "transcribe") -> logging.Logger:
    logdir = Path("logs")
    logdir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    logfile = logdir / f"{name}_{ts}.log"
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))

    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.debug("Logger initialized.")
    logger.info(f"[log] {logfile}")
    return logger

# ------------------ Shell utils ------------------
def run(cmd: list, log: logging.Logger) -> Tuple[int, str, str]:
    log.debug(f"RUN: {' '.join(cmd)}")
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    log.debug(f"RC={p.returncode}\nSTDOUT={out[:1000]}\nSTDERR={err[:2000]}")
    return p.returncode, out, err

def has_exec(name: str) -> bool:
    try:
        p = subprocess.Popen(
            ["where" if os.name == "nt" else "which", name],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        p.communicate()
        return p.returncode == 0
    except Exception:
        return False

def bytes_mb(n: int) -> float:
    return round(n / (1024*1024), 2)

# ------------------ Audio selection/compression ------------------
def ffprobe_info(path: Path, log: logging.Logger) -> Dict:
    if not has_exec("ffprobe"):
        log.warning("ffprobe not found; skipping probe.")
        return {}
    code, out, _ = run([
        "ffprobe","-v","error","-select_streams","a:0",
        "-show_entries","stream=bit_rate,sample_rate,channels",
        "-of","json", str(path)
    ], log)
    if code != 0: return {}
    try: return json.loads(out)
    except Exception: return {}

def pick_best_audio(target: Path, log: logging.Logger) -> Path:
    if target.is_file():
        if target.suffix.lower() in SUPPORTED_EXTS:
            log.info(f"[select] Using file: {target}")
            return target
        raise ValueError(f"Unsupported file type: {target.suffix}")

    cands = [p for p in target.iterdir() if p.suffix.lower() in SUPPORTED_EXTS]
    if not cands:
        raise FileNotFoundError(f"No audio found under {target} with {sorted(SUPPORTED_EXTS)}")

    norm = [p for p in cands if re.search(r"(norm|normalized)", p.name, re.I)]
    if norm: cands = norm

    rank = {".m4a":6, ".flac":5, ".wav":4, ".mka":3, ".ogg":2, ".mp3":1}
    scored = []
    for p in cands:
        info = ffprobe_info(p, log)
        br = int(info.get("streams",[{}])[0].get("bit_rate") or 0)
        sr = int(info.get("streams",[{}])[0].get("sample_rate") or 0)
        size = p.stat().st_size
        scored.append((br, sr, rank.get(p.suffix.lower(),0), size, p))
        log.debug(f"[candidate] {p.name} br={br} sr={sr} size={bytes_mb(size)}MB rank={rank.get(p.suffix.lower(),0)}")
    scored.sort(reverse=True)
    best = scored[0][4]
    log.info(f"[select] Best candidate: {best} ({bytes_mb(best.stat().st_size)} MB)")
    return best

def compress_to_under_limit(src: Path, max_mb: float, log: logging.Logger) -> Path:
    """Transcode to Opus mono 16k, decreasing bitrate until size <= cap."""
    if not has_exec("ffmpeg"):
        size_mb = bytes_mb(src.stat().st_size)
        if size_mb > max_mb:
            raise RuntimeError(f"ffmpeg required: {src.name} is {size_mb} MB > {max_mb} MB and cannot be compressed.")
        log.info(f"[compress] ffmpeg missing but file is {size_mb} MB <= {max_mb} MB, using as-is.")
        return src

    tmp_dir = Path(tempfile.gettempdir())
    dst = tmp_dir / f"{src.stem}_opus.ogg"

    for kbps in BITRATE_TRY_K:
        if dst.exists():
            try: dst.unlink()
            except Exception: pass
        cmd = [
            "ffmpeg","-y","-i",str(src),
            "-ac","1","-ar","16000",
            "-c:a","libopus","-b:a", f"{kbps}k",
            str(dst)
        ]
        rc, _, _ = run(cmd, log)
        if rc != 0:
            log.warning(f"[compress] ffmpeg returned {rc} at {kbps}kbps, trying next.")
            continue
        size_mb = bytes_mb(dst.stat().st_size)
        log.info(f"[compress] {kbps}kbps -> {size_mb} MB")
        if size_mb <= max_mb:
            log.info(f"[compress] Success under cap {max_mb} MB with {kbps} kbps.")
            return dst

    sizes = [(p, p.stat().st_size) for p in [dst] if p.exists()]
    if sizes and sizes[0][1] < src.stat().st_size:
        log.warning(f"[compress] Could not reach {max_mb} MB. Using smallest attempt {bytes_mb(sizes[0][1])} MB; upload may fail.")
        return dst
    log.warning("[compress] Compression attempts failed; using original.")
    return src

# ------------------ Replicate ------------------
def _resolve_model_version(client, slug: str, log: logging.Logger) -> str:
    model = client.models.get(slug)
    versions = list(model.versions.list())
    if not versions:
        raise RuntimeError(f"No versions available for {slug}")
    ver = versions[0].id
    log.info(f"[replicate] Using version {ver} for {slug}")
    return ver

@retry(stop=stop_after_attempt(3), wait=wait_fixed(3))
def replicate_predict(audio_path: Path, log: logging.Logger) -> Dict:
    """Create prediction with version-pinned call. No nested progress bars."""
    import replicate
    client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

    size_mb = bytes_mb(audio_path.stat().st_size)
    log.info(f"[upload] File to upload: {audio_path.name} ({size_mb} MB)")

    version_id = REPLICATE_MODEL_VERSION or _resolve_model_version(client, REPLICATE_MODEL, log)
    with open(audio_path, "rb") as fh:
        pred = client.predictions.create(version=version_id, input={"file": fh})
    status = getattr(pred, "status", "starting")
    while status not in ("succeeded","failed","canceled"):
        time.sleep(2)
        pred = client.predictions.get(pred.id)
        status = getattr(pred, "status", status)
        log.info(f"[replicate] status={status}")
    if pred.status != "succeeded":
        raise RuntimeError(f"Replicate prediction failed: {pred.status}")
    return pred.output

# ------------------ JSON -> segments ------------------
def to_segments(pred_output: Dict) -> List[Segment]:
    segs = []
    for s in pred_output.get("segments", []):
        words = [Word(start=w.get("start",0.0), end=w.get("end",0.0), text=w.get("word","")) for w in (s.get("words") or [])]
        segs.append(Segment(
            start=float(s.get("start",0.0)),
            end=float(s.get("end",0.0)),
            text=(s.get("text") or "").strip(),
            speaker=s.get("speaker"),
            words=words if words else None
        ))
    return segs

def write_json(segments: List[Segment], path: Path, meta: Dict):
    payload = {
        "segments":[
            {
                "start": round(s.start,3),
                "end": round(s.end,3),
                "speaker": s.speaker,
                "text": s.text,
                "words": ([{"start":round(w.start,3),"end":round(w.end,3),"word":w.text} for w in s.words] if s.words else None)
            } for s in segments
        ],
        "meta": meta
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

# ------------------ Paragraphizing SRT builder ------------------
PUNCT_BREAK = re.compile(r'[.!?]\s+$')
DUP_WORDS   = re.compile(r'\b(\w+)(\s+\1){1,}\b', re.IGNORECASE)

def fmt_ts(s: float) -> str:
    if s < 0: s = 0
    h = int(s//3600); m = int((s%3600)//60); sec = int(s%60); ms = int(round((s - int(s))*1000))
    return f"{h:02}:{m:02}:{sec:02},{ms:03}"

def sentence_case(text: str) -> str:
    t = text.strip()
    if not t: return t
    chars = list(t); i = 0
    while i < len(chars) and not chars[i].isalpha(): i += 1
    if i < len(chars): chars[i] = chars[i].upper()
    return ''.join(chars)

def fix_spacing(t: str) -> str:
    t = re.sub(r'\s+([,.;:!?])', r'\1', t)
    t = re.sub(r'\(\s+', '(', t); t = re.sub(r'\s+\)', ')', t)
    t = re.sub(r'\s*/\s*', '/', t)
    t = re.sub(r'(\d)\s*-\s*([A-Za-z0-9])', r'\1-\2', t)  # 12 -Month -> 12-month
    t = re.sub(r'\bU\s*\.\s*S\s*\.', 'U.S.', t)
    t = re.sub(r'\bE\s*\.\s*U\s*\.', 'E.U.', t)
    return t

def wrap_text(text: str, width: int = 72, max_lines: int = 3) -> str:
    if width <= 0: return text
    words = text.split()
    lines, cur = [], ""
    i = 0
    while i < len(words):
        w = words[i]
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur += " " + w
        else:
            lines.append(cur); cur = w
        i += 1
    if cur: lines.append(cur)
    return "\n".join(lines[:max_lines])

def stable_speaker_map(labels: List[Optional[str]]) -> Dict[str, str]:
    mapping, n = {}, 1
    for lab in labels:
        key = lab or "UNKNOWN"
        if key not in mapping:
            mapping[key] = f"Speaker {n}"; n += 1
    return mapping

def split_segment_words(seg: Dict, max_sec: float) -> List[Dict]:
    words = seg.get("words") or []
    if not words or max_sec <= 0:
        return [seg]
    out, cur_words = [], []
    cur_start, last_end = None, None

    def flush():
        nonlocal cur_words, cur_start, last_end, out
        if cur_words:
            text = " ".join(w.get("word","") for w in cur_words).strip()
            if text:
                out.append({
                    "start": cur_start,
                    "end": last_end,
                    "speaker": seg.get("speaker"),
                    "text": text,
                    "words": cur_words
                })
            cur_words = []

    for w in words:
        wst = float(w.get("start", seg["start"]))
        wed = float(w.get("end",   seg["end"]))
        if cur_start is None:
            cur_start = wst
        cur_words.append({"start": wst, "end": wed, "word": w.get("word","")})
        last_end = wed
        duration = last_end - cur_start
        if duration >= max_sec:
            chunk_text = " ".join(x["word"] for x in cur_words)
            if PUNCT_BREAK.search(chunk_text) or duration >= max_sec + 1.0:
                flush(); cur_start = None
    flush()
    return out or [seg]

def proportional_split(seg: Dict, max_sec: float) -> List[Dict]:
    if max_sec <= 0: return [seg]
    dur = float(seg["end"]) - float(seg["start"])
    if dur <= max_sec: return [seg]
    text = seg.get("text","").strip()
    if not text: return [seg]
    approx_chunks = max(1, int(math.ceil(dur / max_sec)))
    parts, tokens = [], text.split()
    per = max(1, len(tokens)//approx_chunks)
    i = 0
    for k in range(approx_chunks):
        chunk_tokens = tokens[i:i+per] if k < approx_chunks-1 else tokens[i:]
        t_text = " ".join(chunk_tokens).strip()
        if not t_text: continue
        s = float(seg["start"]) + k * (dur/approx_chunks)
        e = float(seg["start"]) + (k+1) * (dur/approx_chunks)
        parts.append({"start": s, "end": e, "speaker": seg.get("speaker"), "text": t_text, "words": None})
        i += per
    return parts or [seg]

def merge_short(chunks: List[Dict], min_sec: float, min_chars: int, max_gap: float = 0.5) -> List[Dict]:
    if not chunks: return chunks
    out = [chunks[0]]
    for c in chunks[1:]:
        last = out[-1]
        dur = float(last["end"]) - float(last["start"])
        gap = float(c["start"]) - float(last["end"])
        last_chars = len(last.get("text",""))
        if ((dur < min_sec) or (last_chars < min_chars)) and (last.get("speaker")==c.get("speaker") or gap <= max_gap):
            last["end"] = float(c["end"])
            last["text"] = (last.get("text","") + " " + c.get("text","")).strip()
            last["words"] = None
        else:
            out.append(c)
    return out

def join_same_speaker(chunks: List[Dict], join_sec: float, gap_merge: float, max_chars: int) -> List[Dict]:
    if not chunks: return chunks
    out = [chunks[0]]
    for c in chunks[1:]:
        last = out[-1]
        same = (last.get("speaker") == c.get("speaker"))
        gap  = float(c["start"]) - float(last["end"])
        if same and gap <= gap_merge:
            combined_sec   = float(c["end"]) - float(last["start"])
            combined_chars = len(last.get("text","")) + 1 + len(c.get("text",""))
            if combined_sec <= join_sec and combined_chars <= max_chars:
                last["end"]  = float(c["end"])
                last["text"] = (last["text"] + " " + c.get("text","")).strip()
                last["words"]= None
                continue
        out.append(c)
    return out

def remap_speakers(chunks: List[Dict]) -> List[Dict]:
    mapping = stable_speaker_map([c.get("speaker") for c in chunks])
    for c in chunks:
        c["speaker"] = mapping[c.get("speaker") or "UNKNOWN"]
    return chunks

def build_final_srt_from_json(json_path: Path, out_srt_path: Path):
    data = json.loads(json_path.read_text(encoding="utf-8"))
    segs = data.get("segments", [])

    # 1) initial chunks with optional pre-splitting (disabled by default)
    chunks: List[Dict] = []
    for s in segs:
        s = {
            "start": float(s.get("start",0.0)),
            "end": float(s.get("end",0.0)),
            "speaker": s.get("speaker") or "UNKNOWN",
            "text": (s.get("text") or "").strip(),
            "words": s.get("words")
        }
        dur = s["end"] - s["start"]
        if PRE_SPLIT_MAX_SEC and dur > PRE_SPLIT_MAX_SEC:
            parts = split_segment_words(s, PRE_SPLIT_MAX_SEC)
            if len(parts) == 1 and parts[0].get("words") is None and dur > PRE_SPLIT_MAX_SEC:
                parts = proportional_split(s, PRE_SPLIT_MAX_SEC)
            chunks.extend(parts)
        else:
            chunks.append(s)

    chunks.sort(key=lambda c: (c["start"], c["end"]))
    # 2) merge ultra-short
    chunks = merge_short(chunks, min_sec=TRANSCRIPT_MIN_SEC, min_chars=TRANSCRIPT_MIN_CHARS, max_gap=0.5)
    # 3) paragraphize same-speaker
    chunks = join_same_speaker(chunks, join_sec=TRANSCRIPT_JOIN_SEC, gap_merge=TRANSCRIPT_GAP_MERGE, max_chars=TRANSCRIPT_MAX_CHARS)
    # 4) remap speakers
    chunks = remap_speakers(chunks)
    # 5) de-overlap rounding issues and enforce minimum span
    for i in range(1, len(chunks)):
        prev = chunks[i-1]; cur = chunks[i]
        if cur["start"] < prev["end"]:
            cur["start"] = prev["end"] + 0.02
        if cur["end"] <= cur["start"]:
            cur["end"] = cur["start"] + 0.50

    # 6) write final SRT
    with out_srt_path.open("w", encoding="utf-8") as f:
        for i, c in enumerate(chunks, 1):
            # normalize text last to preserve joins
            t = c.get("text","").strip()
            t = DUP_WORDS.sub(r"\1", t)
            t = fix_spacing(t)
            t = sentence_case(t)
            if WRAP_WIDTH > 0:
                t = wrap_text(t, width=WRAP_WIDTH, max_lines=WRAP_MAX_LINES)
            spk = c.get("speaker")
            f.write(f"{i}\n")
            f.write(f"{fmt_ts(float(c['start']))} --> {fmt_ts(float(c['end']))}\n")
            prefix = f"{spk}: " if spk else ""
            f.write(prefix + t + "\n\n")

# ------------------ SRT audit (integrated) ------------------
TIME_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")
SPK_RE  = re.compile(r"^(SPEAKER[_\s-]?\d+|Speaker\s*\d+|[A-Za-z][\w .-]{0,30})\s*:\s*", re.IGNORECASE)

def parse_time_srt(t: str) -> float:
    m = TIME_RE.fullmatch(t.strip())
    if not m: raise ValueError(f"Bad timestamp: {t}")
    hh, mm, ss, ms = map(int, m.groups())
    return hh*3600 + mm*60 + ss + ms/1000.0

def split_blocks(raw: str) -> List[str]:
    return [b.strip() for b in re.split(r"\r?\n\r?\n+", raw.strip()) if b.strip()]

def parse_block(b: str):
    lines = b.splitlines()
    # tolerate non-numeric indices
    try:
        idx = int(lines[0].strip()); i = 1
    except:
        idx = -1; i = 0
    tl = lines[i].strip()
    left, right = [x.strip() for x in tl.split("-->")]
    start = parse_time_srt(left); end = parse_time_srt(right)
    body = "\n".join(lines[i+1:]).strip()
    m = SPK_RE.match(body)
    speaker = None
    if m:
        speaker = m.group(1).strip()
        body = body[m.end():].strip()
    return {"idx":idx,"start":start,"end":end,"speaker":speaker,"text":body}

def audit_srt(srt_path: Path, out_json: Path) -> Dict[str, Any]:
    raw = srt_path.read_text(encoding="utf-8", errors="replace")
    items = [parse_block(b) for b in split_blocks(raw)]
    # fix indices
    for i, it in enumerate(items, 1):
        it["idx"] = i
    warn = []
    for a, b in zip(items, items[1:]):
        if b["start"] < a["start"]:
            warn.append({"type":"non_monotonic", "idx": b["idx"]})
        if b["start"] < a["end"]:
            warn.append({"type":"overlap", "a": a["idx"], "b": b["idx"]})

    long_caps = [it["idx"] for it in items if it["end"] - it["start"] > 10.0]
    tiny_caps = [it["idx"] for it in items if it["end"] - it["start"] < 0.3]

    spk_turns: Dict[str,int] = {}
    for it in items:
        key = it["speaker"] or "Speaker"
        spk_turns[key] = spk_turns.get(key, 0) + 1

    switches = 0
    last = None
    for it in items:
        if it["speaker"] != last:
            if last is not None: switches += 1
            last = it["speaker"]

    rep = {
        "total_items": len(items),
        "duration_s": round(items[-1]["end"] - items[0]["start"], 3) if items else 0.0,
        "warnings": warn,
        "long_segments_over_10s": long_caps,
        "short_segments_under_0.3s": tiny_caps,
        "speakers": spk_turns,
        "speaker_switches": switches
    }
    out_json.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    return rep

# ------------------ Main transcription function ------------------
def transcribe_audio(
    audio_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    progress_callback=None
) -> Tuple[Path, Path, Path]:
    """
    Main transcription function that can be called from CLI or GUI.
    
    Args:
        audio_path: Path to audio file or folder. If None, prompts user.
        output_dir: Output directory. If None, uses 'out' folder.
        progress_callback: Optional callback for progress updates.
        
    Returns:
        Tuple of (json_path, srt_path, audit_path)
    """
    load_dotenv()
    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN missing. Put it in .env.")
    
    log = setup_logger("transcribe")
    
    # Get audio path
    if audio_path is None:
        try:
            path_str = input("Enter path to meeting audio (file or folder): ").strip().strip('"')
        except KeyboardInterrupt:
            print("\n[abort]")
            sys.exit(1)
        if not path_str:
            raise ValueError("No path provided.")
        audio_path = Path(path_str)
    
    target = audio_path.expanduser().resolve()
    if not target.exists():
        raise FileNotFoundError(f"Path not found: {target}")
    
    # Set output directory
    if output_dir is None:
        output_dir = Path("out")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Progress steps: select, probe, compress, upload+transcribe, write json, build final srt, audit, cleanup
    total_steps = 8
    current_step = 0
    
    def update_progress(message: str):
        nonlocal current_step
        current_step += 1
        if progress_callback:
            progress_callback(current_step, total_steps, message)
        else:
            log.info(f"[{current_step}/{total_steps}] {message}")
    
    # 1 select
    update_progress("Selecting best audio")
    audio = pick_best_audio(target, log)
    log.info(f"[select] {audio} size={bytes_mb(audio.stat().st_size)} MB")
    
    # 2 probe
    update_progress("Probing audio")
    _ = ffprobe_info(audio, log)
    
    # 3 compress
    update_progress(f"Compressing to <= {MAX_UPLOAD_MB} MB (Opus 16k mono)")
    compressed = compress_to_under_limit(audio, MAX_UPLOAD_MB, log)
    log.info(f"[compress] chosen={compressed} size={bytes_mb(compressed.stat().st_size)} MB")
    
    # 4 upload+transcribe
    update_progress("Uploading & transcribing (Replicate)")
    try:
        raw = replicate_predict(compressed, log)
    except Exception as e:
        log.exception(f"[replicate] fatal: {e}")
        raise
    
    # 5 write json
    update_progress("Writing JSON")
    segments = to_segments(raw)
    base = audio.stem
    json_path = output_dir / f"{base}.json"
    meta = {
        "source": str(audio),
        "uploaded": str(compressed),
        "uploaded_size_mb": bytes_mb(compressed.stat().st_size),
        "provider": f"replicate:{REPLICATE_MODEL}",
        "version": REPLICATE_MODEL_VERSION or "resolved-latest",
        "mode": "transcript-paragraphized"
    }
    write_json(segments, json_path, meta)
    
    # 6 build final srt
    update_progress("Building FINAL transcript SRT")
    final_srt = output_dir / f"{base}.final.srt"
    build_final_srt_from_json(json_path, final_srt)
    if not final_srt.exists() or final_srt.stat().st_size == 0:
        raise RuntimeError("Final SRT creation failed.")
    
    # 7 audit final srt
    update_progress("Auditing final SRT")
    audit_path = output_dir / f"{base}.final.audit.json"
    audit_srt(final_srt, audit_path)
    
    # 8 cleanup legacy outputs
    update_progress("Cleanup legacy files")
    legacy = [output_dir / f"{base}.srt", output_dir / f"{base}.txt"]
    removed = []
    for f in legacy:
        try:
            if f.exists():
                f.unlink()
                removed.append(str(f))
        except Exception as e:
            log.warning(f"[cleanup] Could not remove {f}: {e}")
    if removed:
        log.info("[cleanup] Removed: " + ", ".join(removed))
    
    log.info(f"[ok] Wrote:\n  {json_path}\n  {final_srt}\n  {audit_path}")
    return json_path, final_srt, audit_path

# ------------------ CLI entry point ------------------
def main():
    """CLI entry point for standalone usage."""
    try:
        json_path, srt_path, audit_path = transcribe_audio()
        print(f"[ok] Wrote:\n  {json_path}\n  {srt_path}\n  {audit_path}")
    except Exception as e:
        logging.exception(f"[fatal] {e}")
        print(f"[fatal] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()