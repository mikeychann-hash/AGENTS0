# Agent0 GUI System Documentation

**Last Updated:** December 5, 2025
**Status:** Fully Operational
**Components:** 3 Main Applications

---

## 🎯 Overview

The Agent0 GUI system provides comprehensive visualization of the teacher-executor co-evolution process, learning dynamics, and system performance. The GUI perfectly demonstrates Agent0's core innovation: self-evolving AI agents that improve through their own interactions without human-curated data.

---

## 🖥️ GUI Components

### 1. Main Evolution Dashboard (`dashboard_gui.py`)

**Purpose:** Primary control center for monitoring agent co-evolution

**Key Features:**
- **Evolution Overview** - Real-time co-evolution metrics and progress
- **Agents Tab** - Detailed teacher vs executor performance tracking
- **Curriculum Tab** - Task generation and difficulty progression
- **Performance Tab** - Learning analytics and success trends
- **Tools Tab** - Tool usage patterns and reasoning evolution

**Live Metrics Displayed:**
- Tasks completed counter
- Overall success rate
- Current difficulty level
- Co-evolution cycle count
- Domain distribution charts
- Learning velocity trends

---

### 2. Evolution Monitor (`evolution_monitor.py`)

**Purpose:** Real-time tracking of teacher-executor interactions

**Key Features:**
- **Live Interactions** - Real-time dialogue between teacher and executor
- **Learning Dynamics** - Difficulty progression and adaptation
- **Co-Evolution Metrics** - Cycle counting and success tracking
- **Agent Metrics** - Separate performance tracking for each agent

**Example Output:**
```
[14:32:15] Teacher proposes math task at difficulty 0.523
[14:32:16] Executor attempts solution with tool integration
[14:32:17] Task completed successfully! Success rate: 78.5%
[14:32:18] Teacher adapts curriculum based on executor performance
[14:32:19] Difficulty increased to 0.528 for next challenge
```

---

### 3. Log Viewer (`log_viewer.py`)

**Purpose:** Advanced log analysis for agent behavior

**Key Features:**
- **Syntax Highlighting** - Automatic log level detection
- **Search & Filter** - Find specific agent interactions
- **Auto-refresh** - Real-time log updates (2-second intervals)
- **Export Capability** - Save analysis results

**Supported Log Levels:**
- DEBUG - Detailed diagnostic information
- INFO - General operational messages
- WARNING - Warning conditions
- ERROR - Error events
- CRITICAL - Critical failures

---

## 🚀 Quick Start

### Starting the GUI System

#### Option 1: Launch All Components
```bash
start_agent0.bat
```
This starts:
- Agent0 core system
- Evolution dashboard
- Evolution monitor
- Log viewer

#### Option 2: Launch Individual Components
```bash
# Main dashboard only
python dashboard_gui.py

# Evolution monitor only
python evolution_monitor.py

# Log viewer only
python log_viewer.py
```

---

## 🤖 Understanding Co-Evolution Visualization

### The Teacher-Executor Interaction Flow

```
Teacher (qwen2.5:3b)          Executor (qwen2.5:7b)
     │                              │
     ├─ Generates Task ─────────────▶│
     │  (appropriate difficulty)     │
     │                              ├─ Attempts Solution
     │                              │  (with tool integration)
     │                              │
     ◀─ Feedback Loop ──────────────┤
     │  (adjusts difficulty)        │
     │                              │
     ├─ New Task ──────────────────▶│
     │  (based on performance)      │
```

### Key Co-Evolution Metrics Tracked

1. **Co-Evolution Cycles** - Count of teacher-executor iterations
2. **Success Rate Trend** - Learning progress over time (target: 78-82%)
3. **Difficulty Progression** - Curriculum adaptation (0.0-1.0 scale)
4. **Domain Distribution** - Balance across math/logic/code domains
5. **Learning Velocity** - Rate of improvement over time

---

## 📊 Dashboard Tabs Explained

### Evolution Overview Tab
- Real-time status of co-evolution process
- Current iteration count
- Success rate trends
- System health indicators

### Agents Tab
**Teacher Agent Metrics:**
- Tasks generated
- Difficulty adjustments
- Domain selections
- Novelty scores

**Executor Agent Metrics:**
- Tasks attempted
- Success/failure rate
- Tool usage frequency
- Average solving time

### Curriculum Tab
- Task difficulty over time
- Domain rotation patterns
- Frontier learning visualization
- Success rate by domain

### Performance Tab
- Learning curves
- Success rate trends
- Tool usage efficiency
- Performance improvements over time

### Tools Tab
- Tool usage frequency (Python, Math, Shell)
- Tool success rates
- Reasoning pattern analysis
- Multi-tool composition tracking

---

## 🎯 What the GUI Demonstrates

### Core Agent0 Innovation

✅ **Self-Evolving Without Human Data**
- Agents generate their own training curriculum
- No manual data labeling required
- Fully autonomous improvement

✅ **Teacher-Executor Co-Evolution**
- Symbiotic learning relationship
- Teacher adapts based on executor performance
- Executor improves through challenging tasks

✅ **Tool-Integrated Reasoning**
- External tools enhance problem-solving
- Multi-step tool composition
- Intelligent tool selection

✅ **Adaptive Curriculum**
- Automatic difficulty adjustment
- Domain rotation for balanced learning
- Frontier learning (tasks at capability edge)

✅ **Real-Time Learning**
- Live improvement visualization
- Immediate feedback loops
- Observable learning dynamics

---

## 🧪 Testing the GUI

### Component Test Script
```bash
python test_gui_components.py
```

