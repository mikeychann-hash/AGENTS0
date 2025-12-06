@echo off
REM Agent0 Unified Launcher - Single Window with Tabs
REM This script starts the unified GUI with all components integrated

title Agent0 Unified Launcher - Agent Co-Evolution System

REM Set console colors and formatting
chcp 65001 >nul 2>&1
color 0A

REM Get current directory
set AGENT0_HOME=%~dp0
set AGENT0_HOME=%AGENT0_HOME:~0,-1%

REM Set Python path (adjust if needed)
set PYTHON_CMD=python

REM Set log directory
set LOG_DIR=%AGENT0_HOME%\runs

REM Create necessary directories if they don't exist
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%AGENT0_HOME%\sandbox" mkdir "%AGENT0_HOME%\sandbox"

cls
echo.
echo    ╔══════════════════════════════════════════════════════════════╗
echo    ║                    Agent0 Framework                          ║
echo    ║              Unified GUI with Tabs                         ║
echo    ║                                                              ║
echo    ║  🤖 Direct LLM Connection - No Scaffolding                 ║
echo    ║  🔄 Real-time Agent Co-Evolution                           ║
echo    ║  📊 Integrated Dashboard with Tabs                         ║
echo    ╚══════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is available
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    set PYTHON_CMD=py -3
    %PYTHON_CMD% --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ??O Python not found! Please install Python 3.8+ and ensure its in PATH
        pause
        exit /b 1
    )
)

echo [INFO] Python found: %PYTHON_CMD%
echo [INFO] Agent0 Home: %AGENT0_HOME%
echo [INFO] Log Directory: %LOG_DIR%
echo.

REM Check if Ollama is running
echo [INFO] Checking Ollama service status...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Ollama service is running
) else (
    echo ⚠️  Ollama service not detected at http://localhost:11434
    echo [INFO] Please start Ollama service: ollama serve
    echo [INFO] Or install Ollama from: https://ollama.ai
    echo.
)

REM Install/Update dependencies
echo [INFO] Checking dependencies...
echo [INFO] Installing required packages...
%PYTHON_CMD% -m pip install -r requirements_complete.txt >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Dependencies installed/updated successfully
) else (
    echo ⚠️  Some dependencies may be missing, but core functionality should work
)
echo.

REM Start the unified GUI
echo [INFO] Starting Agent0 Unified GUI...
echo [INFO] Launching integrated dashboard with tabs...
echo.

REM Create startup log
echo %date% %time% - Agent0 Unified GUI Started > "%LOG_DIR%\launcher.log"
echo Configuration: %AGENT0_HOME%\agent0\configs\3070ti.yaml >> "%LOG_DIR%\launcher.log"

REM Start the unified GUI
echo [STARTUP] Launching Agent0 Unified GUI...
start "Agent0 Unified GUI" cmd /k "%PYTHON_CMD% "%AGENT0_HOME%\main_gui.py" 2>&1 ^| tee "%LOG_DIR%\gui.log""

timeout /t 3 /nobreak >nul

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    Agent0 Services Started!                  ║
echo ║                                                              ║
echo ║  🤖 Unified GUI: Active (see GUI window)                     ║
echo ║  🔄 Agent Co-Evolution: Real-time monitoring                ║
echo ║  📊 Integrated Dashboard: All features in one window        ║
echo ║                                                              ║
echo ║  📁 Logs: %LOG_DIR%                                          ║
echo ║  🔧 Config: agent0/configs/3070ti.yaml                       ║
echo ║                                                              ║
echo ║  The unified GUI is now running!                           ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo [INFO] The Agent0 unified GUI is now running with direct LLM connection!
echo [INFO] Check the GUI window for real-time agent co-evolution visualization.
echo [INFO] All features are integrated into the single dashboard window.
echo.
echo Press any key to exit this launcher (GUI will continue running)...
pause >nul

echo [INFO] Launcher exiting. GUI continues running in background...
timeout /t 2 /nobreak >nul
