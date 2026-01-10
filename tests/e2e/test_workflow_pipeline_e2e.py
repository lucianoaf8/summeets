import json
from pathlib import Path

from src.workflow import WorkflowConfig, execute_workflow


def _stub_filesystem(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stub")
    return path


def test_workflow_e2e_video_pipeline(monkeypatch, tmp_path):
    """End-to-end workflow for video input with all steps stubbed."""
    # Input video placeholder
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"00")

    calls = {
        "extract": 0,
        "volume": 0,
        "normalize": 0,
        "convert": 0,
        "ensure_wav": 0,
        "transcribe": 0,
        "summarize": 0,
    }

    import src.workflow as workflow

    def fake_extract(video_path, output_path, format="m4a", quality="high", normalize=True):
        calls["extract"] += 1
        return _stub_filesystem(output_path)

    def fake_volume(input_path, output_path, gain_db=10.0):
        calls["volume"] += 1
        return _stub_filesystem(output_path)

    def fake_normalize(input_path, output_path):
        calls["normalize"] += 1
        return _stub_filesystem(Path(output_path))

    def fake_convert(input_path, output_path, format="m4a", quality="medium"):
        calls["convert"] += 1
        return _stub_filesystem(output_path)

    def fake_ensure_wav(audio_path):
        calls["ensure_wav"] += 1
        return audio_path

    def fake_transcribe_run(audio_path, output_dir=None, **_):
        calls["transcribe"] += 1
        out_dir = Path(output_dir or tmp_path)
        transcript_path = out_dir / "sample.json"
        _stub_filesystem(transcript_path)
        return transcript_path

    def fake_summarize_run(transcript_path, provider, model, output_dir=None, **_):
        calls["summarize"] += 1
        out_dir = Path(output_dir or tmp_path)
        summary_json = out_dir / "sample.summary.json"
        summary_md = out_dir / "sample.summary.md"
        _stub_filesystem(summary_json)
        _stub_filesystem(summary_md)
        return summary_json, summary_md

    # Patch workflow dependencies to avoid real ffmpeg/API calls
    monkeypatch.setattr(workflow, "extract_audio_from_video", fake_extract)
    monkeypatch.setattr(workflow, "increase_audio_volume", fake_volume)
    monkeypatch.setattr(workflow, "normalize_loudness", fake_normalize)
    monkeypatch.setattr(workflow, "convert_audio_format", fake_convert)
    monkeypatch.setattr(workflow, "ensure_wav16k_mono", fake_ensure_wav)
    monkeypatch.setattr(workflow, "transcribe_run", fake_transcribe_run)
    monkeypatch.setattr(workflow, "summarize_run", fake_summarize_run)

    config = WorkflowConfig(
        input_file=video_path,
        output_dir=tmp_path / "out",
        extract_audio=True,
        process_audio=True,
        transcribe=True,
        summarize=True,
        audio_format="m4a",
        audio_quality="high",
        normalize_audio=True,
        output_formats=["m4a"],
        summary_template="default",
        provider="openai",
        model="gpt-4o-mini",
    )

    results = execute_workflow(config)

    # Assert step execution order and artifacts
    assert calls["extract"] == 1
    assert calls["volume"] == 0 or calls["volume"] == 1  # optional gain
    assert calls["normalize"] == 1
    assert calls["transcribe"] == 1
    assert calls["summarize"] == 1
    assert "transcribe" in results and "summarize" in results
    summary_file = Path(results["summarize"]["summary_file"])
    assert summary_file.exists()


def test_workflow_e2e_transcript_only(monkeypatch, tmp_path):
    """End-to-end workflow starting from transcript input, skipping audio work."""
    transcript_path = tmp_path / "input.json"
    transcript_path.write_text(json.dumps({"segments": [{"start": 0, "end": 1, "text": "hello"}]}))

    calls = {"transcribe": 0, "summarize": 0}

    import src.workflow as workflow

    def fake_transcribe_run(*args, **kwargs):
        calls["transcribe"] += 1
        raise AssertionError("transcription should not run for transcript inputs")

    def fake_summarize_run(transcript_path, provider, model, output_dir=None, **_):
        calls["summarize"] += 1
        out_dir = Path(output_dir or tmp_path)
        summary_json = out_dir / "input.summary.json"
        summary_md = out_dir / "input.summary.md"
        _stub_filesystem(summary_json)
        _stub_filesystem(summary_md)
        return summary_json, summary_md

    monkeypatch.setattr(workflow, "transcribe_run", fake_transcribe_run)
    monkeypatch.setattr(workflow, "summarize_run", fake_summarize_run)

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

    assert calls["transcribe"] == 0
    assert calls["summarize"] == 1
    summary_file = Path(results["summarize"]["summary_file"])
    assert summary_file.exists()


