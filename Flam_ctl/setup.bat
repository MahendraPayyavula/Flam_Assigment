@echo off
REM Quick start script for QueueCTL on Windows

echo ========================================
echo QueueCTL - Quick Start Script (Windows)
echo ========================================
echo.

REM Check Python version
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo OK - Found: %PYTHON_VERSION%
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    exit /b 1
)
echo OK - Dependencies installed
echo.

REM Install package
echo Installing queuectl...
pip install -e .
if errorlevel 1 (
    echo Error: Failed to install queuectl
    exit /b 1
)
echo OK - QueueCTL installed
echo.

REM Verify installation
echo Verifying installation...
queuectl --version >nul 2>&1
if errorlevel 1 (
    echo Error: Installation verification failed
    exit /b 1
)
echo OK - Installation verified
echo.

REM Run tests
echo Running tests...
echo.
python tests\test_integration.py
if errorlevel 1 (
    echo Warning: Some tests failed, but setup is complete
    echo.
)

echo ========================================
echo OK - Setup Complete!
echo ========================================
echo.
echo Quick start:
echo   1. Enqueue a job:
echo      queuectl enqueue "echo Hello World"
echo.
echo   2. Start workers:
echo      queuectl worker start --count 2
echo.
echo   3. View status:
echo      queuectl status
echo.
echo   4. List jobs:
echo      queuectl list --state pending
echo.
echo For more information, run: queuectl --help
echo.