**Expected Output:**
```
AGENT0 GUI COMPONENTS TEST
============================================================
Testing GUI component imports...
SUCCESS: Dashboard GUI import successful
SUCCESS: Evolution Monitor import successful
SUCCESS: Log Viewer import successful

Testing basic functionality...
SUCCESS: All GUI tests passed!
============================================================
```

### Simple GUI Test
```bash
python test_gui_simple.py
```

---

## 🛠️ Configuration

### GUI Update Intervals
- **Dashboard:** 2 seconds
- **Evolution Monitor:** 2 seconds
- **Log Viewer:** 2 seconds (configurable)

### Theme Settings
- **Default:** Dark theme (professional monitoring interface)
- **Colors:** Optimized for extended viewing
- **Fonts:** Monospace for code/logs, sans-serif for UI

### Window Sizes
- **Dashboard:** 1200x800 (resizable)
- **Evolution Monitor:** 1000x700 (resizable)
- **Log Viewer:** 900x600 (resizable)

---

## 🔧 Customization

### Adding Custom Metrics

Edit `dashboard_gui.py`:
```python
def update_custom_metric(self):
    # Your custom metric calculation
    value = calculate_custom_metric()
    self.custom_label.config(text=f"Custom: {value}")
```

### Customizing Log Viewer Filters

Edit `log_viewer.py`:
```python
def add_custom_filter(self):
    # Your custom filter logic
    filtered = [line for line in logs if custom_condition(line)]
    return filtered
```

---

## 📋 Troubleshooting

### Common Issues

**Issue:** GUI doesn't start
```bash
# Check dependencies
pip install tkinter
pip install matplotlib
```

**Issue:** No data displayed
```bash
# Verify Agent0 core is running
# Check logs in runs/ directory
```

**Issue:** Performance lag
```bash
# Increase update interval in code
# Reduce chart history length
```

**Issue:** Charts not updating
```bash
# Verify trajectory logging is enabled
# Check file permissions on runs/ directory
```

---

## 📊 Performance Metrics Explained

### Success Rate
- **Range:** 0-100%
- **Target:** 78-82% (optimal learning frontier)
- **Too High (>90%):** Tasks too easy, reduce difficulty
- **Too Low (<60%):** Tasks too hard, increase support

### Difficulty Level
- **Range:** 0.0-1.0
- **Scale:** 0.0 = trivial, 1.0 = extremely challenging
- **Adaptation:** Automatic based on success rate

### Learning Velocity
- **Metric:** Tasks solved per unit time
- **Higher = Better:** Faster learning and adaptation
- **Trend:** Should increase as agents improve

### Tool Usage Efficiency
- **Metric:** Percentage of tool calls that contribute to solution
- **Target:** >70%
- **Indicates:** How well agents use external tools

---

## 🎬 Demo Mode

### Running Demo Scenarios

The GUI can display demo/recorded data for presentations:
```bash
python dashboard_gui.py --demo
```

This loads pre-recorded co-evolution sessions for demonstration purposes.

---

## 🔄 Real-Time Updates

### How Data Flows to GUI

1. **Agent0 Core** executes tasks
2. **Trajectory Logger** writes to `runs/trajectories.jsonl`
3. **GUI Components** read updated trajectories every 2 seconds
4. **Charts & Metrics** update automatically
5. **User sees** real-time learning progress

---

## 📈 Monitoring Best Practices

### What to Watch

1. **Success Rate Stability** - Should hover around target (78-82%)
2. **Difficulty Progression** - Should gradually increase
3. **Domain Balance** - Even distribution across math/logic/code
4. **Error Patterns** - Look for systematic failures
5. **Tool Usage** - Should become more sophisticated over time

### When to Intervene

- Success rate consistently below 50%
- Difficulty not increasing after 100+ tasks
- One domain completely avoided
- Frequent tool execution errors
- System crashes or timeouts

---

## 🎯 Success Indicators

### Healthy Co-Evolution Shows:
- ✅ Gradual difficulty increase
- ✅ Stable success rate (75-85%)
- ✅ Balanced domain distribution
- ✅ Increasing tool sophistication
- ✅ Decreasing solution time (with practice)

### Problematic Patterns:
- ❌ Flat difficulty (no progression)
- ❌ Success rate extremes (<50% or >95%)
- ❌ Single domain dominance
- ❌ Decreasing tool usage
- ❌ Increasing error rates

---

## 🔗 Integration with Core System

### Log Files Monitored
- `runs/agent0_local.log` - Main system logs
- `runs/security.log` - Security events
- `runs/code_execution.log` - Code execution logs

### Data Files Read
- `runs/trajectories.jsonl` - Task-solution pairs
- `runs/logs/*.json` - Structured run logs

### Configuration
- `agent0/configs/3070ti.yaml` - System configuration
- GUI settings can reference config values

---

## 🚀 Future Enhancements

### Planned Features
- [ ] Multi-agent comparison view
- [ ] Export learning curves to charts
- [ ] Real-time performance alerts
- [ ] Benchmark comparison overlay
- [ ] Training progress predictions
- [ ] Advanced filtering and search
- [ ] Custom dashboard layouts

---

## 📚 Related Documentation

- **ARCHITECTURE.md** - System architecture
- **AGENTS.md** - Developer guide
- **README.md** - Project overview
- **QUICK_START.md** - Setup guide

---

## 🎉 Summary

The Agent0 GUI system provides:
- ✅ Complete visualization of agent co-evolution
- ✅ Real-time monitoring of learning dynamics
- ✅ Professional monitoring interface
- ✅ Easy-to-understand metrics
- ✅ Demonstration of self-evolving AI

**The GUI perfectly showcases Agent0's innovation: autonomous agent improvement through co-evolution and tool-integrated reasoning, without any human-curated datasets.**

---

*Last updated: December 5, 2025*
*For support or feature requests, see project repository*
