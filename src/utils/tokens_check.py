# tools/tokens_check.py
import argparse
import json
from pathlib import Path
from ..tokenizer import TokenBudget, plan_fit
from ..summarize.legacy_prompts import SYSTEM_CORE, CHUNK_PROMPT, REDUCE_PROMPT
from ..summarize.legacy_prompts import format_chunk_text, format_partial_summaries

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True, type=Path)
    ap.add_argument("--provider", choices=["openai","anthropic"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--encoding", default="o200k_base")
    ap.add_argument("--ctx", type=int, required=True, help="context window tokens")
    ap.add_argument("--out", type=int, default=800, help="planned max_output_tokens")
    ap.add_argument("--margin", type=int, default=512)
    ap.add_argument("--chunk-seconds", type=int, default=1800)
    args = ap.parse_args()

    transcript_data = json.loads(Path(args.transcript).read_text(encoding="utf-8"))
    # Handle both formats: direct array or {"segments": [...]}
    segments = transcript_data if isinstance(transcript_data, list) else transcript_data.get("segments", [])

    # naive time-based chunking like pipeline
    chunks = []
    cur = []
    start = None
    for s in segments:
        if start is None:
            start = s.get("start", 0)
        cur.append(s)
        if s.get("end", 0) - start >= args.chunk_seconds:
            chunks.append(cur); cur=[]; start=None
    if cur:
        chunks.append(cur)

    budget = TokenBudget(args.ctx, args.out, args.margin)

    # map phase checks
    for i, chunk in enumerate(chunks, 1):
        chunk_text = format_chunk_text(chunk)
        prompt = CHUNK_PROMPT.format(chunk=chunk_text)
        messages = [{"role": "user", "content": prompt}]
        n, fits = plan_fit(args.provider, args.model, messages, budget, system=SYSTEM_CORE, encoding=args.encoding)
        print(f"map[{i}] tokens={n}, fits={fits}")

    # reduce phase check (using synthesized partials)
    partials = []
    for chunk in chunks:
        partials.append("PLACEHOLDER_PARTIAL_SUMMARY")  # we just need structure for sizing
    parts_text = format_partial_summaries(partials)
    final_prompt = REDUCE_PROMPT.format(parts=parts_text)
    messages = [{"role": "user", "content": final_prompt}]
    n, fits = plan_fit(args.provider, args.model, messages, budget, system=SYSTEM_CORE, encoding=args.encoding)
    print(f"reduce tokens={n}, fits={fits}")

if __name__ == "__main__":
    main()
