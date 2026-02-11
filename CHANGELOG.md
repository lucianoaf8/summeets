# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-02-06

### Added

- **CLI Interface**: Typer-based commands (`transcribe`, `summarize`, `process`, `config`, `health`, `templates`, `tui`)
- **TUI Interface**: Textual-based terminal GUI with real-time progress tracking via `summeets tui`
- **Audio Processing**: FFmpeg-based normalization, extraction, format conversion, and volume adjustment
- **Transcription Pipeline**: Replicate API integration (Whisper v3 + Pyannote) with speaker diarization
- **Summarization Pipeline**: Map-reduce chunking + Chain-of-Density refinement with OpenAI and Anthropic providers
- **Summary Templates**: Five templates (default, SOP, decision, brainstorm, requirements) with auto-detection
- **Workflow Engine**: Flexible pipeline composition supporting video, audio, and transcript inputs
- **Configuration**: Pydantic-based settings with environment variable support and `.env` file loading
- **Structured Logging**: API key sanitization, log injection prevention via `SanitizingFormatter`
- **Job Management**: State persistence and progress tracking for long-running operations
- **Security**: FFmpeg binary allowlisting, path traversal prevention, secure temp file handling
- **Service Layer**: Dependency injection container with abstract interfaces
- **Supported Formats**: Audio (m4a, flac, wav, mka, ogg, mp3, webm), Video (mp4, mkv, avi, mov, wmv, flv, webm, m4v), Transcript (json, txt)
