# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based audio transcription tool that uses Replicate's Whisper + diarization model to transcribe and identify speakers in audio files. The tool:

- Prompts for a single path (file or folder) with no additional configuration
- Auto-selects the best quality audio file from supported formats
- Converts audio to 16kHz mono (if ffmpeg is available) for optimal transcription
- Uses Replicate's `thomasmol/whisper-diarization` model for speaker detection
- Outputs transcriptions in JSON, TXT, and SRT formats

## Dependencies

The project requires these Python packages (install manually):
- `replicate` - For Replicate API calls
- `python-dotenv` - For loading environment variables
- `tenacity` - For retry logic
- `alive-progress` - For live progress indicators

External dependencies:
- `ffmpeg` and `ffprobe` (optional but recommended) - For audio conversion and analysis

## Environment Setup

1. Create a `.env` file with your Replicate API token:
   ```
   REPLICATE_API_TOKEN=your_token_here
   ```

2. Install dependencies:
   ```bash
   pip install replicate python-dotenv tenacity alive-progress
   ```

3. Optionally install ffmpeg for better audio processing

## Running the Tool

Execute the main script:
```bash
python meeting_transcribe.py
```

The tool will prompt for an audio file or folder path and automatically handle the rest.

## Code Architecture

### Core Components

- **Audio Selection Logic** (`pick_best_audio`): Intelligently selects the highest quality audio from a folder based on bitrate, sample rate, and file format preferences
- **Audio Processing** (`ensure_wav16k_mono`): Converts audio to optimal format using ffmpeg
- **Replicate Integration** (`replicate_predict`): Handles API calls with live progress tracking and retry logic
- **Output Generation**: Creates JSON (detailed), TXT (speaker-labeled), and SRT (subtitle) formats

### Data Models

- `Word`: Individual word with timing
- `Segment`: Text segment with speaker attribution and word-level timing

### File Structure

- `meeting_transcribe.py` - Main script containing all functionality
- `audio_files/` - Contains sample audio files in various formats
- `out/` - Output directory for transcriptions (auto-created)
- `.env` - Environment variables (not tracked in git)

## Supported Audio Formats

Ranked by preference: `.m4a`, `.flac`, `.wav`, `.mka`, `.ogg`, `.mp3`, `.webm`

The tool automatically prioritizes "normalized" files and selects based on audio quality metrics.