#!/usr/bin/env python3
"""
Summarization module for Summeets
Handles meeting summarization using OpenAI or Anthropic LLMs
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import re
import sys
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# Optional dotenv for local development
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except Exception:
    pass

# --- Configuration from env with sane defaults ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1").strip()
SUMMARY_MAX_OUTPUT_TOKENS = int(os.getenv("SUMMARY_MAX_OUTPUT_TOKENS", "3000"))
SUMMARY_CHUNK_SECONDS = int(os.getenv("SUMMARY_CHUNK_SECONDS", "1800"))  # 30 min
SUMMARY_COD_PASSES = int(os.getenv("SUMMARY_COD_PASSES", "2"))

# --- Lazy client loaders to avoid hard deps unless used ---
def _get_openai():
    from openai import OpenAI
    return OpenAI()

def _get_anthropic():
    from anthropic import Anthropic
    return Anthropic()

# --- SRT/JSON transcript handling ---
_ts_pat = re.compile(r"(\d\d):(\d\d):(\d\d),(\d\d\d)")

def _to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0

def _parse_srt(path: pathlib.Path) -> List[Dict[str, Any]]:
    blocks = path.read_text(encoding="utf-8", errors="ignore").split("\n\n")
    segs: List[Dict[str, Any]] = []
    for b in blocks:
        lines = [ln.strip() for ln in b.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        time_line = next((ln for ln in lines if "-->" in ln), "")
        times = list(_ts_pat.finditer(time_line))
        if len(times) < 2:
            continue
        (h1, m1s, s1, ms1) = times[0].groups()
        (h2, m2s, s2, ms2) = times[1].groups()
        content = [ln for ln in lines if "-->" not in ln and not ln.isdigit()]
        text = " ".join(content).strip()
        speaker = None
        first = text.split(" ", 1)[0] if text else ""
        if first.endswith(":") and len(first) < 40:
            speaker = first[:-1]
        segs.append({
            "start": _to_seconds(h1, m1s, s1, ms1),
            "end": _to_seconds(h2, m2s, s2, ms2),
            "speaker": speaker or "Speaker",
            "text": text
        })
    return segs

def load_segments_from_path(path: pathlib.Path) -> List[Dict[str, Any]]:
    """Load segments from a JSON or SRT transcript file."""
    if not path.exists():
        raise FileNotFoundError(path)
    ext = path.suffix.lower()
    if ext == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        segs = raw.get("segments", raw) if isinstance(raw, dict) else raw
        out: List[Dict[str, Any]] = []
        for s in segs:
            if not s:
                continue
            out.append({
                "start": float(s.get("start", 0.0)),
                "end": float(s.get("end", 0.0)),
                "speaker": s.get("speaker", "Speaker"),
                "text": (s.get("text") or "").strip(),
            })
        return out
    if ext == ".srt":
        return _parse_srt(path)
    raise ValueError(f"Unsupported transcript type: {ext} (expected .json or .srt)")

def resolve_transcript_by_audio(audio_path: pathlib.Path) -> pathlib.Path:
    """
    Given audio path like audio_files/Workshop_audio_norm.m4a,
    derive transcript under ../out with stems:
      out/Workshop_audio_norm.json
      out/Workshop_audio_norm.final.srt
      out/Workshop_audio_norm.srt
    """
    base_noext = audio_path.with_suffix("")
    if base_noext.parent.name == "audio_files":
        out_dir = base_noext.parent.parent / "out"
    else:
        out_dir = base_noext.parent / "out"
    stem = base_noext.stem.replace(".final", "")
    candidates = [
        out_dir / f"{stem}.json",
        out_dir / f"{stem}.final.srt",
        out_dir / f"{stem}.srt",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f"No transcript for stem '{stem}' in {out_dir}")

def determine_out_dir_and_stem(hint_path: pathlib.Path, transcript_explicit: bool) -> Tuple[pathlib.Path, str]:
    """
    Returns (out_dir, stem_for_outputs). If transcript was explicit and lives under /out,
    keep outputs beside it; otherwise use sibling /out/.
    """
    if transcript_explicit:
        if hint_path.parent.name == "out":
            out_dir = hint_path.parent
            stem = hint_path.stem.replace(".final", "")
            return out_dir, stem
        out_dir = hint_path.parent / "out"
        stem = hint_path.stem.replace(".final", "")
        return out_dir, stem
    if hint_path.parent.name == "audio_files":
        out_dir = hint_path.parent.parent / "out"
    else:
        out_dir = hint_path.parent / "out"
    stem = hint_path.stem.replace(".final", "")
    return out_dir, stem

# --- Chunking utilities ---
def _chunk_by_time(segs: List[Dict[str, Any]], seconds: int) -> List[List[Dict[str, Any]]]:
    if seconds <= 0:
        return [segs]
    chunks: List[List[Dict[str, Any]]] = []
    cur: List[Dict[str, Any]] = []
    cur_start: Optional[float] = None
    for seg in segs:
        if cur_start is None:
            cur_start = seg["start"]
        cur.append(seg)
        if seg["end"] - cur_start >= seconds:
            chunks.append(cur)
            cur = []
            cur_start = None
    if cur:
        chunks.append(cur)
    return chunks

def _fmt_chunk_txt(chunk: List[Dict[str, Any]]) -> str:
    return "\n".join(
        f"[{seg['start']:.2f}s] {seg.get('speaker','Speaker')}: {seg.get('text','')}"
        for seg in chunk
    )

# --- Prompts ---
SYSTEM_CORE = (
    "You are a surgical meeting summarizer. Write with extreme recall and structure. "
    "Never invent facts. Include timestamps when possible.\n"
    "Audience: busy executives and the delivery team.\n"
)

CHUNK_PROMPT = (
    "Summarize this transcript chunk into the following sections. Be exhaustive but concise. "
    "Preserve numbers, owners, and dates. Include timestamp ranges in [mm:ss] where possible.\n\n"
    "Required sections:\n"
    "1) Key Points\n"
    "2) Decisions\n"
    "3) Action Items [owner | item | due | status]\n"
    "4) Risks/Blockers\n"
    "5) Open Questions\n"
    "6) Notable Quotes [timestamp | speaker | quote]\n\n"
    "Transcript chunk:\n{chunk}\n"
)

REDUCE_PROMPT = (
    "You are given ordered partial summaries from consecutive chunks of the same meeting. "
    "Merge them into a single, deduplicated, contradiction-resolved report with the sections:\n"
    "## Executive Summary (≤10 bullets)\n"
    "## Decisions\n"
    "## Action Items (owner | item | due | status)\n"
    "## Risks/Blockers\n"
    "## Open Questions\n"
    "## Timeline of Key Moments [timestamp | what happened]\n"
    "## Stakeholders & Responsibilities\n"
    "## Next Steps\n"
    "## Glossary (if any abbreviations)\n\n"
    "Partial summaries:\n{parts}\n"
)

COD_PROMPT = (
    "Chain-of-Density refinement. Improve the following meeting summary by adding missing salient entities, "
    "numbers, owners, and dates without increasing verbosity. Keep the same sections and structure. "
    "Prefer facts grounded in the transcript. Return the full improved summary.\n\n"
    "Current summary:\n{current}\n"
)

STRUCTURED_JSON_SPEC = {
    "name": "MeetingSummary",
    "schema": {
        "type": "object",
        "properties": {
            "executive_summary": {"type": "array", "items": {"type": "string"}},
            "decisions": {"type": "array", "items": {"type": "string"}},
            "action_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "item": {"type": "string"},
                        "due": {"type": "string"},
                        "status": {"type": "string"},
                        "timestamp": {"type": "string"},
                    },
                    "required": ["owner", "item"],
                    "additionalProperties": False,
                },
            },
            "risks": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
            "timeline": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "string"},
                        "event": {"type": "string"},
                    },
                    "required": ["event"],
                    "additionalProperties": False,
                },
            },
            "stakeholders": {"type": "array", "items": {"type": "string"}},
            "next_steps": {"type": "array", "items": {"type": "string"}},
            "glossary": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["executive_summary", "decisions", "action_items", "risks", "open_questions"],
        "additionalProperties": False,
    },
    "strict": True,
}

# --- LLM client wrapper ---
@dataclass
class LLM:
    provider: str
    model: str
    max_output_tokens: int

    def _check_keys(self):
        if self.provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set")
        if self.provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set")

    def summarize(self, content: str, system: Optional[str] = None) -> str:
        self._check_keys()
        if self.provider == "openai":
            client = _get_openai()
            # Responses API (preferred) — https://platform.openai.com/docs/api-reference/responses
            kwargs = {
                "model": self.model,
                "input": content if not system else f"System:\n{system}\n\nUser:\n{content}",
                "max_output_tokens": self.max_output_tokens,
                "temperature": 0.2,
            }
            resp = client.responses.create(**kwargs)
            return resp.output_text
        elif self.provider == "anthropic":
            client = _get_anthropic()
            # Messages API — https://docs.anthropic.com/en/api/messages
            msg = client.messages.create(
                model=self.model,
                max_tokens=self.max_output_tokens,
                temperature=0.2,
                system=system or SYSTEM_CORE,
                messages=[{"role": "user", "content": content}],
            )
            return "".join(getattr(part, "text", "") for part in msg.content)
        raise ValueError(f"Unsupported provider: {self.provider}")

    def structured_json(self, content: str) -> str:
        """
        Primary: OpenAI Responses API with response_format=json_schema (Structured Outputs).
        Fallback A: Responses API without response_format (prompt-enforced JSON).
        Fallback B: Chat Completions JSON mode if available.
        Anthropic: prompt-enforced JSON.
        """
        self._check_keys()
        if self.provider == "openai":
            client = _get_openai()
            # Try Structured Outputs first
            try:
                resp = client.responses.create(
                    model=self.model,
                    input=content,
                    response_format={"type": "json_schema", "json_schema": STRUCTURED_JSON_SPEC},
                    max_output_tokens=self.max_output_tokens,
                    temperature=0.0,
                )
                return resp.output_text
            except TypeError:
                # Older SDK without 'response_format' on Responses API
                pass
            except Exception:
                # Some models/versions may not accept response_format; continue to fallbacks
                pass
            # Fallback A: prompt-enforced JSON via Responses API
            try:
                prompt = (
                    "Return only minified JSON. No prose. Strictly include keys: "
                    "executive_summary, decisions, action_items, risks, open_questions, timeline, stakeholders, next_steps, glossary.\n\n"
                    + content
                )
                resp = client.responses.create(
                    model=self.model,
                    input=prompt,
                    max_output_tokens=self.max_output_tokens,
                    temperature=0.0,
                )
                return resp.output_text
            except Exception:
                # Fallback B: Chat Completions JSON mode (json_object)
                try:
                    cc = client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "Return only minified JSON. No extra text."},
                            {"role": "user", "content": content},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.0,
                    )
                    return cc.choices[0].message.content or ""
                except Exception as e:
                    raise e
        else:
            # Anthropic best-effort JSON
            text = self.summarize(
                "Return only minified JSON for this content. No commentary. "
                "Include keys: executive_summary, decisions, action_items, risks, open_questions, timeline, stakeholders, next_steps, glossary.\n\n"
                + content,
                system="Return only minified JSON. No extra text.",
            )
            return text

# --- Pipeline ---
def summarize_pipeline_from_segments(
    segs: List[Dict[str, Any]],
    out_dir: pathlib.Path,
    stem: str,
    provider: str,
    model: str,
    chunk_seconds: int,
    cod_passes: int,
    max_tokens: int,
    progress_callback=None
) -> Tuple[pathlib.Path, pathlib.Path]:
    """
    Summarize segments and produce markdown and JSON outputs.
    
    Args:
        segs: List of transcript segments
        out_dir: Output directory
        stem: Base filename stem
        provider: LLM provider (openai/anthropic)
        model: Model name
        chunk_seconds: Chunk size in seconds (0 to disable)
        cod_passes: Chain-of-Density refinement passes
        max_tokens: Max output tokens per request
        progress_callback: Optional callback for progress updates
        
    Returns:
        Tuple of (md_path, json_path)
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    llm = LLM(provider, model, max_tokens)

    chunks = _chunk_by_time(segs, chunk_seconds)
    logging.info("Summarizing %d chunk(s) with %s/%s", len(chunks), provider, model)
    
    total_steps = len(chunks) + 1 + cod_passes + 1  # chunks + reduce + CoD passes + JSON
    current_step = 0
    
    def update_progress(message: str):
        nonlocal current_step
        current_step += 1
        if progress_callback:
            progress_callback(current_step, total_steps, message)

    # map
    partials: List[str] = []
    for i, ch in enumerate(chunks, 1):
        payload = _fmt_chunk_txt(ch)
        prompt = CHUNK_PROMPT.format(chunk=payload)
        update_progress(f"Processing chunk {i}/{len(chunks)}")
        logging.info("  Chunk %d/%d (%d segs)", i, len(chunks), len(ch))
        partials.append(llm.summarize(prompt, system=SYSTEM_CORE))

    # reduce
    update_progress("Merging summaries")
    parts_blob = "\n\n".join(f"### Part {i}\n{p}" for i, p in enumerate(partials, 1))
    final_md = llm.summarize(REDUCE_PROMPT.format(parts=parts_blob), system=SYSTEM_CORE).strip()

    # Chain-of-Density refinement
    for pidx in range(max(cod_passes, 0)):
        update_progress(f"Refinement pass {pidx + 1}/{cod_passes}")
        final_md = llm.summarize(COD_PROMPT.format(current=final_md), system=SYSTEM_CORE).strip()
        logging.info("  CoD refinement pass %d complete", pidx + 1)

    # JSON extraction
    update_progress("Extracting structured JSON")
    schema_instructions = textwrap.dedent(
        f"""
        Extract JSON for the following keys ONLY:
        executive_summary, decisions, action_items, risks, open_questions, timeline, stakeholders, next_steps, glossary.
        Base your JSON strictly on this final summary. Do not invent fields or content.

        Final summary:
        {final_md}
        """
    ).strip()
    final_json = llm.structured_json(schema_instructions).strip()

    md_path = out_dir / f"{stem}.summary.md"
    json_path = out_dir / f"{stem}.summary.json"

    md_path.write_text(final_md, encoding="utf-8")
    try:
        json.loads(final_json)  # validate
        json_path.write_text(final_json, encoding="utf-8")
    except Exception:
        # still write best-effort JSON text for debugging
        json_path.write_text(final_json, encoding="utf-8")

    logging.info("Summary written:\n  %s\n  %s", md_path, json_path)
    return md_path, json_path

