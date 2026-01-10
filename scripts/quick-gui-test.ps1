# Quick GUI Test Script - PowerShell
# Simple automation for testing Summeets GUI workflow

param(
    [string]$VideoFile = "C:\Projects\summeets\data\video\video_for_testing.mp4"
)

$ProjectRoot = "C:\Projects\summeets"
$LogFile = Join-Path $ProjectRoot "quick-test.log"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "HH:mm:ss"
    $logEntry = "[$timestamp] $Message"
    Write-Host $logEntry
    Add-Content -Path $LogFile -Value $logEntry
}

Write-Log "Starting Quick GUI Test"
Write-Log "Test video: $VideoFile"

# Change to project directory
Set-Location $ProjectRoot

# Verify video file exists
if (-not (Test-Path $VideoFile)) {
    Write-Log "ERROR: Video file not found: $VideoFile"
    exit 1
}

Write-Log "Launching GUI..."
# Launch GUI in background
$guiProcess = Start-Process -FilePath "python" -ArgumentList "main.py", "gui" -PassThru

Write-Log "GUI launched with PID: $($guiProcess.Id)"
Write-Log ""
Write-Log "MANUAL STEPS REQUIRED:"
Write-Log "1. Wait for GUI to load (5-10 seconds)"
Write-Log "2. Click the 'Video' button in the file selection area"
Write-Log "3. Select the test video file: $VideoFile"
Write-Log "4. Verify all workflow steps are enabled (Extract Audio, Process Audio, Transcribe, Summarize)"
Write-Log "5. Click 'Start Processing' button"
Write-Log "6. Click 'Processing' tab to monitor progress"
Write-Log ""

# Monitor for output files
$baseName = [System.IO.Path]::GetFileNameWithoutExtension($VideoFile)
$audioDir = Join-Path $ProjectRoot "data\audio\$baseName"
$transcriptDir = Join-Path $ProjectRoot "data\transcript\$baseName"

Write-Log "Monitoring for output files..."
Write-Log "Audio directory: $audioDir"
Write-Log "Transcript directory: $transcriptDir"

$startTime = Get-Date
$timeoutMinutes = 15
$found = @{}

while (((Get-Date) - $startTime).TotalMinutes -lt $timeoutMinutes) {
    # Check for audio file
    if ((Test-Path $audioDir) -and -not $found.Audio) {
        $audioFiles = Get-ChildItem $audioDir -Filter "*.m4a" -ErrorAction SilentlyContinue
        if ($audioFiles) {
            Write-Log "✅ Audio extraction completed: $($audioFiles[0].Name)"
            $found.Audio = $true
        }
    }
    
    # Check for transcript file
    if ((Test-Path $transcriptDir) -and -not $found.Transcript) {
        $transcriptFiles = Get-ChildItem $transcriptDir -Filter "*.json" -ErrorAction SilentlyContinue
        if ($transcriptFiles) {
            Write-Log "✅ Transcription completed: $($transcriptFiles[0].Name)"
            $found.Transcript = $true
        }
    }
    
    # Check for summary file
    if ((Test-Path $transcriptDir) -and -not $found.Summary) {
        $summaryFiles = Get-ChildItem $transcriptDir -Filter "*summary*" -ErrorAction SilentlyContinue
        if ($summaryFiles) {
            Write-Log "✅ Summarization completed: $($summaryFiles[0].Name)"
            $found.Summary = $true
        }
    }
    
    # Check if all steps completed
    if ($found.Count -eq 3) {
        Write-Log ""
        Write-Log "🎉 ALL WORKFLOW STEPS COMPLETED SUCCESSFULLY!"
        $duration = (Get-Date) - $startTime
        Write-Log "Total processing time: $($duration.ToString('mm\:ss'))"
        break
    }
    
    Start-Sleep -Seconds 5
}

if ($found.Count -lt 3) {
    Write-Log ""
    Write-Log "⚠️  Workflow did not complete within $timeoutMinutes minutes"
    Write-Log "Completed steps: $($found.Keys -join ', ')"
}

Write-Log ""
Write-Log "Test completed. Check the GUI Processing tab for detailed logs."
Write-Log "Press Enter to close GUI and exit..."
Read-Host

# Clean up
Stop-Process -Id $guiProcess.Id -Force -ErrorAction SilentlyContinue
Write-Log "GUI process terminated."