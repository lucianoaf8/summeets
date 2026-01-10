# Summeets GUI Automation Test Script
# PowerShell script to automate end-to-end testing of the Electron GUI

param(
    [string]$TestVideoFile = "C:\Projects\summeets\data\video\video_for_testing.mp4",
    [string]$ProjectRoot = "C:\Projects\summeets",
    [int]$TimeoutMinutes = 15,
    [switch]$KeepGUIOpen,
    [switch]$Verbose
)

# Set up error handling and logging
$ErrorActionPreference = "Stop"
$VerbosePreference = if ($Verbose) { "Continue" } else { "SilentlyContinue" }

# Test configuration
$TestConfig = @{
    VideoFile = $TestVideoFile
    ProjectRoot = $ProjectRoot
    TimeoutSeconds = $TimeoutMinutes * 60
    OutputDir = Join-Path $ProjectRoot "data"
    LogFile = Join-Path $ProjectRoot "test-automation.log"
    ExpectedOutputs = @("audio", "transcript", "summary")
}

# Initialize logging
function Write-TestLog {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Write-Host $logEntry
    Add-Content -Path $TestConfig.LogFile -Value $logEntry
}

# Clean up previous test artifacts
function Clear-TestArtifacts {
    Write-TestLog "Cleaning up previous test artifacts..."
    
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($TestConfig.VideoFile)
    $cleanupPaths = @(
        (Join-Path $TestConfig.OutputDir "audio\$baseName"),
        (Join-Path $TestConfig.OutputDir "transcript\$baseName"),
        (Join-Path $TestConfig.OutputDir "temp"),
        $TestConfig.LogFile
    )
    
    foreach ($path in $cleanupPaths) {
        if (Test-Path $path) {
            Remove-Item $path -Recurse -Force
            Write-TestLog "Removed: $path"
        }
    }
}

# Launch GUI application
function Start-SummeetsGUI {
    Write-TestLog "Launching Summeets GUI application..."
    
    # Change to project directory
    Set-Location $TestConfig.ProjectRoot
    
    # Verify test video file exists
    if (-not (Test-Path $TestConfig.VideoFile)) {
        throw "Test video file not found: $($TestConfig.VideoFile)"
    }
    
    # Launch the GUI application
    $guiProcess = Start-Process -FilePath "python" -ArgumentList "main.py", "gui" -PassThru -NoNewWindow
    
    if (-not $guiProcess) {
        throw "Failed to start GUI application"
    }
    
    Write-TestLog "GUI process started with PID: $($guiProcess.Id)"
    
    # Wait for GUI to initialize
    Write-TestLog "Waiting for GUI to initialize..."
    Start-Sleep -Seconds 5
    
    return $guiProcess
}

# Monitor process output and logs
function Monitor-ProcessingWorkflow {
    param([int]$TimeoutSeconds)
    
    Write-TestLog "Monitoring workflow processing..."
    $startTime = Get-Date
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($TestConfig.VideoFile)
    
    # Define expected output files
    $expectedFiles = @{
        "Audio" = Join-Path $TestConfig.OutputDir "audio\$baseName\$baseName.m4a"
        "Transcript" = Join-Path $TestConfig.OutputDir "transcript\$baseName\$baseName.json"
        "Summary" = Join-Path $TestConfig.OutputDir "transcript\$baseName\$baseName.summary.md"
    }
    
    $completedSteps = @()
    
    while (((Get-Date) - $startTime).TotalSeconds -lt $TimeoutSeconds) {
        # Check for each expected output file
        foreach ($stepName in $expectedFiles.Keys) {
            $filePath = $expectedFiles[$stepName]
            
            if ((Test-Path $filePath) -and ($stepName -notin $completedSteps)) {
                $fileSize = (Get-Item $filePath).Length
                Write-TestLog "✓ $stepName completed - File: $filePath (Size: $fileSize bytes)" "SUCCESS"
                $completedSteps += $stepName
            }
        }
        
        # Check if all steps are completed
        if ($completedSteps.Count -eq $expectedFiles.Count) {
            Write-TestLog "All workflow steps completed successfully!" "SUCCESS"
            return $true
        }
        
        # Progress update
        if (((Get-Date) - $startTime).TotalSeconds % 30 -lt 1) {
            $elapsed = [int]((Get-Date) - $startTime).TotalSeconds
            Write-TestLog "Processing... Elapsed: ${elapsed}s, Completed: $($completedSteps -join ', ')"
        }
        
        Start-Sleep -Seconds 2
    }
    
    # Timeout reached
    Write-TestLog "Workflow monitoring timed out after $TimeoutSeconds seconds" "ERROR"
    return $false
}

