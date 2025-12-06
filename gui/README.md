# Agent0 GUI Components

This directory contains the graphical user interface components for the Agent0 framework.

## Components

### Main Applications

1. **dashboard_gui.py** - Main evolution dashboard
   - Evolution overview and metrics
   - Agent performance tracking
   - Curriculum visualization
   - Performance analytics

2. **evolution_monitor.py** - Real-time co-evolution tracker
   - Live teacher-executor interactions
   - Learning dynamics visualization
   - Co-evolution metrics

3. **main_dashboard.py** - Alternative dashboard implementation
   - Comprehensive system monitoring
   - Multi-panel interface

4. **log_viewer.py** - Advanced log analysis tool
   - Syntax highlighting
   - Search and filter capabilities
   - Real-time log updates

5. **security_monitor.py** - Security event monitoring
   - Security event tracking
   - Real-time security alerts

## Quick Start

### Launch Main Dashboard
```bash
cd gui
python dashboard_gui.py
```

### Launch Evolution Monitor
```bash
cd gui
python evolution_monitor.py
```

### Launch All Components
```bash
cd ..
./scripts/start_agent0.bat
```

## Requirements

- Python 3.9+
- tkinter (included with Python on most systems)
- matplotlib
- Agent0 core framework

## Configuration

GUI components read from:
- `../runs/trajectories.jsonl` - Training data
- `../runs/*.log` - System logs
- `../agent0/configs/3070ti.yaml` - System configuration

## Documentation

See `../GUI.md` for comprehensive documentation.

## Troubleshooting

**Issue:** GUI doesn't start
- Ensure tkinter is installed: `python -m tkinter`
- Check Python version: `python --version` (need 3.9+)

**Issue:** No data displayed
- Verify Agent0 core is running
- Check that `runs/trajectories.jsonl` exists
- Verify log files are being written

**Issue:** Import errors
- Ensure you're in the correct directory
- Try: `cd .. && python -m gui.dashboard_gui`

## Notes

- All GUI components auto-refresh every 2 seconds
- Dark theme optimized for extended viewing
- Resizable windows with responsive layouts
