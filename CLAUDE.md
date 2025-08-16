# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Summeets** is a production-grade Python monorepo for transcribing and summarizing meetings with speaker diarization. It provides a shared processing core exposed through both CLI and GUI interfaces:

### Key Features
- **Audio Processing**: FFmpeg-based normalization, extraction, and format conversion
- **Transcription**: Replicate's `thomasmol/whisper-diarization` (Whisper v3 + Pyannote) for speaker-aware transcription
- **Summarization**: Map-reduce + Chain-of-Density summarization with OpenAI GPT-4o or Anthropic Claude
- **Dual Interface**: Full-featured CLI (`summeets`) and Electron GUI (`python main.py gui`) sharing the same core
- **Production Ready**: Structured logging, configuration management, error handling, comprehensive test suite

### Architecture
The project follows clean architecture principles with clear separation of concerns:
- **Core Module**: Shared business logic, models, and utilities
- **CLI Interface**: Typer-based command-line interface
- **GUI Interface**: Electron-based graphical user interface
- **Main Entry Point**: Router that launches CLI or GUI based on arguments

## Dependencies

Install the package and its dependencies:
```bash
pip install -e .
```

Core dependencies include:
- `typer` - CLI framework
- `ttkbootstrap` - Modern tkinter themes (removed - now using Electron)
- `pydantic` + `pydantic-settings` - Configuration and validation
- `openai` + `anthropic` - LLM providers for summarization
- `replicate` - Transcription API
- `tenacity` - Retry logic
- `alive-progress` - Progress indicators
- `rich` - Terminal formatting

External dependencies:
- `ffmpeg` and `ffprobe` (optional but recommended) - For audio/video processing
- `Node.js` and `npm` - Required for Electron GUI

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
python main.py gui
# or (default behavior)
python main.py
```

Requirements:
- Node.js and npm must be installed

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
│  ├─ workflow.py           # Flexible workflow engine
│  ├─ audio/                # Audio/video processing
│  │  ├─ ffmpeg_ops.py      # FFmpeg operations (audio + video)
│  │  ├─ selection.py       # Audio file selection logic
│  │  └─ compression.py     # Audio compression utilities
│  ├─ providers/            # LLM clients
│  │  ├─ openai_client.py   # OpenAI API client
│  │  └─ anthropic_client.py # Anthropic API client
│  ├─ transcribe/           # Transcription pipeline
│  │  ├─ pipeline.py        # Main transcription logic
│  │  ├─ formatting.py      # Output formatting (JSON, SRT)
│  │  └─ replicate_api.py   # Replicate API integration
│  ├─ summarize/            # Summarization pipeline
│  │  └─ pipeline.py        # Map-reduce + COD summarization
│  └─ utils/                # Utility modules
│     ├─ config.py          # Pydantic settings management
│     ├─ logging.py         # Structured logging setup
│     ├─ fsio.py            # File system operations
│     ├─ jobs.py            # Job management
│     ├─ cache.py           # Caching utilities
│     ├─ security.py        # Security utilities
│     ├─ validation.py      # Input validation (video/audio/transcript)
│     └─ exceptions.py      # Custom exceptions
├─ cli/app.py               # Typer CLI interface
├─ electron/                # Electron GUI application
│  ├─ main.js               # Electron main process
│  ├─ index.html            # GUI interface
│  └─ preload.js            # Preload script
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

- **Workflow Engine** (`core.workflow`): Flexible pipeline supporting video/audio/transcript inputs
- **Audio/Video Processing** (`core.audio.ffmpeg_ops`): FFmpeg-based operations including:
  - Video to audio extraction with quality settings
  - Audio normalization and volume adjustment
  - Format conversion (m4a, mp3, wav, flac, ogg)
  - Video metadata extraction
- **Audio Selection** (`core.audio.selection`): Intelligently selects highest quality audio from directories
- **Transcription Pipeline** (`core.transcribe.pipeline`): Replicate API integration with progress tracking
- **Summarization Pipeline** (`core.summarize.pipeline`): Map-reduce chunking + Chain-of-Density refinement
- **LLM Providers** (`core.providers`): Unified interface for OpenAI and Anthropic APIs
- **Configuration** (`core.utils.config`): Pydantic-based settings with environment variable support
- **Job Management** (`core.utils.jobs`): State persistence and progress tracking
- **Validation** (`core.utils.validation`): Input validation for video, audio, and transcript files

### Data Models

- `TranscriptWord`: Individual word with timing and confidence
- `TranscriptSegment`: Text segment with speaker attribution and word-level timing
- `TranscriptData`: Complete transcript with metadata
- `SummaryData`: Structured summary with sections and metadata
- `WorkflowConfig`: Configuration for flexible workflow execution
- `WorkflowStep`: Individual workflow step with conditional execution
- `JobData`: Job state tracking for long-running operations

## Supported File Formats

### Audio Formats
Ranked by preference: `.m4a`, `.flac`, `.wav`, `.mka`, `.ogg`, `.mp3`, `.webm`

### Video Formats
Supported: `.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`

### Transcript Formats
Supported: `.json`, `.txt`

The tool automatically detects file type and adjusts the workflow accordingly:
- **Video files**: Extract audio → Process → Transcribe → Summarize
- **Audio files**: Process → Transcribe → Summarize
- **Transcript files**: Summarize only

## Development

### Code Quality Tools
```bash
# Type checking
mypy core/ cli/

# Linting
ruff check .

# Testing
python -m pytest tests/
```

### Entry Points
- `summeets` command maps to `main:main` function
- Both CLI and Electron GUI share the same core processing logic
- Configuration is centralized through Pydantic settings
- GUI runs via `python main.py gui` (launches Electron app)
- Windows compatibility: Uses `npm.cmd` with `shell=True` for proper execution