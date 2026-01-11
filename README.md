# Summeets

## What this does

Production-grade monorepo for transcribing and summarizing meetings with speaker diarization. Single processing core exposed via CLI and TUI interfaces:

* **Audio Processing**: FFmpeg-based normalization, extraction, and format conversion
* **Transcription**: Replicate's `thomasmol/whisper-diarization` (Whisper v3 + Pyannote) for speaker-aware transcription
* **Summarization**: Map-reduce + Chain-of-Density summarization with OpenAI GPT-4o or Anthropic Claude, multiple templates for different meeting types
* **Dual Interface**: Full-featured CLI (`summeets`) and Textual TUI (`summeets tui`) sharing the same core
* **Production Ready**: Structured logging, configuration management, error handling

### Model Support

* **OpenAI**: GPT-4o models with Structured Outputs via `response_format: json_schema` ([OpenAI Platform](https://platform.openai.com/docs/guides/structured-outputs "Structured model outputs - OpenAI API"))
* **Anthropic**: Claude models with dated IDs like `claude-3-5-sonnet-20241022` ([Anthropic](https://docs.anthropic.com/en/api/messages-examples "Messages examples"))
* **Replicate**: Whisper + diarization via official Python client ([Replicate](https://replicate.com/docs/get-started/python "Run a model from Python"), [GitHub](https://github.com/replicate/replicate-python "Python client for Replicate"))

### FFmpeg Operations

Audio processing using FFmpeg's documented features:
* **Loudness normalization**: EBU R128 via `loudnorm` filter ([FFmpeg Filters](https://ffmpeg.org/ffmpeg-filters.html "FFmpeg Filters Documentation"))
* **Stream extraction**: `-map`, `-vn`, `-c:a copy` for lossless extraction ([FFmpeg](https://ffmpeg.org/ffmpeg.html "ffmpeg Documentation"))
* **Codec options**: AAC with `-b:a`, MP3 with `libmp3lame -q:a` for VBR ([FFmpeg Codecs](https://ffmpeg.org/ffmpeg-codecs.html "FFmpeg Codecs Documentation"))

---

## Quick start

### 1) Requirements

* **Python 3.11+**
* **FFmpeg** (optional but recommended) with `ffmpeg` and `ffprobe` binaries
* **API Keys**: At least one of:
  * OpenAI API key for GPT-4o summarization
  * Anthropic API key for Claude summarization
  * Replicate API token for transcription

### 2) Install

#### Windows (PowerShell)
```powershell
# Quick setup
.\scripts\win_dev.ps1

# Or manual setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

#### Linux/Mac
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3) Configuration

Create a `.env` file with your API keys:
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
SUMMARY_TEMPLATE=default            # default|sop|decision|brainstorm
SUMMARY_AUTO_DETECT_TEMPLATE=true   # Auto-detect template from content
SUMMARY_CHUNK_SECONDS=1800
SUMMARY_COD_PASSES=2
```

## Usage

### CLI Interface

The `summeets` CLI provides access to all core functionality:

#### Complete Pipeline
```bash
# Process audio file end-to-end (transcribe + summarize)
summeets process /path/to/meeting.m4a

# With specific provider/model
summeets process /path/to/meeting.m4a --provider anthropic --model claude-3-5-sonnet-20241022

# With specific template (auto-detection also works)
summeets process /path/to/training.m4a --template sop
```

#### Individual Steps
```bash
# 1. Transcribe audio
summeets transcribe /path/to/audio.m4a
# → Creates out/audio.json (or data/output/ if using DataManager)

# 2. Summarize transcript
summeets summarize out/audio.json --provider openai --model gpt-4o

# 2a. With specific template
summeets summarize out/audio.json --template sop
summeets summarize out/audio.json --template decision --no-auto-detect

# 2b. List available templates
summeets templates

# 3. View configuration
summeets config
```

### Summary Templates

Summeets supports multiple summary templates optimized for different meeting types:

| Template | Description | Best For |
|----------|-------------|----------|
| **default** | Comprehensive summary for general meetings | Status updates, discussions, regular meetings |
| **sop** | Standard Operating Procedure documentation | Training sessions, process walkthroughs, tutorials |
| **decision** | Focus on decisions and their rationale | Strategy meetings, decision-making sessions |
| **brainstorm** | Capture and organize creative ideas | Brainstorming sessions, idea generation |

#### SOP Template Features
The SOP template is specifically designed for process documentation and includes:
- **Step-by-step instructions** extracted from the meeting
- **File references** with locations and purposes  
- **System requirements** and prerequisites
- **Troubleshooting** common issues mentioned
- **Additional resources** and reference materials

Perfect for creating comprehensive guides from training recordings.

#### Auto-Detection
Summeets can automatically detect the meeting type based on content keywords:
- Process indicators: "step by step", "how to", "configure", "setup"
- Decision indicators: "decide", "choose", "vote", "recommendation"  
- Brainstorm indicators: "idea", "creative", "what if", "possibility"

Use `--auto-detect` (default) to enable or `--no-auto-detect` to force a specific template.

### TUI Interface

Launch the Textual-based TUI with:
```bash
summeets tui
```

The TUI provides:
- **Terminal-based graphical interface** with keyboard navigation
- **Workflow automation** for video/audio/transcript processing
- **Real-time progress tracking**
- **Interactive file selection**

### Configuration

View current settings:
```bash
summeets config
```

The configuration shows current LLM provider settings, output directories, and FFmpeg binary paths.

## Architecture

### Clean Architecture
```
summeets/
├─ core/                    # Shared processing core
│  ├─ models.py             # Data models & job tracking
│  ├─ config.py             # Pydantic settings
│  ├─ logging.py            # Structured logging
│  ├─ fsio.py               # File system operations
│  ├─ jobs.py               # Job management
│  ├─ workflow.py           # Workflow engine for multi-step processing
│  ├─ audio/                # Audio processing
│  │  ├─ ffmpeg_ops.py      # FFmpeg operations
│  │  ├─ selection.py       # Audio file selection logic
│  │  └─ compression.py     # Audio compression utilities
│  ├─ providers/            # LLM clients (OpenAI, Anthropic)
│  ├─ transcribe/pipeline.py # Transcription logic
│  ├─ summarize/pipeline.py  # Summarization logic
│  └─ utils/                # Reorganized utilities
│     ├─ file_utils.py      # File operations
│     ├─ text_utils.py      # Text processing
│     └─ validation.py      # Input validation
├─ cli/app.py               # Typer CLI interface
├─ archive/                 # Deprecated components
│  └─ electron_gui/         # Legacy Electron GUI (deprecated)
├─ data/                    # Organized data storage
│  ├─ input/                # Input files (by date)
│  ├─ output/               # Processing results (by date/type)
│  ├─ temp/                 # Temporary files
│  └─ jobs/                 # Job state persistence
├─ tests/                   # Comprehensive test suite
├─ scripts/win_dev.ps1      # Development setup
└─ pyproject.toml           # Python package definition
```

### Processing Pipeline

1. **Input Detection**: Automatically identifies file type (video/audio/transcript)
2. **Workflow Engine**: Conditionally executes appropriate processing steps
3. **Audio Extraction**: FFmpeg extracts audio from video if needed
4. **Format Optimization**: Converts to optimal format (16kHz mono) using FFmpeg
5. **Transcription**: Replicate's Whisper + Pyannote for speaker-aware transcription
6. **Chunking**: Time-based segmentation for large transcripts
7. **Map-Reduce**: Parallel summarization across chunks
8. **Chain-of-Density**: Iterative refinement for concise summaries

### Output Files

All outputs are saved to the `out/` directory:

* `<basename>.json` — Raw transcript with speaker labels and word timing
* `<basename>.summary.json` — Structured summary with metadata
* `<basename>.summary.md` — Human-readable summary
* `logs/summeets_*.log` — Detailed processing logs

## Project Evolution

This project evolved from a simple transcription script into a production-grade monorepo with:
- **Modular architecture** with separated concerns
- **Dual interfaces** (CLI/GUI) sharing the same core
- **Multiple LLM providers** with consistent APIs
- **Production features** like structured logging and configuration management

## Troubleshooting

### Common Issues

* **Missing API Keys**: Ensure `.env` file contains valid API keys for your chosen provider
* **FFmpeg Not Found**: Install FFmpeg or set `ffmpeg_bin`/`ffprobe_bin` paths in config
* **Replicate Upload Errors**: Audio compression happens automatically to fit upload limits
* **Model Errors**: Use exact model names (e.g., `claude-3-5-sonnet-20241022` not `claude-sonnet`)
* **TUI Won't Start**:
  - Ensure `textual` is installed: `pip install textual`
  - Check terminal supports ANSI colors and Unicode

### Advanced Configuration

Environment variables for fine-tuning:
* `MAX_UPLOAD_MB=24` — Audio compression target size
* `SUMMARY_CHUNK_SECONDS=1800` — Summarization chunk size 
* `SUMMARY_COD_PASSES=2` — Chain-of-Density refinement passes

### Performance Tips

* Use SSD storage for faster audio processing
* Larger chunks (3600s) for longer meetings
* OpenAI GPT-4o-mini for cost-effective summarization
* Anthropic Claude for better reasoning on complex content

## Development

### Setup Development Environment

```bash
# Windows
.\scripts\win_dev.ps1

# Manual setup
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

### Code Quality

```bash
# Type checking
mypy core/ cli/

# Linting
ruff check .

# Testing
python -m pytest tests/
```

### Contributing

1. Fork and clone the repository
2. Create a feature branch
3. Make your changes with proper type hints and documentation
4. Add tests for new functionality
5. Ensure all checks pass
6. Submit a pull request

## License

MIT License - see LICENSE file for details.
