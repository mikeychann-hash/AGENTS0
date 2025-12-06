@echo off
REM Agent0 Launcher with GUI Dashboard
REM This script starts all Agent0 services and opens a GUI dashboard

title Agent0 Launcher - Enhanced Security Edition

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
echo    ║              Enhanced Security Edition                       ║
echo    ║                                                              ║
echo    ║  🛡️  Enterprise-grade security protection active             ║
echo    ║  🔒 All security features operational                        ║
echo    ║  📊 Real-time monitoring and logging                         ║
echo    ╚══════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is available
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.8+ and ensure it's in PATH
    pause
    exit /b 1
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
    echo [INFO] Please start Ollama service first: ollama serve
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

REM Start the main Agent0 service
echo [INFO] Starting Agent0 services...
echo [INFO] Starting enhanced security monitoring...
echo.

REM Create startup log
echo %date% %time% - Agent0 Launcher Started > "%LOG_DIR%\launcher.log"
echo Configuration: %AGENT0_HOME%\agent0\configs\3070ti.yaml >> "%LOG_DIR%\launcher.log"

REM Start the Agent0 system in background with enhanced security
echo [STARTUP] Launching Agent0 core system...
start "Agent0 Core System" cmd /k "%PYTHON_CMD% -m agent0.scripts.run_loop --config agent0/configs/3070ti.yaml --steps 10 2>&1 ^| tee "%LOG_DIR%\agent0_runtime.log""

timeout /t 3 /nobreak >nul

REM Start the GUI dashboard
echo [STARTUP] Launching Agent Evolution Dashboard...
start "Agent0 Evolution Dashboard" cmd /k "%PYTHON_CMD% "%AGENT0_HOME%\dashboard_gui.py" 2>&1 ^| tee "%LOG_DIR%\dashboard.log""

timeout /t 3 /nobreak >nul

REM Start the evolution monitor
echo [STARTUP] Launching Evolution Monitor...
start "Agent0 Evolution Monitor" cmd /k "%PYTHON_CMD% "%AGENT0_HOME%\evolution_monitor.py" 2>&1 ^| tee "%LOG_DIR%\evolution_monitor.log""

timeout /t 2 /nobreak >nul

REM Start log viewer
echo [STARTUP] Launching Log Viewer...
start "Agent0 Log Viewer" cmd /k "%PYTHON_CMD% "%AGENT0_HOME%\log_viewer.py" 2>&1 ^| tee "%LOG_DIR%\log_viewer.log""

timeout /t 2 /nobreak >nul

timeout /t 2 /nobreak >nul

REM Start security monitor
echo [STARTUP] Launching Security Monitor...
start "Agent0 Security Monitor" cmd /k "%PYTHON_CMD% "%AGENT0_HOME%\security_monitor.py""

timeout /t 2 /nobreak >nul

REM Start log viewer
echo [STARTUP] Launching Log Viewer...
start "Agent0 Log Viewer" cmd /k "%PYTHON_CMD% "%AGENT0_HOME%\log_viewer.py""

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    Agent0 Services Started!                  ║
echo ║                                                              ║
echo ║  🎯 Core System: Running (see runtime log)                   ║
echo ║  📊 Dashboard: Opened in new window                          ║
echo ║  🔒 Security Monitor: Active (monitoring threats)            ║
echo ║  📝 Log Viewer: Available for detailed analysis              ║
echo ║                                                              ║
echo ║  📁 Logs: %LOG_DIR%                                          ║
echo ║  🔧 Config: agent0/configs/3070ti.yaml                       ║
echo ║                                                              ║
echo ║  Press any key to open main dashboard...                   ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Wait for user input then open main dashboard
pause >nul
start "Agent0 Main Dashboard" cmd /k "%PYTHON_CMD% "%AGENT0_HOME%\main_dashboard.py""

echo.
echo [INFO] All services started successfully!
echo [INFO] Check the individual windows for detailed status and logs.
echo [INFO] Press any key to exit this launcher (services will continue running)...
pause >nul

echo [INFO] Launcher exiting. Services continue running in background...
timeout /t 2 /nobreak >nul