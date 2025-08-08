@echo off
:: Voxiom TTS GUI Launcher - Detached Version
:: Windows 10 Batch File
:: Version 1.1

title Voxiom TTS GUI Launcher
color 0A
echo.
echo **********************************************
echo *   Voxiom TTS GUI - Initializing System    *
echo **********************************************
echo.

:: Check Python installation
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

:: Verify Python version
for /f "tokens=2 delims= " %%A in ('python --version 2^>^&1') do set "python_version=%%A"
for /f "tokens=1-3 delims=." %%A in ("%python_version%") do (
    if %%A LSS 3 (
        echo [ERROR] Requires Python 3.8+. Found version: %python_version%
        pause
        exit /b 1
    )
    if %%A equ 3 if %%B LSS 8 (
        echo [ERROR] Requires Python 3.8+. Found version: %python_version%
        pause
        exit /b 1
    )
)

:: Check for virtual environment
if not exist ".venv\" (
    echo Creating Python virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

:: Install/upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [WARNING] Failed to upgrade pip - continuing anyway
)

:: Install required packages
echo Installing dependencies...
pip install torch numpy sounddevice soundfile customtkinter matplotlib
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

:: Check for models directory
if not exist "models\tts\" (
    echo Creating models directory...
    mkdir "models\tts"
)

:: Launch application in a separate process
echo.
echo **********************************************
echo *       Starting Voxiom TTS GUI...          *
echo *  (This window can now be safely closed)   *
echo **********************************************
echo.

:: Method 1: Using START (recommended)
:: start "Voxiom TTS GUI" /B python main.py

:: Alternative Method 2: Using WMIC (more robust)
:: wmic process call create "python gui.py","%CD%"

set /p VERSION=<version.txt
echo Starting VoxiomTTS v%VERSION%

:: Alternative Method 3: Using PowerShell
powershell -Command "Start-Process python -ArgumentList 'main.py' -WorkingDirectory '%CD%' -WindowStyle Hidden"

:: Immediately deactivate venv and exit launcher
deactivate
exit /b 0