def test_workflow_audio_pipeline(monkeypatch, tmp_path):
    """Audio input should skip extraction but process/transcribe/summarize."""
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"00")

    calls = {"extract": 0, "process": 0, "ensure_wav": 0, "transcribe": 0, "summarize": 0}

    import src.workflow as workflow

    def fake_extract(*args, **kwargs):
        calls["extract"] += 1
        raise AssertionError("extract should not run for audio files")

    def fake_process_audio(input_path, output_path, gain_db=0, format=None, quality=None):
        calls["process"] += 1
        return _stub_filesystem(Path(output_path))

    def fake_ensure_wav(audio_path):
        calls["ensure_wav"] += 1
        return audio_path

    def fake_transcribe_run(audio_path, output_dir=None, **_):
        calls["transcribe"] += 1
        transcript = (output_dir or tmp_path) / "sample.json"
        _stub_filesystem(transcript)
        return transcript

    def fake_summarize_run(transcript_path, provider, model, output_dir=None, **_):
        calls["summarize"] += 1
        out_dir = Path(output_dir or tmp_path)
        summary_json = out_dir / "sample.summary.json"
        summary_md = out_dir / "sample.summary.md"
        _stub_filesystem(summary_json)
        _stub_filesystem(summary_md)
        return summary_json, summary_md

    monkeypatch.setattr(workflow, "extract_audio_from_video", fake_extract)
    monkeypatch.setattr(workflow, "increase_audio_volume", fake_process_audio)
    monkeypatch.setattr(workflow, "normalize_loudness", fake_process_audio)
    monkeypatch.setattr(workflow, "convert_audio_format", fake_process_audio)
    monkeypatch.setattr(workflow, "ensure_wav16k_mono", fake_ensure_wav)
    monkeypatch.setattr(workflow, "transcribe_run", fake_transcribe_run)
    monkeypatch.setattr(workflow, "summarize_run", fake_summarize_run)

    config = WorkflowConfig(
        input_file=audio_path,
        output_dir=tmp_path / "out",
        extract_audio=False,
        process_audio=True,
        transcribe=True,
        summarize=True,
        audio_format="m4a",
        audio_quality="high",
        normalize_audio=True,
        output_formats=["m4a"],
        summary_template="default",
        provider="openai",
        model="gpt-4o-mini",
    )

    results = execute_workflow(config)

    assert calls["extract"] == 0
    assert calls["ensure_wav"] == 1
    assert calls["transcribe"] == 1
    assert calls["summarize"] == 1
    assert "summarize" in results


def test_workflow_respects_auto_detect(monkeypatch, tmp_path):
    """Ensure auto_detect_template flag is passed through to summarize pipeline."""
    transcript_path = tmp_path / "input.json"
    transcript_path.write_text(json.dumps({"segments": []}))

    seen_flags = []

    import src.workflow as workflow

    def fake_transcribe_run(*args, **kwargs):
        raise AssertionError("transcription should not be called")

    def fake_summarize_run(transcript_path, provider, model, output_dir=None, auto_detect_template=True, **_):
        seen_flags.append(auto_detect_template)
        out_dir = Path(output_dir or tmp_path)
        summary_json = out_dir / "input.summary.json"
        summary_md = out_dir / "input.summary.md"
        _stub_filesystem(summary_json)
        _stub_filesystem(summary_md)
        return summary_json, summary_md

    monkeypatch.setattr(workflow, "transcribe_run", fake_transcribe_run)
    monkeypatch.setattr(workflow, "summarize_run", fake_summarize_run)

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
        auto_detect_template=False,
    )

    execute_workflow(config)
    assert seen_flags == [False]