# Validate workflow outputs
function Test-WorkflowOutputs {
    Write-TestLog "Validating workflow outputs..."
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($TestConfig.VideoFile)
    $validationResults = @{}
    
    # Test audio file
    $audioFile = Join-Path $TestConfig.OutputDir "audio\$baseName\$baseName.m4a"
    if (Test-Path $audioFile) {
        $audioSize = (Get-Item $audioFile).Length
        $validationResults["Audio"] = @{
            "Exists" = $true
            "Size" = $audioSize
            "Valid" = $audioSize -gt 1000  # Minimum 1KB
        }
        Write-TestLog "Audio file validation: Size=$audioSize bytes, Valid=$($validationResults.Audio.Valid)"
    } else {
        $validationResults["Audio"] = @{ "Exists" = $false; "Valid" = $false }
        Write-TestLog "Audio file not found" "ERROR"
    }
    
    # Test transcript file
    $transcriptFile = Join-Path $TestConfig.OutputDir "transcript\$baseName\$baseName.json"
    if (Test-Path $transcriptFile) {
        $transcriptContent = Get-Content $transcriptFile -Raw
        $transcriptSize = $transcriptContent.Length
        $isValidJson = $false
        
        try {
            $transcriptData = $transcriptContent | ConvertFrom-Json
            $isValidJson = $true
            $hasSegments = $transcriptData.segments -and $transcriptData.segments.Count -gt 0
        } catch {
            $hasSegments = $false
        }
        
        $validationResults["Transcript"] = @{
            "Exists" = $true
            "Size" = $transcriptSize
            "ValidJSON" = $isValidJson
            "HasSegments" = $hasSegments
            "Valid" = $isValidJson -and $hasSegments
        }
        Write-TestLog "Transcript validation: Size=$transcriptSize, JSON=$isValidJson, Segments=$hasSegments"
    } else {
        $validationResults["Transcript"] = @{ "Exists" = $false; "Valid" = $false }
        Write-TestLog "Transcript file not found" "ERROR"
    }
    
    # Test summary file
    $summaryFile = Join-Path $TestConfig.OutputDir "transcript\$baseName\$summaryFileName"
    $summaryFound = $false
    $summaryPatterns = @("*.summary.md", "*.summary.json", "*summary*")
    
    foreach ($pattern in $summaryPatterns) {
        $summaryFiles = Get-ChildItem -Path (Join-Path $TestConfig.OutputDir "transcript\$baseName") -Filter $pattern -ErrorAction SilentlyContinue
        if ($summaryFiles) {
            $summaryFile = $summaryFiles[0].FullName
            $summaryFound = $true
            break
        }
    }
    
    if ($summaryFound) {
        $summarySize = (Get-Item $summaryFile).Length
        $summaryContent = Get-Content $summaryFile -Raw
        $hasContent = $summaryContent -and $summaryContent.Length -gt 100
        
        $validationResults["Summary"] = @{
            "Exists" = $true
            "Size" = $summarySize
            "HasContent" = $hasContent
            "Valid" = $hasContent
        }
        Write-TestLog "Summary validation: File=$summaryFile, Size=$summarySize, HasContent=$hasContent"
    } else {
        $validationResults["Summary"] = @{ "Exists" = $false; "Valid" = $false }
        Write-TestLog "Summary file not found" "ERROR"
    }
    
    return $validationResults
}

