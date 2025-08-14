# Summeets

## What this does

Production-grade monorepo for transcribing and summarizing meetings with speaker diarization. Single processing core exposed via CLI and GUI interfaces:

* **Audio Processing**: FFmpeg-based normalization, extraction, and format conversion
* **Transcription**: Replicate's `thomasmol/whisper-diarization` (Whisper v3 + Pyannote) for speaker-aware transcription
* **Summarization**: Map-reduce + Chain-of-Density summarization with OpenAI GPT-4o or Anthropic Claude
* **Dual Interface**: Full-featured CLI (`summeets`) and GUI (`summeets gui`) sharing the same core
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
```

#### Individual Steps
```bash
# 1. Transcribe audio
summeets transcribe /path/to/audio.m4a
# → Creates out/audio.json (or data/output/ if using DataManager)

# 2. Summarize transcript
summeets summarize out/audio.json --provider openai --model gpt-4o

# 3. View configuration
summeets config
```


### GUI Interface

Launch the GUI with:
```bash
summeets gui
# or
python main.py gui
# or (default behavior)
python main.py
```

The GUI provides an intuitive interface for:
- Audio normalization and extraction
- Interactive transcription with progress tracking
- Summarization with provider selection
- Real-time status updates

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
│  ├─ audio/ffmpeg_ops.py   # Audio processing
│  ├─ providers/            # LLM clients (OpenAI, Anthropic)
│  ├─ transcribe/pipeline.py # Transcription logic
│  └─ summarize/pipeline.py  # Summarization logic
├─ cli/app.py               # Typer CLI interface
├─ gui/app.py               # tkinter GUI interface
├─ data/                    # Organized data storage
│  ├─ input/                # Input files (by date)
│  ├─ output/               # Processing results (by date/type)
│  ├─ temp/                 # Temporary files
│  └─ jobs/                 # Job state persistence
├─ tests/                   # Comprehensive test suite
├─ scripts/win_dev.ps1      # Development setup
└─ pyproject.toml           # Package definition
```

### Processing Pipeline

1. **Audio Selection**: Intelligently picks best quality audio from directories
2. **Format Optimization**: Converts to optimal format (16kHz mono) using FFmpeg
3. **Transcription**: Replicate's Whisper + Pyannote for speaker-aware transcription
4. **Chunking**: Time-based segmentation for large transcripts
5. **Map-Reduce**: Parallel summarization across chunks
6. **Chain-of-Density**: Iterative refinement for concise summaries

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
mypy core/ cli/ gui/

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
