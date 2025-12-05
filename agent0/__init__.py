"""
Agent0 - Self-Evolving AI Agents

A dual-agent co-evolution framework with:
- Curriculum Agent (Teacher): Proposes challenging tasks
- Executor Agent (Student): Solves tasks with tool-augmented reasoning
- VeRL-style RL training with PPO/GRPO
- Benchmark evaluation on MATH, GSM8K

Quick Start:
    # CLI
    agent0 status
    agent0 run --steps 100
    agent0 benchmark --type math

    # Python
    from agent0 import Coordinator, StudentAgent, TeacherAgent
    from agent0.config import load_config

    config = load_config("agent0/configs/3070ti.yaml")
    coordinator = Coordinator(config)
    trajectory = coordinator.run_once({"next_task_id": "task-001"})
"""

__version__ = "0.2.0"
__author__ = "Agent0 Team"

# Core components
from agent0.config import load_config
from agent0.loop.coordinator import Coordinator
from agent0.agents.teacher import TeacherAgent
from agent0.agents.student import StudentAgent
from agent0.tasks.schema import TaskSpec, Trajectory

__all__ = [
    # Version
    "__version__",
    # Config
    "load_config",
    # Core
    "Coordinator",
    "TeacherAgent",
    "StudentAgent",
    # Schema
    "TaskSpec",
    "Trajectory",
]
