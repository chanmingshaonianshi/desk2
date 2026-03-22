@echo off
setlocal enabledelayedexpansion

echo ==============================================
echo Docker Batch Processor for Moon Dance
echo ==============================================

rem Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not installed or not in PATH.
    echo Please install Docker Desktop for Windows first.
    pause
    exit /b 1
)

echo [1/3] Building Docker image...
docker build -t moondance-batch:latest .
if %errorlevel% neq 0 (
    echo Error: Failed to build Docker image.
    pause
    exit /b 1
)

rem Create output directory if it doesn't exist
if not exist "batch_reports" mkdir "batch_reports"

set /p COUNT="Enter number of users to generate (default 5): "
if "%COUNT%"=="" set COUNT=5

echo [2/3] Running batch job for %COUNT% users...
echo Output directory: %CD%\batch_reports

docker run --rm -v "%CD%\batch_reports:/app/output" -e BATCH_COUNT=%COUNT% moondance-batch:latest

echo.
echo [3/3] Job complete!
echo Please check the "batch_reports" folder for Excel files.
echo ==============================================
pause