def summarize_transcript(
    transcript_path: Optional[pathlib.Path] = None,
    audio_path: Optional[pathlib.Path] = None,
    provider: str = LLM_PROVIDER,
    model: str = LLM_MODEL,
    chunk_seconds: int = SUMMARY_CHUNK_SECONDS,
    cod_passes: int = SUMMARY_COD_PASSES,
    max_output_tokens: int = SUMMARY_MAX_OUTPUT_TOKENS,
    progress_callback=None
) -> Tuple[pathlib.Path, pathlib.Path]:
    """
    Main summarization function that can be called from CLI or GUI.
    
    Args:
        transcript_path: Path to transcript (.json or .srt). Takes precedence over audio_path.
        audio_path: Path to original audio; used only to infer transcript stem in /out.
        provider: LLM provider (openai/anthropic)
        model: Model name
        chunk_seconds: Chunk size in seconds (0 to disable)
        cod_passes: Chain-of-Density refinement passes
        max_output_tokens: Max output tokens per request
        progress_callback: Optional callback for progress updates
        
    Returns:
        Tuple of (md_path, json_path)
    """
    transcript_explicit = bool(transcript_path)
    
    if transcript_explicit:
        tpath = transcript_path.resolve()
        segs = load_segments_from_path(tpath)
        out_dir, stem = determine_out_dir_and_stem(tpath, transcript_explicit=True)
    elif audio_path:
        apath = audio_path.resolve()
        tpath = resolve_transcript_by_audio(apath)
        segs = load_segments_from_path(tpath)
        out_dir, stem = determine_out_dir_and_stem(apath, transcript_explicit=False)
    else:
        raise ValueError("Either transcript_path or audio_path must be provided")

    return summarize_pipeline_from_segments(
        segs=segs,
        out_dir=out_dir,
        stem=stem,
        provider=provider,
        model=model,
        chunk_seconds=chunk_seconds,
        cod_passes=cod_passes,
        max_tokens=max_output_tokens,
        progress_callback=progress_callback
    )