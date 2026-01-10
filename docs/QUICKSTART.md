# Summeets Quick Start Guide

## Prerequisites

### 1. Installation
```bash
# Install the package
pip install -e .

# Verify installation
summeets --help
```

### 2. API Keys Setup
Create `.env` file in project root:
```env
# Required: Choose your LLM provider
LLM_PROVIDER=openai                    # or "anthropic"
LLM_MODEL=gpt-4o-mini                  # or "claude-3-5-sonnet-20241022"

# API Keys (at least one required)
OPENAI_API_KEY=sk-proj-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
REPLICATE_API_TOKEN=r8_your-token-here

# Optional: Email configuration for sending summaries
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 3. External Dependencies
```bash
# FFmpeg (required for video processing)
# Windows: Download from https://ffmpeg.org/download.html
# Mac: brew install ffmpeg
# Linux: apt-get install ffmpeg

# Verify FFmpeg installation
ffmpeg -version
```

## Processing a Video

### Complete Pipeline (One Command)
```bash
# Process video → extract audio → transcribe → summarize
summeets process "path/to/video.mkv"

# With specific provider and model
summeets process "video.mkv" --provider openai --model gpt-4o-mini

# With custom output directory
summeets process "video.mkv" --output-dir "custom/output/path"

# With specific summary template
summeets process "video.mkv" --template requirements
```

### Step-by-Step Pipeline

#### Step 1: Extract Audio from Video
```bash
summeets extract "video.mkv" "output.m4a" --codec aac --quality high
```

#### Step 2: Transcribe Audio
```bash
summeets transcribe "output.m4a"
# Creates: data/transcript/output/output.json
```

#### Step 3: Summarize Transcript
```bash
summeets summarize "data/transcript/output/output.json" \
  --provider openai \
  --model gpt-4o-mini
# Creates: data/summary/output/requirements/output.summary.md
```

## Output Structure

After processing, files are organized as:
```
data/
├── audio/
│   └── {filename}/
│       └── {filename}.m4a
├── transcript/
│   └── {filename}/
│       ├── {filename}.json       # Structured transcript
│       ├── {filename}.txt        # Plain text
│       └── {filename}.srt        # Subtitle format
└── summary/
    └── {filename}/
        └── requirements/
            ├── {filename}.summary.json
            └── {filename}.summary.md
```

## Sending Summary via Email

### Method 1: Using Python Script
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

def send_summary_email(summary_path: str, recipient: str):
    """Send summary file via email."""

    # Read summary
    summary_content = Path(summary_path).read_text(encoding='utf-8')

    # Email setup
    msg = MIMEMultipart()
    msg['From'] = os.getenv('SMTP_USERNAME')
    msg['To'] = recipient
    msg['Subject'] = f"Meeting Summary: {Path(summary_path).stem}"

    # Attach summary
    msg.attach(MIMEText(summary_content, 'plain'))

    # Send email
    with smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) as server:
        server.starttls()
        server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))
        server.send_message(msg)

    print(f"✓ Summary sent to {recipient}")

# Usage
send_summary_email(
    "data/summary/video/requirements/video.summary.md",
    "recipient@example.com"
)
```

### Method 2: Using CLI Email Tool (Future Enhancement)
```bash
# Not yet implemented - requires new command
summeets email-summary "data/summary/video/requirements/video.summary.md" \
  --to "recipient@example.com" \
  --subject "Meeting Summary"
```

## Common Workflows

### 1. Quick Meeting Summary
```bash
# Record meeting → Save as video.mkv → Run:
summeets process "video.mkv" --provider openai --model gpt-4o-mini
```

### 2. Batch Processing Multiple Videos
```bash
# Process all videos in directory
for video in data/video/*.mkv; do
  summeets process "$video" --provider openai --model gpt-4o-mini
done
```

### 3. Audio-Only Processing
```bash
# If you already have audio file
summeets transcribe "audio.m4a"
summeets summarize "data/transcript/audio/audio.json"
```

### 4. Re-summarize with Different Template
```bash
# Use existing transcript, new summary
summeets process "data/transcript/video/video.json" --template action-items
```

## Supported File Formats

### Video Formats
`.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`

### Audio Formats
`.m4a`, `.flac`, `.wav`, `.mka`, `.ogg`, `.mp3`, `.webm`

### Transcript Formats
`.json`, `.txt`

## Troubleshooting

### FFmpeg Not Found
```bash
# Manually set FFmpeg path in .env
FFMPEG_BIN=/path/to/ffmpeg
FFPROBE_BIN=/path/to/ffprobe
```

### API Key Errors
```bash
# Verify API keys are loaded
summeets config

# Test with environment variable
export OPENAI_API_KEY="sk-proj-..."
summeets process "video.mkv" --provider openai
```

### Out of Credits Error
```bash
# Switch provider if one runs out of credits
summeets process "video.mkv" --provider anthropic  # instead of openai
```

### Unicode Encoding Errors (Windows)
```bash
# Use PowerShell with UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
summeets process "video.mkv"
```

## Advanced Options

### Custom Audio Quality
```bash
summeets process "video.mkv" \
  --audio-format flac \
  --audio-quality high \
  --normalize
```

### Skip Steps in Pipeline
```bash
# Only transcribe (skip summarization)
summeets transcribe "video.mkv"

# Only summarize (skip transcription)
summeets summarize "existing_transcript.json"
```

### View Configuration
```bash
# Show current settings
summeets config

# Validate video file
summeets probe "video.mkv"
```

## Performance Tips

1. **Use M4A format** (default) - Best balance of quality and size
2. **Enable normalization** (default) - Improves transcription accuracy
3. **Use gpt-4o-mini** - Faster and cheaper than gpt-4o
4. **Batch process overnight** - For multiple long videos
5. **Keep original videos** - Compressed audio is stored separately

## Example: Complete Workflow

```bash
# 1. Process the video
summeets process "meeting.mkv" --provider openai --model gpt-4o-mini

# 2. Verify outputs
ls data/audio/meeting/          # → meeting.m4a
ls data/transcript/meeting/     # → meeting.json, meeting.txt, meeting.srt
ls data/summary/meeting/        # → requirements/meeting.summary.md

# 3. Review summary
cat data/summary/meeting/requirements/meeting.summary.md

# 4. Send via email (using Python script above)
python send_summary.py \
  --summary "data/summary/meeting/requirements/meeting.summary.md" \
  --to "team@example.com"
```

## Next Steps

- Customize summary templates in `core/summarize/templates.py`
- Add email sending command to CLI
- Integrate with calendar for automatic meeting processing
- Set up scheduled batch processing for recorded meetings
