$ErrorActionPreference = "Stop"

Write-Host "Setting up Summeets development environment..." -ForegroundColor Cyan

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
python -V
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python not found. Please install Python 3.11 or later." -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv .venv

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install package in editable mode
Write-Host "Installing summeets in editable mode..." -ForegroundColor Yellow
python -m pip install -e .

# Check ffmpeg/ffprobe availability
Write-Host "Checking ffmpeg installation..." -ForegroundColor Yellow
try {
    ffmpeg -version | Out-Null
    Write-Host "✓ ffmpeg found" -ForegroundColor Green
} catch {
    Write-Host "⚠ ffmpeg not found. Audio processing features will be limited." -ForegroundColor Yellow
    Write-Host "  Install from: https://ffmpeg.org/download.html" -ForegroundColor Yellow
}

try {
    ffprobe -version | Out-Null
    Write-Host "✓ ffprobe found" -ForegroundColor Green
} catch {
    Write-Host "⚠ ffprobe not found. Audio probing features will be limited." -ForegroundColor Yellow
}

Write-Host "`n✅ Summeets installed successfully!" -ForegroundColor Green
Write-Host "`nAvailable commands:" -ForegroundColor Cyan
Write-Host "  CLI: summeets --help" -ForegroundColor White
Write-Host "  GUI: summeets-gui" -ForegroundColor White
Write-Host "`nMake sure to set up your .env file with API keys!" -ForegroundColor Yellow