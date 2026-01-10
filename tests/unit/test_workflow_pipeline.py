import json
from pathlib import Path

from src.workflow import WorkflowConfig, execute_workflow


def test_execute_workflow_transcript_only(monkeypatch, tmp_path):
    """Run workflow summarize-only path with a transcript file and stubbed deps."""
    transcript_path = tmp_path / "sample.json"
    transcript_path.write_text(json.dumps({"segments": [{"start": 0, "end": 1, "text": "hello"}]}))

    call_counts = {"summary": 0, "transcribe": 0}

    def fake_summarize_run(transcript_path, provider, model, output_dir=None, **_):
        call_counts["summary"] += 1
        out_dir = Path(output_dir or tmp_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        summary_json = out_dir / "sample.summary.json"
        summary_md = out_dir / "sample.summary.md"
        summary_json.write_text("{}")
        summary_md.write_text("# summary")
        return summary_json, summary_md

    def fake_transcribe_run(*args, **kwargs):
        call_counts["transcribe"] += 1
        raise AssertionError("transcription should not be called for transcript inputs")

    # Patch pipeline hooks so no external services or ffmpeg are needed
    import src.workflow as workflow

    monkeypatch.setattr(workflow, "summarize_run", fake_summarize_run)
    monkeypatch.setattr(workflow, "transcribe_run", fake_transcribe_run)

    config = WorkflowConfig(
        input_file=transcript_path,
        output_dir=tmp_path / "out",
        extract_audio=False,
        process_audio=False,
        transcribe=False,
        summarize=True,
        summary_template="default",
        provider="openai",
        model="gpt-4o-mini",
    )

    results = execute_workflow(config)

    assert call_counts["transcribe"] == 0
    assert call_counts["summary"] == 1
    summarize_results = results.get("summarize")
    assert summarize_results is not None
    summary_file = Path(summarize_results["summary_file"])
    assert summary_file.exists()
