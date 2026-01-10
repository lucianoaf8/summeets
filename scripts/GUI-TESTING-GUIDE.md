# Summeets GUI Testing Guide

This document provides comprehensive instructions for automated testing of the Summeets Electron GUI application.

## Overview

The testing suite includes PowerShell scripts that automate the workflow testing process while requiring minimal manual interaction for the GUI components that cannot be fully automated without specialized tools.

## Test Scripts

### 1. `test-gui-automation.ps1` - Comprehensive Test Suite

**Purpose:** Full-featured automated testing with detailed reporting and validation.

**Features:**
- Complete workflow monitoring
- Output file validation
- Detailed test reporting
- Error handling and logging
- Configurable timeouts

**Usage:**
```powershell
# Basic usage
.\scripts\test-gui-automation.ps1

# With custom video file
.\scripts\test-gui-automation.ps1 -TestVideoFile "C:\path\to\video.mp4"

# Extended timeout and verbose logging
.\scripts\test-gui-automation.ps1 -TimeoutMinutes 20 -Verbose

# Keep GUI open after test
.\scripts\test-gui-automation.ps1 -KeepGUIOpen
```

### 2. `quick-gui-test.ps1` - Simple Test Runner

**Purpose:** Quick and simple testing for development workflows.

**Features:**
- Basic workflow monitoring
- Real-time progress updates
- Simple file system validation

**Usage:**
```powershell
.\scripts\quick-gui-test.ps1
```

### 3. `run-gui-test.bat` - Windows Batch Wrapper

**Purpose:** Easy execution from Windows command prompt or file explorer.

**Usage:**
- Double-click the batch file, or
- Run from command prompt: `scripts\run-gui-test.bat`

## Test Workflow

### Automated Steps
1. **Environment Setup**
   - Verify test video file exists
   - Clean up previous test artifacts
   - Initialize logging

2. **GUI Launch**
   - Start Electron application
   - Wait for initialization
   - Capture process ID for cleanup

3. **Workflow Monitoring**
   - Monitor file system for output files
   - Track progress through audio → transcript → summary
   - Validate file contents and formats

4. **Results Validation**
   - Verify audio extraction (file size, format)
   - Validate transcript JSON structure
   - Check summary content quality

5. **Reporting**
   - Generate detailed test report
   - Log all activities with timestamps
   - Provide recommendations for failures

### Manual Steps Required
Due to Electron GUI automation complexity, these steps require manual interaction:

1. **File Selection**
   - Click the "Video" button in file selection area
   - Navigate to and select the test video file
   - Confirm file is displayed in the selected file area

2. **Workflow Configuration**
   - Verify all workflow steps are enabled:
     - ✅ Extract Audio
     - ✅ Process Audio  
     - ✅ Transcribe
     - ✅ Summarize
   - Adjust settings if needed

3. **Process Initiation**
   - Click "Start Processing" button
   - Switch to "Processing" tab to monitor progress

## Test Configuration

### Default Settings
```powershell
$TestConfig = @{
    VideoFile = "C:\Projects\summeets\data\video\video_for_testing.mp4"
    ProjectRoot = "C:\Projects\summeets"
    TimeoutSeconds = 900  # 15 minutes
    OutputDir = "C:\Projects\summeets\data"
    ExpectedOutputs = @("audio", "transcript", "summary")
}
```

### Required Files
- **Test Video:** `data/video/video_for_testing.mp4` (58MB MP4 file)
- **Project Root:** `/mnt/c/Projects/summeets` (or `C:\Projects\summeets` on Windows)

## Output Validation

### Audio Files
- **Location:** `data/audio/{filename}/{filename}.m4a`
- **Validation:** File size > 1KB, valid audio format
- **Expected:** Extracted from source video with proper codec

### Transcript Files  
- **Location:** `data/transcript/{filename}/{filename}.json`
- **Validation:** Valid JSON structure with segments array
- **Expected:** Speaker-separated transcript with timestamps

### Summary Files
- **Location:** `data/transcript/{filename}/{filename}.summary.md`
- **Validation:** Content length > 100 characters
- **Expected:** Structured markdown summary with sections

## Error Handling

### Common Issues
1. **GUI Launch Failure**
   - Check Node.js and npm installation
   - Verify project dependencies: `npm install`
   - Ensure Python environment is activated

2. **File Selection Issues**
   - Verify test video file exists and is accessible
   - Check file permissions
   - Ensure correct file path format

3. **Processing Failures**
   - Check API key configuration (OpenAI, Anthropic, Replicate)
   - Verify network connectivity
   - Check system resources (disk space, memory)

4. **Timeout Issues**
   - Increase timeout for large video files
   - Check system performance
   - Monitor for hung processes

### Debugging Tips
1. Check `test-automation.log` for detailed execution logs
2. Monitor GUI "Processing" tab for real-time status
3. Verify API keys in Settings tab
4. Check Windows Event Viewer for system-level errors

## Advanced Automation (Future Implementation)

For full GUI automation without manual steps, consider implementing:

### Windows UI Automation
```powershell
# Example using UIA PowerShell modules
Add-Type -AssemblyName UIAutomationClient
$automation = [System.Windows.Automation.AutomationElement]::RootElement
```

### Playwright for Electron
```javascript
// Example Playwright + Electron automation
const { _electron: electron } = require('playwright');
const app = await electron.launch({ args: ['main.py', 'gui'] });
```

### Selenium WebDriver
```powershell
# Example WebDriver setup for Electron
$driver = New-Object OpenQA.Selenium.Chrome.ChromeDriver
$driver.Navigate().GoToUrl("file://app/index.html")
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: GUI Tests
on: [push, pull_request]
jobs:
  gui-test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          pip install -e .
          npm install
      - name: Run GUI tests
        run: .\scripts\test-gui-automation.ps1
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          REPLICATE_API_TOKEN: ${{ secrets.REPLICATE_API_TOKEN }}
```

## Test Reports

### Sample Report Structure
```markdown
# Summeets GUI Automation Test Report

**Test Date:** 2024-08-17 06:45:32
**Duration:** 00:12:45
**Test Video:** video_for_testing.mp4
**Workflow Completed:** True

## Test Results Summary
| Component | Status | Details |
|-----------|--------|---------|
| Audio Extraction | ✅ PASS | Size: 2,457,892 bytes |
| Transcription | ✅ PASS | JSON Valid: True, Has Segments: True |
| Summarization | ✅ PASS | Has Content: True |

## Recommendations
- All tests passed successfully
- Processing completed within expected timeframe
- No issues detected
```

## Troubleshooting

### PowerShell Execution Policy
If you encounter execution policy errors:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### WSL Path Conversion
For WSL environments, ensure proper path conversion:
```bash
# Convert WSL path to Windows path
wslpath -w /mnt/c/Projects/summeets
# Result: C:\Projects\summeets
```

### Dependencies Check
Verify all required tools are installed:
```powershell
# Check Python
python --version

# Check Node.js
node --version

# Check npm
npm --version

# Check project installation
python -c "import summeets.core; print('Summeets package installed')"
```

## Contributing

When adding new test features:

1. Follow PowerShell best practices
2. Add comprehensive error handling
3. Include detailed logging
4. Update this documentation
5. Test on both Windows and WSL environments

## Support

For issues with GUI testing:
1. Check the troubleshooting section above
2. Review log files for error details
3. Verify all dependencies are installed
4. Test CLI workflow independently first
5. Create GitHub issue with test logs and system information