# Simulate GUI interactions (alternative approach using file system automation)
function Invoke-GUIAutomation {
    Write-TestLog "Setting up GUI automation via file system approach..."
    
    # Create a test configuration file that the GUI can detect
    $autoTestConfig = @{
        "autoTest" = $true
        "testFile" = $TestConfig.VideoFile
        "testMode" = "full-workflow"
        "timestamp" = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }
    
    $configFile = Join-Path $TestConfig.ProjectRoot "auto-test-config.json"
    $autoTestConfig | ConvertTo-Json | Set-Content $configFile
    
    Write-TestLog "Created auto-test configuration: $configFile"
    
    # For now, we'll rely on the user to manually select the file and start processing
    # In a full implementation, we would use tools like:
    # - Windows UI Automation (UIA)
    # - Selenium WebDriver for Electron
    # - Playwright with Electron support
    # - Direct Electron testing APIs
    
    Write-TestLog "GUI automation setup complete. Manual interaction required:"
    Write-TestLog "1. Select video file: $($TestConfig.VideoFile)"
    Write-TestLog "2. Ensure all workflow steps are enabled"
    Write-TestLog "3. Click 'Start Processing' button"
    Write-TestLog "4. Switch to 'Processing' tab to monitor progress"
}

# Generate test report
function Write-TestReport {
    param([hashtable]$ValidationResults, [bool]$WorkflowCompleted, [timespan]$Duration)
    
    $reportFile = Join-Path $TestConfig.ProjectRoot "test-report-$(Get-Date -Format 'yyyyMMdd-HHmmss').md"
    
    $report = @"
# Summeets GUI Automation Test Report

**Test Date:** $(Get-Date)
**Duration:** $($Duration.ToString('hh\:mm\:ss'))
**Test Video:** $($TestConfig.VideoFile)
**Workflow Completed:** $WorkflowCompleted

## Test Results Summary

| Component | Status | Details |
|-----------|--------|---------|
| Audio Extraction | $($ValidationResults.Audio.Valid ? "✅ PASS" : "❌ FAIL") | Size: $($ValidationResults.Audio.Size) bytes |
| Transcription | $($ValidationResults.Transcript.Valid ? "✅ PASS" : "❌ FAIL") | JSON Valid: $($ValidationResults.Transcript.ValidJSON), Has Segments: $($ValidationResults.Transcript.HasSegments) |
| Summarization | $($ValidationResults.Summary.Valid ? "✅ PASS" : "❌ FAIL") | Has Content: $($ValidationResults.Summary.HasContent) |

## Workflow Steps

- **File Selection:** Manual (GUI interaction required)
- **Audio Extraction:** $($ValidationResults.Audio.Valid ? "Completed" : "Failed")
- **Audio Processing:** $($ValidationResults.Audio.Valid ? "Completed" : "Failed")
- **Transcription:** $($ValidationResults.Transcript.Valid ? "Completed" : "Failed")
- **Summarization:** $($ValidationResults.Summary.Valid ? "Completed" : "Failed")

## Output Files

- **Audio:** $(Join-Path $TestConfig.OutputDir "audio\$baseName")
- **Transcript:** $(Join-Path $TestConfig.OutputDir "transcript\$baseName")
- **Logs:** $($TestConfig.LogFile)

## Recommendations

$( if (-not $WorkflowCompleted) { "- Workflow did not complete within timeout period. Consider increasing timeout or checking for errors." } )
$( if (-not $ValidationResults.Audio.Valid) { "- Audio extraction failed. Check FFmpeg installation and video file format." } )
$( if (-not $ValidationResults.Transcript.Valid) { "- Transcription failed. Verify Replicate API token and network connectivity." } )
$( if (-not $ValidationResults.Summary.Valid) { "- Summarization failed. Check LLM API configuration (OpenAI/Anthropic keys)." } )

---
*Generated by Summeets GUI Automation Test Script*
"@

    Set-Content $reportFile -Value $report
    Write-TestLog "Test report generated: $reportFile"
    
    return $reportFile
}

