# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Summeets** is a production-grade Python monorepo for transcribing and summarizing meetings with speaker diarization. It provides a shared processing core exposed through both CLI and GUI interfaces:

### Key Features
- **Audio Processing**: FFmpeg-based normalization, extraction, and format conversion
- **Transcription**: Replicate's `thomasmol/whisper-diarization` (Whisper v3 + Pyannote) for speaker-aware transcription
- **Summarization**: Map-reduce + Chain-of-Density summarization with OpenAI GPT-4o or Anthropic Claude
- **Dual Interface**: Full-featured CLI (`summeets`) and tkinter GUI (`summeets-gui`) sharing the same core
- **Production Ready**: Structured logging, configuration management, error handling, comprehensive test suite

### Architecture
The project follows clean architecture principles with clear separation of concerns:
- **Core Module**: Shared business logic, models, and utilities
- **CLI Interface**: Typer-based command-line interface
- **GUI Interface**: tkinter-based graphical user interface
- **Main Entry Point**: Router that launches CLI or GUI based on arguments

## Dependencies

Install the package and its dependencies:
```bash
pip install -e .
```

Core dependencies include:
- `typer` - CLI framework
- `tkinter` - Built-in GUI framework (no additional installation required)
- `pydantic` + `pydantic-settings` - Configuration and validation
- `openai` + `anthropic` - LLM providers for summarization
- `replicate` - Transcription API
- `tenacity` - Retry logic
- `alive-progress` - Progress indicators
- `rich` - Terminal formatting

External dependencies:
- `ffmpeg` and `ffprobe` (optional but recommended) - For audio processing

## Environment Setup

1. Create a `.env` file with your API keys:
   ```env
   # LLM Provider (openai or anthropic)
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-4o-mini
   
   # API Keys (at least one required)
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   REPLICATE_API_TOKEN=r8_...
   
   # Optional settings
   SUMMARY_MAX_OUTPUT_TOKENS=3000
   SUMMARY_CHUNK_SECONDS=1800
   SUMMARY_COD_PASSES=2
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

## Running the Tool

### CLI Interface
```bash
# Complete pipeline (transcribe + summarize)
summeets process /path/to/meeting.m4a

# Individual steps
summeets transcribe /path/to/audio.m4a
summeets summarize out/audio.json --provider openai --model gpt-4o

# Audio processing
summeets normalize input.mkv output.mkv
summeets extract input.mkv output.m4a --codec aac
summeets probe input.mkv

# View configuration
summeets config
```

### GUI Interface
```bash
summeets-gui
# or
python main.py gui
```

### Direct Execution
```bash
# Default: launches GUI
python main.py

# Explicit CLI/GUI
python main.py cli transcribe audio.m4a
python main.py gui
```

## Code Architecture

### Clean Architecture Structure
```
summeets/
├─ core/                    # Shared processing core
│  ├─ models.py             # Pydantic data models & job tracking
│  ├─ config.py             # Pydantic settings management
│  ├─ logging.py            # Structured logging setup
│  ├─ fsio.py               # File system operations
│  ├─ jobs.py               # Job management
│  ├─ audio/                # Audio processing
│  │  ├─ ffmpeg_ops.py      # FFmpeg operations
│  │  ├─ selection.py       # Audio file selection logic
│  │  └─ compression.py     # Audio compression utilities
│  ├─ providers/            # LLM clients
│  │  ├─ openai_client.py   # OpenAI API client
│  │  └─ anthropic_client.py # Anthropic API client
│  ├─ transcribe/           # Transcription pipeline
│  │  └─ pipeline.py        # Main transcription logic
│  ├─ transcription/        # Transcription utilities
│  │  ├─ replicate_api.py   # Replicate API integration
│  │  └─ formatting.py      # Output formatting (JSON, SRT)
│  ├─ summarize/            # Summarization pipeline
│  │  └─ pipeline.py        # Map-reduce + COD summarization
│  ├─ cache.py              # Caching utilities
│  ├─ security.py           # Security utilities
│  ├─ validation.py         # Input validation
│  └─ exceptions.py         # Custom exceptions
├─ cli/app.py               # Typer CLI interface
├─ gui/app.py               # Textual GUI interface
├─ main.py                  # Entry point router
├─ data/                    # Organized data storage
│  ├─ input/                # Input files (by date)
│  ├─ output/               # Processing results (by date/type)
│  ├─ temp/                 # Temporary files
│  └─ jobs/                 # Job state persistence
├─ tests/                   # Comprehensive test suite
│  ├─ unit/                 # Unit tests
│  ├─ integration/          # Integration tests
│  └─ conftest.py           # Test configuration
└─ scripts/win_dev.ps1      # Development setup script
```

### Core Components

- **Audio Selection** (`core.audio.selection`): Intelligently selects highest quality audio from directories
- **Audio Processing** (`core.audio.ffmpeg_ops`): FFmpeg-based normalization, extraction, conversion
- **Transcription Pipeline** (`core.transcribe.pipeline`): Replicate API integration with progress tracking
- **Summarization Pipeline** (`core.summarize.pipeline`): Map-reduce chunking + Chain-of-Density refinement
- **LLM Providers** (`core.providers`): Unified interface for OpenAI and Anthropic APIs
- **Configuration** (`core.config`): Pydantic-based settings with environment variable support
- **Job Management** (`core.jobs`): State persistence and progress tracking

### Data Models

- `TranscriptWord`: Individual word with timing and confidence
- `TranscriptSegment`: Text segment with speaker attribution and word-level timing
- `TranscriptData`: Complete transcript with metadata
- `SummaryData`: Structured summary with sections and metadata
- `JobData`: Job state tracking for long-running operations

## Supported Audio Formats

Ranked by preference: `.m4a`, `.flac`, `.wav`, `.mka`, `.ogg`, `.mp3`, `.webm`

The tool automatically prioritizes "normalized" files and selects based on audio quality metrics.

## Development

### Code Quality Tools
```bash
# Type checking
mypy core/ cli/ gui/

# Linting
ruff check .

# Testing
python -m pytest tests/
```

### Entry Points
- `summeets` command maps to `main:main` function
- Both CLI and GUI share the same core processing logic
- Configuration is centralized through Pydantic settings