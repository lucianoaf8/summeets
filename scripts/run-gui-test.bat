@echo off
REM Summeets GUI Test Runner - Windows Batch File
REM This script launches the PowerShell GUI automation test

echo ========================================
echo Summeets GUI Automation Test
echo ========================================
echo.

REM Change to project directory
cd /d "C:\Projects\summeets"

REM Check if PowerShell is available
powershell -Command "Get-Host" >nul 2>&1
if errorlevel 1 (
    echo ERROR: PowerShell is not available
    echo Please install PowerShell or run from PowerShell directly
    pause
    exit /b 1
)

echo Starting GUI automation test...
echo.

REM Run the PowerShell test script
powershell -ExecutionPolicy Bypass -File "scripts\quick-gui-test.ps1"

echo.
echo Test completed. Check the logs for results.
pause