# Main test execution
function Invoke-GUITest {
    try {
        Write-TestLog "Starting Summeets GUI Automation Test" "INFO"
        Write-TestLog "================================================"
        
        $testStartTime = Get-Date
        
        # Step 1: Clean up previous test artifacts
        Clear-TestArtifacts
        
        # Step 2: Launch GUI application
        $guiProcess = Start-SummeetsGUI
        
        # Step 3: Set up GUI automation
        Invoke-GUIAutomation
        
        # Step 4: Wait for user to initiate processing
        Write-TestLog "Waiting for processing to begin..."
        Write-TestLog "Please select the test video file and click 'Start Processing' in the GUI"
        
        # Give user time to start the process
        Write-Host "`nPress ENTER after you have started the processing in the GUI..." -ForegroundColor Yellow
        Read-Host
        
        # Step 5: Monitor the workflow
        $workflowCompleted = Monitor-ProcessingWorkflow -TimeoutSeconds $TestConfig.TimeoutSeconds
        
        # Step 6: Validate outputs
        $validationResults = Test-WorkflowOutputs
        
        # Step 7: Calculate test duration
        $testDuration = (Get-Date) - $testStartTime
        
        # Step 8: Generate report
        $reportFile = Write-TestReport -ValidationResults $validationResults -WorkflowCompleted $workflowCompleted -Duration $testDuration
        
        # Step 9: Clean up GUI process
        if ($guiProcess -and -not $KeepGUIOpen) {
            Write-TestLog "Terminating GUI process..."
            Stop-Process -Id $guiProcess.Id -Force -ErrorAction SilentlyContinue
        }
        
        # Final results
        $allValid = $validationResults.Values | ForEach-Object { $_.Valid } | Where-Object { $_ -eq $false } | Measure-Object | Select-Object -ExpandProperty Count
        $testPassed = $workflowCompleted -and ($allValid -eq 0)
        
        Write-TestLog "================================================"
        Write-TestLog "TEST RESULT: $($testPassed ? "PASSED" : "FAILED")" ($testPassed ? "SUCCESS" : "ERROR")
        Write-TestLog "Duration: $($testDuration.ToString('hh\:mm\:ss'))"
        Write-TestLog "Report: $reportFile"
        
        return $testPassed
        
    } catch {
        Write-TestLog "Test execution failed: $($_.Exception.Message)" "ERROR"
        Write-TestLog $_.ScriptStackTrace "ERROR"
        return $false
    }
}

# Advanced automation functions for future implementation
function Install-AutomationDependencies {
    Write-TestLog "Installing automation dependencies..."
    
    # Future implementation could install:
    # - Playwright for Electron
    # - Windows UI Automation PowerShell modules
    # - Selenium WebDriver
    
    Write-TestLog "Automation dependencies would be installed here in full implementation"
}

function Invoke-AdvancedGUIAutomation {
    # Future implementation for full GUI automation
    # This would use tools like:
    # - Windows UI Automation to find and click GUI elements
    # - Playwright with Electron support
    # - Direct manipulation of Electron renderer process
    
    Write-TestLog "Advanced GUI automation would be implemented here"
    Write-TestLog "Current implementation requires manual GUI interaction"
}

# Script entry point
if ($MyInvocation.InvocationName -ne '.') {
    Write-Host "Summeets GUI Automation Test Script" -ForegroundColor Cyan
    Write-Host "=====================================" -ForegroundColor Cyan
    
    $testResult = Invoke-GUITest
    
    if ($testResult) {
        Write-Host "`nTEST PASSED ✅" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "`nTEST FAILED ❌" -ForegroundColor Red
        exit 1
    }
}