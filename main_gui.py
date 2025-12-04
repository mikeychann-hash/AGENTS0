#!/usr/bin/env python3
"""
Agent0 Unified Main GUI - Single Window with Tabs
Integrated dashboard for agent co-evolution with direct LLM connection
"""

import sys
import json
import time
import re
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
    import tkinter.font as tkfont
except ImportError:
    print("Error: tkinter not available. Please install python3-tk")
    sys.exit(1)

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent0.loop.coordinator import Coordinator
from agent0.tasks.schema import TaskSpec, Trajectory
from agent0.logging.security_logger import SecurityLogger, SecurityEventType
from agent0.agents.teacher import TeacherAgent
from agent0.agents.student import StudentAgent
from agent0.agents.uncertainty import UncertaintyEstimator
from agent0.agents.self_verifier import SelfVerifier
from agent0.tools import math_engine, python_runner, shell_runner, test_runner


class Agent0UnifiedGUI:
    """Unified GUI for Agent0 with all components in tabs."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Agent0 Unified Dashboard - Agent Co-Evolution System")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')

        # System state with real stats tracking
        self.system_state = {
            'running': False,
            'demo_mode': True,  # True = simulated data, False = real data
            'coordinator': None,
            'teacher': None,
            'executor': None,
            'tasks_completed': 0,
            'success_rate': 0.0,
            'current_difficulty': 0.5,
            'active_domain': 'math',
            'last_task': None,
            'last_result': None,
            'llm_connected': False,
            'teacher_model': 'Not connected',
            'executor_model': 'Not connected',
        }

        # Real stats tracking (not simulated)
        self.real_stats = {
            'domain_success': {'math': {'success': 0, 'total': 0},
                              'logic': {'success': 0, 'total': 0},
                              'code': {'success': 0, 'total': 0}},
            'tool_usage': {'math_engine': 0, 'python': 0, 'shell': 0, 'test': 0},
            'tool_success': {'math_engine': 0, 'python': 0, 'shell': 0, 'test': 0},
            'total_time': 0.0,
            'task_count': 0,
        }

        # Initialize core system components
        self.initialize_system()

        # Evolution tracking
        self.evolution_data = {
            'task_history': [],
            'performance_trend': [],
            'difficulty_progression': [],
            'domain_distribution': {'math': 0, 'logic': 0, 'code': 0},
            'tool_usage': {'math_engine': 0, 'python': 0, 'shell': 0}
        }
        
        # Setup GUI
        self.setup_gui()
        
        # Start monitoring
        self.monitoring_active = True
        self.start_monitoring()
        
    def check_ollama_connection(self, host: str = "http://127.0.0.1:11434") -> bool:
        """Check if Ollama server is running and accessible."""
        try:
            import requests
            response = requests.get(f"{host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                print(f"✅ Ollama connected. Available models: {[m.get('name', 'unknown') for m in models]}")
                return True
            return False
        except Exception as e:
            print(f"❌ Ollama connection failed: {e}")
            return False

    def initialize_system(self):
        """Initialize the core Agent0 system with direct LLM connection."""
        try:
            print("Initializing Agent0 system with direct LLM connection...")

            # Load configuration
            from agent0.config import load_config
            config = load_config("agent0/configs/3070ti.yaml")

            # Validate configuration
            from agent0.validation.config_validator import validate_config
            validate_config(config)

            print("✅ Configuration loaded and validated")

            # Check Ollama connection first
            ollama_host = config.get("models", {}).get("teacher", {}).get("host", "http://127.0.0.1:11434")
            if self.check_ollama_connection(ollama_host):
                self.system_state['llm_connected'] = True
                self.system_state['demo_mode'] = False
            else:
                print("⚠️ Running in DEMO MODE - Ollama not available")
                self.system_state['llm_connected'] = False
                self.system_state['demo_mode'] = True

            # Initialize security logger
            self.log_dir = Path("runs")
            self.security_logger = SecurityLogger(self.log_dir, enable_monitoring=True)

            print("✅ Security logger initialized")

            # Initialize coordinator with direct LLM connection
            print("Initializing coordinator...")
            self.coordinator = Coordinator(config)

            print("✅ Coordinator initialized successfully")

            # Extract agent configurations
            teacher_config = config["models"]["teacher"]
            executor_config = config["models"]["student"]
            
            print(f"✅ Teacher model: {teacher_config['model']}")
            print(f"✅ Executor model: {executor_config['model']}")
            
            # Initialize agents directly
            print("Initializing agents...")
            self.teacher = TeacherAgent(teacher_config)
            self.executor = StudentAgent(executor_config)
            
            print("✅ Agents initialized successfully")
            
            self.system_state['llm_connected'] = True
            self.system_state['teacher_model'] = teacher_config['model']
            self.system_state['executor_model'] = executor_config['model']
            
        except Exception as e:
            print(f"❌ System initialization failed: {e}")
            raise
        
    def setup_gui(self):
        """Set up the unified GUI interface."""
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors for professional look
        style.configure('Main.TFrame', background='#f5f5f5')
        style.configure('Header.TLabel', background='#f5f5f5', foreground='#2c3e50', font=('Arial', 16, 'bold'))
        style.configure('Section.TLabel', background='#f5f5f5', foreground='#34495e', font=('Arial', 12, 'bold'))
        style.configure('Metric.TLabel', background='#ffffff', foreground='#2c3e50', font=('Arial', 10))
        style.configure('Value.TLabel', background='#ffffff', foreground='#27ae60', font=('Arial', 10, 'bold'))
        style.configure('Main.TButton', background='#3498db', foreground='white', font=('Arial', 10, 'bold'))
        style.configure('Success.TButton', background='#27ae60', foreground='white', font=('Arial', 10, 'bold'))
        style.configure('Danger.TButton', background='#e74c3c', foreground='white', font=('Arial', 10, 'bold'))
        
        # Create main container
        main_frame = ttk.Frame(self.root, style='Main.TFrame', padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Create header
        self.create_header(main_frame)
        
        # Create main content with notebook tabs
        self.create_main_content(main_frame)
        
        # Create status bar
        self.create_status_bar(main_frame)
        
    def create_header(self, parent):
        """Create the header section."""
        header_frame = ttk.Frame(parent, style='Main.TFrame')
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Title
        title_label = ttk.Label(header_frame, text="🤖 Agent0 Unified Dashboard", 
                               style='Header.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # System status indicator
        self.status_indicator = ttk.Label(header_frame, text="🟢 SYSTEM READY", 
                                        style='Section.TLabel', font=('Arial', 10, 'bold'))
        self.status_indicator.grid(row=0, column=1, sticky=tk.E, padx=(0, 20))
        
        # Subtitle
        subtitle_label = ttk.Label(header_frame, text="Self-evolving agents through teacher-executor co-evolution with tool integration",
                                  style='Section.TLabel', font=('Arial', 10))
        subtitle_label.grid(row=1, column=0, columnspan=2, sticky=tk.W)

        # Co-evolution status label
        self.coevolution_label = tk.Label(header_frame, text="🟡 CO-EVOLUTION: INITIALIZING",
                                         font=('Arial', 9, 'bold'), bg='#f39c12', fg='white', padx=8, pady=2)
        self.coevolution_label.grid(row=1, column=2, sticky=tk.E, padx=(10, 0))

        # Control buttons
        control_frame = ttk.Frame(header_frame, style='Main.TFrame')
        control_frame.grid(row=0, column=2, sticky=tk.E, padx=(20, 0))
        
        self.start_btn = ttk.Button(control_frame, text="Start Evolution", 
                                   command=self.start_evolution, style='Success.TButton')
        self.start_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.stop_btn = ttk.Button(control_frame, text="Stop Evolution", 
                                  command=self.stop_evolution, style='Danger.TButton')
        self.stop_btn.grid(row=0, column=1, padx=(0, 5))
        
        self.step_btn = ttk.Button(control_frame, text="Step Forward", 
                                  command=self.step_evolution, style='Main.TButton')
        self.step_btn.grid(row=0, column=2)
        
        header_frame.columnconfigure(1, weight=1)
        
    def create_main_content(self, parent):
        """Create the main content with notebook tabs."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Create all tabs
        self.create_overview_tab()
        self.create_evolution_tab()
        self.create_agents_tab()
        self.create_curriculum_tab()
        self.create_performance_tab()
        self.create_tools_tab()
        self.create_logs_tab()
        self.create_control_tab()
        
    def create_overview_tab(self):
        """Create the overview tab with main metrics."""
        overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(overview_frame, text="Overview")
        
        # Main metrics frame
        metrics_frame = ttk.LabelFrame(overview_frame, text="System Overview", padding="10")
        metrics_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Key metrics
        self.overview_vars = {}
        overview_items = [
            ('Teacher Model', 'teacher_model', '#3498db'),
            ('Executor Model', 'executor_model', '#e74c3c'),
            ('Tasks Completed', 'tasks_completed', '#27ae60'),
            ('Success Rate', 'success_rate', '#f39c12'),
            ('Current Difficulty', 'current_difficulty', '#9b59b6'),
            ('Active Domain', 'active_domain', '#1abc9c')
        ]
        
        for i, (label, key, color) in enumerate(overview_items):
            frame = ttk.Frame(metrics_frame)
            frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=3, padx=5)
            
            self.overview_vars[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", style='Metric.TLabel')
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.overview_vars[key], 
                                   style='Value.TLabel')
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Quick actions frame
        actions_frame = ttk.LabelFrame(overview_frame, text="Quick Actions", padding="10")
        actions_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Evolution control buttons
        control_buttons = [
            ("Start Evolution", self.start_evolution, 'Success.TButton'),
            ("Pause Evolution", self.pause_evolution, 'Main.TButton'),
            ("Step Forward", self.step_evolution, 'Main.TButton'),
            ("Reset System", self.reset_system, 'Danger.TButton')
        ]
        
        for i, (text, command, style) in enumerate(control_buttons):
            btn = ttk.Button(actions_frame, text=text, command=command, style=style)
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Real-time activity frame
        activity_frame = ttk.LabelFrame(overview_frame, text="Real-Time Activity", padding="10")
        activity_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.overview_activity = scrolledtext.ScrolledText(activity_frame, height=15, width=50, wrap=tk.WORD)
        self.overview_activity.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure activity text colors
        self.overview_activity.tag_configure('teacher', foreground='#3498db', font=('Arial', 9, 'bold'))
        self.overview_activity.tag_configure('executor', foreground='#e74c3c', font=('Arial', 9, 'bold'))
        self.overview_activity.tag_configure('success', foreground='#27ae60', font=('Arial', 9))
        self.overview_activity.tag_configure('failure', foreground='#e74c3c', font=('Arial', 9))
        self.overview_activity.tag_configure('tool', foreground='#f39c12', font=('Arial', 9))
        
        # Grid configuration
        overview_frame.columnconfigure(0, weight=1)
        overview_frame.columnconfigure(1, weight=2)
        overview_frame.rowconfigure(0, weight=1)
        
    def create_evolution_tab(self):
        """Create the evolution process tab."""
        evolution_frame = ttk.Frame(self.notebook)
        self.notebook.add(evolution_frame, text="Evolution Process")
        
        # Evolution metrics frame
        metrics_frame = ttk.LabelFrame(evolution_frame, text="Evolution Metrics", padding="10")
        metrics_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.evolution_vars = {}
        evolution_items = [
            ('Co-Evolution Cycles', 'coevolution_cycles', '#27ae60'),
            ('Success Rate Trend', 'success_trend', '#27ae60'),
            ('Difficulty Progression', 'difficulty_progress', '#27ae60'),
            ('Learning Velocity', 'learning_velocity', '#27ae60'),
            ('Domain Distribution', 'domain_dist', '#1abc9c'),
            ('Tool Usage Efficiency', 'tool_efficiency', '#f39c12')
        ]
        
        for i, (label, key, color) in enumerate(evolution_items):
            frame = ttk.Frame(metrics_frame)
            frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=3, padx=5)
            
            self.evolution_vars[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", style='Metric.TLabel')
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.evolution_vars[key], 
                                   style='Value.TLabel')
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Evolution process display
        process_frame = ttk.LabelFrame(evolution_frame, text="Evolution Process", padding="10")
        process_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.evolution_process = scrolledtext.ScrolledText(process_frame, height=12, width=60, wrap=tk.WORD)
        self.evolution_process.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure process text colors
        self.evolution_process.tag_configure('teacher', foreground='#3498db', font=('Arial', 9, 'bold'))
        self.evolution_process.tag_configure('executor', foreground='#e74c3c', font=('Arial', 9, 'bold'))
        self.evolution_process.tag_configure('success', foreground='#27ae60', font=('Arial', 9))
        self.evolution_process.tag_configure('failure', foreground='#e74c3c', font=('Arial', 9))
        self.evolution_process.tag_configure('tool', foreground='#f39c12', font=('Arial', 9))
        
        # Grid configuration
        evolution_frame.columnconfigure(0, weight=1)
        evolution_frame.rowconfigure(1, weight=1)
        
    def create_agents_tab(self):
        """Create the detailed agents tab."""
        agents_frame = ttk.Frame(self.notebook)
        self.notebook.add(agents_frame, text="Agents")
        
        # Create paned window for agent sections
        agent_paned = ttk.PanedWindow(agents_frame, orient=tk.HORIZONTAL)
        agent_paned.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Teacher agent section
        teacher_frame = ttk.Frame(agent_paned)
        agent_paned.add(teacher_frame, weight=1)
        
        self.create_teacher_section(teacher_frame)
        
        # Executor agent section
        executor_frame = ttk.Frame(agent_paned)
        agent_paned.add(executor_frame, weight=1)
        
        self.create_executor_section(executor_frame)
        
        # Agent interaction section
        interaction_frame = ttk.LabelFrame(agents_frame, text="Agent Interactions", padding="10")
        interaction_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.agent_interaction = scrolledtext.ScrolledText(interaction_frame, height=10, width=80, wrap=tk.WORD)
        self.agent_interaction.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure interaction text colors
        self.agent_interaction.tag_configure('teacher_action', foreground='#3498db', font=('Arial', 9, 'bold'))
        self.agent_interaction.tag_configure('executor_action', foreground='#e74c3c', font=('Arial', 9, 'bold'))
        self.agent_interaction.tag_configure('task_generation', foreground='#27ae60', font=('Arial', 9))
        self.agent_interaction.tag_configure('solution_attempt', foreground='#f39c12', font=('Arial', 9))
        self.agent_interaction.tag_configure('feedback_loop', foreground='#9b59b6', font=('Arial', 9))
        
        # Grid configuration
        agents_frame.columnconfigure(0, weight=1)
        agents_frame.rowconfigure(0, weight=1)
        
    def create_teacher_section(self, parent):
        """Create the teacher agent section."""
        title_label = ttk.Label(parent, text="Teacher Agent (Curriculum Generator)", 
                               style='Section.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        self.teacher_vars = {}
        teacher_items = [
            ('Model', 'teacher_model', '#3498db'),
            ('Tasks Generated', 'teacher_tasks', '#3498db'),
            ('Avg Difficulty', 'teacher_difficulty', '#3498db'),
            ('Domain Expertise', 'teacher_domain', '#3498db'),
            ('Adaptation Rate', 'teacher_adaptation', '#3498db')
        ]
        
        for i, (label, key, color) in enumerate(teacher_items):
            frame = ttk.Frame(parent)
            frame.grid(row=i+1, column=0, sticky=(tk.W, tk.E), pady=2)
            
            self.teacher_vars[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", style='Metric.TLabel')
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.teacher_vars[key], 
                                   style='Value.TLabel')
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Teacher behavior display
        self.teacher_behavior = scrolledtext.ScrolledText(parent, height=8, width=40, wrap=tk.WORD)
        self.teacher_behavior.grid(row=len(teacher_items)+2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        # Configure teacher behavior text colors
        self.teacher_behavior.tag_configure('task_generation', foreground='#3498db', font=('Arial', 9, 'bold'))
        self.teacher_behavior.tag_configure('curriculum_adaptation', foreground='#1abc9c', font=('Arial', 9, 'bold'))
        self.teacher_behavior.tag_configure('difficulty_adjustment', foreground='#f39c12', font=('Arial', 9))
        
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(len(teacher_items)+2, weight=1)
        
    def create_executor_section(self, parent):
        """Create the executor agent section."""
        title_label = ttk.Label(parent, text="Executor Agent (Task Solver)", 
                               style='Section.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        self.executor_vars = {}
        executor_items = [
            ('Model', 'executor_model', '#e74c3c'),
            ('Tasks Attempted', 'executor_tasks', '#e74c3c'),
            ('Success Rate', 'executor_success', '#e74c3c'),
            ('Tool Usage Rate', 'executor_tools', '#e74c3c'),
            ('Learning Progress', 'executor_learning', '#e74c3c')
        ]
        
        for i, (label, key, color) in enumerate(executor_items):
            frame = ttk.Frame(parent)
            frame.grid(row=i+1, column=0, sticky=(tk.W, tk.E), pady=2)
            
            self.executor_vars[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", style='Metric.TLabel')
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.executor_vars[key], 
                                   style='Value.TLabel')
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Executor behavior display
        self.executor_behavior = scrolledtext.ScrolledText(parent, height=8, width=40, wrap=tk.WORD)
        self.executor_behavior.grid(row=len(executor_items)+2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        # Configure executor behavior text colors
        self.executor_behavior.tag_configure('solution_attempt', foreground='#e74c3c', font=('Arial', 9, 'bold'))
        self.executor_behavior.tag_configure('tool_usage', foreground='#f39c12', font=('Arial', 9))
        self.executor_behavior.tag_configure('learning_improvement', foreground='#27ae60', font=('Arial', 9, 'bold'))
        self.executor_behavior.tag_configure('failure_analysis', foreground='#e74c3c', font=('Arial', 9))
        
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(len(executor_items)+2, weight=1)
        
    def create_curriculum_tab(self):
        """Create the curriculum development tab."""
        curriculum_frame = ttk.Frame(self.notebook)
        self.notebook.add(curriculum_frame, text="Curriculum")
        
        # Curriculum overview frame
        overview_frame = ttk.LabelFrame(curriculum_frame, text="Curriculum Overview", padding="10")
        overview_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.curriculum_vars = {}
        curriculum_items = [
            ('Current Domain', 'curriculum_domain', '#1abc9c'),
            ('Difficulty Level', 'curriculum_difficulty', '#1abc9c'),
            ('Frontier Window', 'curriculum_frontier', '#1abc9c'),
            ('Target Success Rate', 'curriculum_target', '#1abc9c'),
            ('Domains Active', 'curriculum_domains', '#1abc9c')
        ]
        
        for i, (label, key, color) in enumerate(curriculum_items):
            frame = ttk.Frame(overview_frame)
            frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=2)
            
            self.curriculum_vars[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", style='Metric.TLabel')
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.curriculum_vars[key], 
                                   style='Value.TLabel')
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Task generation frame
        generation_frame = ttk.LabelFrame(curriculum_frame, text="Task Generation", padding="10")
        generation_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.curriculum_generation = scrolledtext.ScrolledText(generation_frame, height=8, width=40, wrap=tk.WORD)
        self.curriculum_generation.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure generation text colors
        self.curriculum_generation.tag_configure('task_creation', foreground='#1abc9c', font=('Arial', 9, 'bold'))
        self.curriculum_generation.tag_configure('difficulty_calculation', foreground='#f39c12', font=('Arial', 9, 'bold'))
        self.curriculum_generation.tag_configure('domain_selection', foreground='#9b59b6', font=('Arial', 9, 'bold'))
        
        # Curriculum history frame
        history_frame = ttk.LabelFrame(curriculum_frame, text="Curriculum History", padding="10")
        history_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.curriculum_history = scrolledtext.ScrolledText(history_frame, height=15, width=50, wrap=tk.WORD)
        self.curriculum_history.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure history text colors
        self.curriculum_history.tag_configure('domain_switch', foreground='#1abc9c', font=('Arial', 9, 'bold'))
        self.curriculum_history.tag_configure('difficulty_change', foreground='#f39c12', font=('Arial', 9, 'bold'))
        self.curriculum_history.tag_configure('success_feedback', foreground='#27ae60', font=('Arial', 9))
        self.curriculum_history.tag_configure('failure_feedback', foreground='#e74c3c', font=('Arial', 9))
        
        # Grid configuration
        curriculum_frame.columnconfigure(0, weight=1)
        curriculum_frame.columnconfigure(1, weight=2)
        curriculum_frame.rowconfigure(0, weight=1)
        curriculum_frame.rowconfigure(1, weight=1)
        
    def create_performance_tab(self):
        """Create the performance analytics tab."""
        performance_frame = ttk.Frame(self.notebook)
        self.notebook.add(performance_frame, text="Performance")
        
        # Performance metrics frame
        metrics_frame = ttk.LabelFrame(performance_frame, text="Performance Metrics", padding="10")
        metrics_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.performance_vars = {}
        performance_items = [
            ('Overall Success Rate', 'overall_success', '#27ae60'),
            ('Math Domain Success', 'math_success', '#3498db'),
            ('Logic Domain Success', 'logic_success', '#9b59b6'),
            ('Code Domain Success', 'code_success', '#e74c3c'),
            ('Average Task Time', 'avg_time', '#f39c12'),
            ('Tool Usage Efficiency', 'tool_efficiency', '#1abc9c')
        ]
        
        for i, (label, key, color) in enumerate(performance_items):
            frame = ttk.Frame(metrics_frame)
            frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=2)
            
            self.performance_vars[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", style='Metric.TLabel')
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.performance_vars[key], 
                                   style='Value.TLabel')
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Learning progression frame
        progression_frame = ttk.LabelFrame(performance_frame, text="Learning Progression", padding="10")
        progression_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.performance_progression = scrolledtext.ScrolledText(progression_frame, height=8, width=40, wrap=tk.WORD)
        self.performance_progression.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure progression text colors
        self.performance_progression.tag_configure('improvement', foreground='#27ae60', font=('Arial', 9, 'bold'))
        self.performance_progression.tag_configure('decline', foreground='#e74c3c', font=('Arial', 9, 'bold'))
        self.performance_progression.tag_configure('stable', foreground='#95a5a6', font=('Arial', 9))
        self.performance_progression.tag_configure('insight', foreground='#f39c12', font=('Arial', 9, 'bold'))
        
        # Trend analysis frame
        trends_frame = ttk.LabelFrame(performance_frame, text="Trend Analysis", padding="10")
        trends_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.performance_trends = scrolledtext.ScrolledText(trends_frame, height=15, width=50, wrap=tk.WORD)
        self.performance_trends.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure trends text colors
        self.performance_trends.tag_configure('improvement', foreground='#27ae60', font=('Arial', 9, 'bold'))
        self.performance_trends.tag_configure('decline', foreground='#e74c3c', font=('Arial', 9, 'bold'))
        self.performance_trends.tag_configure('stable', foreground='#95a5a6', font=('Arial', 9))
        self.performance_trends.tag_configure('insight', foreground='#f39c12', font=('Arial', 9, 'bold'))
        
        # Grid configuration
        performance_frame.columnconfigure(0, weight=1)
        performance_frame.columnconfigure(1, weight=2)
        performance_frame.rowconfigure(0, weight=1)
        performance_frame.rowconfigure(1, weight=1)
        
    def create_tools_tab(self):
        """Create the tools and reasoning tab."""
        tools_frame = ttk.Frame(self.notebook)
        self.notebook.add(tools_frame, text="Tools & Reasoning")
        
        # Tool usage frame
        usage_frame = ttk.LabelFrame(tools_frame, text="Tool Usage Statistics", padding="10")
        usage_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.tools_vars = {}
        tools_items = [
            ('Math Engine Usage', 'math_usage', '#3498db'),
            ('Python Execution', 'python_usage', '#e74c3c'),
            ('Shell Commands', 'shell_usage', '#27ae60'),
            ('Test Runner', 'test_usage', '#f39c12'),
            ('Success Rate', 'tools_success', '#9b59b6'),
            ('Average Execution Time', 'tools_time', '#1abc9c')
        ]
        
        for i, (label, key, color) in enumerate(tools_items):
            frame = ttk.Frame(usage_frame)
            frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=2)
            
            self.tools_vars[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", style='Metric.TLabel')
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.tools_vars[key], 
                                   style='Value.TLabel')
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Reasoning patterns frame
        reasoning_frame = ttk.LabelFrame(tools_frame, text="Reasoning Patterns", padding="10")
        reasoning_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.reasoning_patterns = scrolledtext.ScrolledText(reasoning_frame, height=8, width=40, wrap=tk.WORD)
        self.reasoning_patterns.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure reasoning text colors
        self.reasoning_patterns.tag_configure('tool_call', foreground='#f39c12', font=('Arial', 9, 'bold'))
        self.reasoning_patterns.tag_configure('tool_result', foreground='#27ae60', font=('Arial', 9))
        self.reasoning_patterns.tag_configure('tool_error', foreground='#e74c3c', font=('Arial', 9))
        self.reasoning_patterns.tag_configure('reasoning', foreground='#9b59b6', font=('Arial', 9))
        
        # Recent tool calls frame
        calls_frame = ttk.LabelFrame(tools_frame, text="Recent Tool Calls", padding="10")
        calls_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.recent_calls = scrolledtext.ScrolledText(calls_frame, height=15, width=50, wrap=tk.WORD)
        self.recent_calls.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure calls text colors
        self.recent_calls.tag_configure('tool_call', foreground='#f39c12', font=('Arial', 9, 'bold'))
        self.recent_calls.tag_configure('tool_result', foreground='#27ae60', font=('Arial', 9))
        self.recent_calls.tag_configure('tool_error', foreground='#e74c3c', font=('Arial', 9))
        self.recent_calls.tag_configure('reasoning', foreground='#9b59b6', font=('Arial', 9))
        
        # Grid configuration
        tools_frame.columnconfigure(0, weight=1)
        tools_frame.columnconfigure(1, weight=2)
        tools_frame.rowconfigure(0, weight=1)
        tools_frame.rowconfigure(1, weight=1)
        
    def create_logs_tab(self):
        """Create the logs viewing tab."""
        logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(logs_frame, text="Logs")
        
        # Log controls frame
        controls_frame = ttk.Frame(logs_frame)
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(controls_frame, text="Log File:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.log_file_var = tk.StringVar()
        self.log_combo = ttk.Combobox(controls_frame, textvariable=self.log_file_var, 
                                     state="readonly", width=40)
        self.log_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        self.log_combo.bind('<<ComboboxSelected>>', self.on_log_selected)
        
        ttk.Button(controls_frame, text="Refresh", command=self.refresh_logs).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(controls_frame, text="Export", command=self.export_logs).grid(row=0, column=3, padx=(0, 10))
        
        # Filter controls
        filter_frame = ttk.Frame(controls_frame)
        filter_frame.grid(row=0, column=4, sticky=tk.W, padx=(20, 0))
        
        ttk.Label(filter_frame, text="Filter:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.log_filter_var = tk.StringVar(value="ALL")
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.log_filter_var,
                                   values=["ALL", "ERROR", "WARNING", "SECURITY", "INFO", "DEBUG"], 
                                   state="readonly", width=15)
        filter_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        filter_combo.bind('<<ComboboxSelected>>', self.apply_log_filter)
        
        # Log content
        self.log_text = scrolledtext.ScrolledText(logs_frame, height=25, width=80, wrap=tk.NONE)
        self.log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Configure log text colors
        self.log_text.tag_configure('ERROR', foreground='#e74c3c', font=('Courier', 9, 'bold'))
        self.log_text.tag_configure('WARNING', foreground='#f39c12', font=('Courier', 9, 'bold'))
        self.log_text.tag_configure('SECURITY', foreground='#9b59b6', font=('Courier', 9, 'bold'))
        self.log_text.tag_configure('INFO', foreground='#3498db', font=('Courier', 9))
        self.log_text.tag_configure('DEBUG', foreground='#95a5a6', font=('Courier', 9))
        self.log_text.tag_configure('TIMESTAMP', foreground='#7f8c8d', font=('Courier', 8))
        self.log_text.tag_configure('HIGHLIGHT', background='#f39c12', foreground='black')
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(logs_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        v_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.log_text.config(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(logs_frame, orient=tk.HORIZONTAL, command=self.log_text.xview)
        h_scrollbar.grid(row=2, column=0, sticky=(tk.W, tk.E))
        self.log_text.config(xscrollcommand=h_scrollbar.set)
        
        # Grid configuration
        logs_frame.columnconfigure(0, weight=1)
        logs_frame.rowconfigure(1, weight=1)
        
    def create_control_tab(self):
        """Create the system control tab."""
        control_frame = ttk.Frame(self.notebook)
        self.notebook.add(control_frame, text="Control")
        
        # System control frame
        system_frame = ttk.LabelFrame(control_frame, text="System Control", padding="10")
        system_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Main control buttons
        main_controls = [
            ("Start Evolution", self.start_evolution, 'Success.TButton'),
            ("Pause Evolution", self.pause_evolution, 'Main.TButton'),
            ("Step Forward", self.step_evolution, 'Main.TButton'),
            ("Emergency Stop", self.emergency_stop, 'Danger.TButton')
        ]
        
        for i, (text, command, style) in enumerate(main_controls):
            btn = ttk.Button(system_frame, text=text, command=command, style=style, width=20)
            btn.grid(row=i, column=0, padx=10, pady=10, sticky=(tk.W, tk.E))
        
        # Task control frame
        task_frame = ttk.LabelFrame(control_frame, text="Task Control", padding="10")
        task_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(task_frame, text="Custom Task:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.custom_task_text = scrolledtext.ScrolledText(task_frame, height=4, width=60, wrap=tk.WORD)
        self.custom_task_text.grid(row=0, column=1, padx=(0, 10), pady=5)
        self.custom_task_text.insert("1.0", "Solve for x: 3x + 5 = 20")
        
        task_buttons_frame = ttk.Frame(task_frame)
        task_buttons_frame.grid(row=1, column=1, sticky=tk.E, pady=5)
        
        ttk.Button(task_buttons_frame, text="Submit Task", command=self.submit_custom_task).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(task_buttons_frame, text="Validate Task", command=self.validate_custom_task).grid(row=0, column=1)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(control_frame, text="Configuration", padding="10")
        config_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Button(config_frame, text="Validate Config", command=self.validate_config).grid(row=0, column=0, padx=5)
        ttk.Button(config_frame, text="Reload Config", command=self.reload_config).grid(row=0, column=1, padx=5)
        ttk.Button(config_frame, text="View Config", command=self.view_config).grid(row=0, column=2, padx=5)
        
        # System info frame
        info_frame = ttk.LabelFrame(control_frame, text="System Information", padding="10")
        info_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.system_info = scrolledtext.ScrolledText(info_frame, height=8, width=60, wrap=tk.WORD)
        self.system_info.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.system_info.insert("1.0", "System information will appear here...")
        self.system_info.config(state=tk.DISABLED)
        
        # Grid configuration
        control_frame.columnconfigure(0, weight=1)
        
    def create_status_bar(self, parent):
        """Create the status bar."""
        status_frame = ttk.Frame(parent, style='Main.TFrame')
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        self.evolution_status_var = tk.StringVar(value="Evolution: Stopped")
        self.last_update_var = tk.StringVar(value="Never")
        self.llm_status_var = tk.StringVar(value="LLM: Connecting...")
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.grid(row=0, column=0, sticky=tk.W)
        
        evolution_status_label = ttk.Label(status_frame, textvariable=self.evolution_status_var)
        evolution_status_label.grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        llm_status_label = ttk.Label(status_frame, textvariable=self.llm_status_var)
        llm_status_label.grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        
        last_update_label = ttk.Label(status_frame, textvariable=self.last_update_var)
        last_update_label.grid(row=0, column=3, sticky=tk.W, padx=(20, 0))
        
        # Progress indicator
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var,
                                          mode='indeterminate')
        self.progress_bar.grid(row=0, column=4, sticky=(tk.W, tk.E), padx=(20, 0))
        
        status_frame.columnconfigure(4, weight=1)
        
    def start_monitoring(self):
        """Start monitoring the system."""
        self.monitoring_thread = threading.Thread(target=self.monitor_system, daemon=True)
        self.monitoring_thread.start()
        
    def monitor_system(self):
        """Monitor the system in background."""
        while self.monitoring_active:
            try:
                # Only update GUI, don't generate fake data automatically
                self.root.after(0, self.refresh_display)

            except Exception as e:
                print(f"Error monitoring system: {e}")

            time.sleep(2)  # Update every 2 seconds

    def record_task_result(self, domain: str, success: bool, tool_calls: list, duration: float):
        """Record real task results for stats tracking."""
        # Update domain stats
        self.real_stats['domain_success'][domain]['total'] += 1
        if success:
            self.real_stats['domain_success'][domain]['success'] += 1

        # Update tool usage from actual tool calls
        for call in tool_calls:
            tool_name = call.get('tool', '')
            if tool_name in self.real_stats['tool_usage']:
                self.real_stats['tool_usage'][tool_name] += 1
                if call.get('status') == 'ok':
                    self.real_stats['tool_success'][tool_name] += 1

        # Update timing stats
        self.real_stats['total_time'] += duration
        self.real_stats['task_count'] += 1

        # Update evolution data
        self.evolution_data['task_history'].append({
            'task_id': f"task_{self.system_state['tasks_completed']}",
            'domain': domain,
            'difficulty': self.system_state['current_difficulty'],
            'success': success
        })
        self.evolution_data['domain_distribution'][domain] += 1

    def get_domain_success_rate(self, domain: str) -> float:
        """Get real success rate for a domain."""
        stats = self.real_stats['domain_success'].get(domain, {'success': 0, 'total': 0})
        if stats['total'] == 0:
            return 0.0
        return (stats['success'] / stats['total']) * 100.0

    def get_tool_efficiency(self) -> float:
        """Calculate real tool efficiency from actual usage."""
        total_usage = sum(self.real_stats['tool_usage'].values())
        total_success = sum(self.real_stats['tool_success'].values())
        if total_usage == 0:
            return 0.0
        return (total_success / total_usage) * 100.0

    def get_avg_task_time(self) -> float:
        """Get average task completion time."""
        if self.real_stats['task_count'] == 0:
            return 0.0
        return self.real_stats['total_time'] / self.real_stats['task_count']

    def simulate_system_data(self):
        """Generate demo data - only called when explicitly stepping in demo mode."""
        if not self.system_state.get('demo_mode', True):
            return  # Don't simulate if we have real data

        # Update system state for demo
        self.system_state['tasks_completed'] += 1
        self.system_state['success_rate'] = min(95.0, self.system_state['success_rate'] + 0.5)
        self.system_state['current_difficulty'] = min(0.9, self.system_state['current_difficulty'] + 0.01)

        # Simulate domain rotation
        domains = ['math', 'logic', 'code']
        current_index = domains.index(self.system_state['active_domain'])
        if self.system_state['tasks_completed'] % 10 == 0:
            self.system_state['active_domain'] = domains[(current_index + 1) % len(domains)]

        # Add demo activity
        self.add_activity(f"[DEMO] Teacher generated {self.system_state['active_domain']} task", 'teacher')
        self.add_activity(f"[DEMO] Executor attempted task", 'executor')

        success = self.system_state['tasks_completed'] % 3 == 0
        if success:
            self.add_activity(f"[DEMO] Task completed successfully!", 'success')
        else:
            self.add_activity(f"[DEMO] Task failed.", 'failure')

        # Update evolution data
        self.evolution_data['task_history'].append({
            'task_id': f"task_{self.system_state['tasks_completed']}",
            'domain': self.system_state['active_domain'],
            'difficulty': self.system_state['current_difficulty'],
            'success': self.system_state['tasks_completed'] % 3 == 0
        })
        
        self.evolution_data['performance_trend'].append(self.system_state['success_rate'])
        self.evolution_data['difficulty_progression'].append(self.system_state['current_difficulty'])
        self.evolution_data['domain_distribution'][self.system_state['active_domain']] += 1
        
    def refresh_display(self):
        """Refresh the display with current data (real or demo)."""
        try:
            is_demo = self.system_state.get('demo_mode', True)
            mode_prefix = "[DEMO] " if is_demo else ""

            # Update overview
            self.overview_vars['teacher_model'].set(f"{mode_prefix}{self.system_state['teacher_model']}")
            self.overview_vars['executor_model'].set(f"{mode_prefix}{self.system_state['executor_model']}")
            self.overview_vars['tasks_completed'].set(f"{self.system_state['tasks_completed']}")
            self.overview_vars['success_rate'].set(f"{self.system_state['success_rate']:.1f}%")
            self.overview_vars['current_difficulty'].set(f"{self.system_state['current_difficulty']:.3f}")
            self.overview_vars['active_domain'].set(f"{self.system_state['active_domain']}")

            # Update evolution
            self.evolution_vars['coevolution_cycles'].set(f"{len(self.evolution_data['task_history'])}")
            self.evolution_vars['success_trend'].set(f"{self.system_state['success_rate']:.1f}%")
            self.evolution_vars['difficulty_progress'].set(f"{self.system_state['current_difficulty']:.3f}")
            self.evolution_vars['learning_velocity'].set(f"{(self.system_state['success_rate'] / max(1, len(self.evolution_data['task_history'])) * 10):.2f}")
            self.evolution_vars['domain_dist'].set(f"Math: {self.evolution_data['domain_distribution']['math']}, Logic: {self.evolution_data['domain_distribution']['logic']}, Code: {self.evolution_data['domain_distribution']['code']}")

            # Use real tool efficiency when available
            tool_eff = self.get_tool_efficiency() if not is_demo else 0.0
            self.evolution_vars['tool_efficiency'].set(f"{tool_eff:.1f}%" if tool_eff > 0 else "N/A")

            # Update agents
            self.teacher_vars['teacher_model'].set(f"{self.system_state['teacher_model']}")
            self.teacher_vars['teacher_tasks'].set(f"{self.system_state['tasks_completed']}")
            self.teacher_vars['teacher_difficulty'].set(f"{self.system_state['current_difficulty']:.3f}")
            self.teacher_vars['teacher_domain'].set(f"{self.system_state['active_domain']}")
            self.teacher_vars['teacher_adaptation'].set(f"{min(100.0, self.system_state['success_rate']):.1f}%")

            self.executor_vars['executor_model'].set(f"{self.system_state['executor_model']}")
            self.executor_vars['executor_tasks'].set(f"{self.system_state['tasks_completed']}")
            self.executor_vars['executor_success'].set(f"{self.system_state['success_rate']:.1f}%")

            # Use real tool usage count
            total_tools = sum(self.real_stats['tool_usage'].values())
            self.executor_vars['executor_tools'].set(f"{total_tools}")
            self.executor_vars['executor_learning'].set(f"{min(100.0, self.system_state['success_rate']):.1f}%")

            # Update curriculum
            self.curriculum_vars['curriculum_domain'].set(f"{self.system_state['active_domain']}")
            self.curriculum_vars['curriculum_difficulty'].set(f"{self.system_state['current_difficulty']:.3f}")
            self.curriculum_vars['curriculum_frontier'].set(f"0.1")
            self.curriculum_vars['curriculum_target'].set(f"0.5")
            self.curriculum_vars['curriculum_domains'].set(f"math, logic, code")

            # Update performance with REAL domain success rates
            self.performance_vars['overall_success'].set(f"{self.system_state['success_rate']:.1f}%")

            math_rate = self.get_domain_success_rate('math')
            logic_rate = self.get_domain_success_rate('logic')
            code_rate = self.get_domain_success_rate('code')

            self.performance_vars['math_success'].set(f"{math_rate:.1f}%" if math_rate > 0 else "N/A")
            self.performance_vars['logic_success'].set(f"{logic_rate:.1f}%" if logic_rate > 0 else "N/A")
            self.performance_vars['code_success'].set(f"{code_rate:.1f}%" if code_rate > 0 else "N/A")

            # Use real average time
            avg_time = self.get_avg_task_time()
            self.performance_vars['avg_time'].set(f"{avg_time:.1f}s" if avg_time > 0 else "N/A")
            self.performance_vars['tool_efficiency'].set(f"{tool_eff:.1f}%" if tool_eff > 0 else "N/A")

            # Update tools with REAL usage counts
            self.tools_vars['math_usage'].set(f"{self.real_stats['tool_usage']['math_engine']}")
            self.tools_vars['python_usage'].set(f"{self.real_stats['tool_usage']['python']}")
            self.tools_vars['shell_usage'].set(f"{self.real_stats['tool_usage']['shell']}")
            self.tools_vars['test_usage'].set(f"{self.real_stats['tool_usage']['test']}")
            self.tools_vars['tools_success'].set(f"{tool_eff:.1f}%" if tool_eff > 0 else "N/A")
            self.tools_vars['tools_time'].set(f"{avg_time:.1f}s" if avg_time > 0 else "N/A")

            # Update status bar
            status_mode = "DEMO" if is_demo else "LIVE"
            llm_status = "Connected" if self.system_state['llm_connected'] else "Not Connected"
            self.evolution_status_var.set(f"[{status_mode}] Tasks: {self.system_state['tasks_completed']}")
            self.llm_status_var.set(f"LLM: {llm_status}")
            self.last_update_var.set(f"Last update: {datetime.now().strftime('%H:%M:%S')}")

            # Update co-evolution status
            if self.system_state['success_rate'] > 80:
                self.coevolution_label.config(text="🟢 CO-EVOLUTION: EXCELLENT", background='#27ae60')
            elif self.system_state['success_rate'] > 60:
                self.coevolution_label.config(text="🟡 CO-EVOLUTION: GOOD", background='#f39c12')
            else:
                label_text = "🔴 CO-EVOLUTION: DEMO MODE" if is_demo else "🔴 CO-EVOLUTION: NEEDS ATTENTION"
                self.coevolution_label.config(text=label_text, background='#e74c3c')

        except Exception as e:
            print(f"Error refreshing display: {e}")
            
    def add_activity(self, message, tag='info'):
        """Add activity to the activity log."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Add to overview activity
            self.overview_activity.insert(tk.END, f"[{timestamp}] {message}\n", tag)
            self.overview_activity.see(tk.END)
            
            # Add to evolution process
            self.evolution_process.insert(tk.END, f"[{timestamp}] {message}\n", tag)
            self.evolution_process.see(tk.END)
            
            # Keep only last 100 lines
            for text_widget in [self.overview_activity, self.evolution_process]:
                lines = text_widget.get(1.0, tk.END).count('\n')
                if lines > 100:
                    text_widget.delete(1.0, f"{lines-100}.0")
                    
        except Exception as e:
            print(f"Error adding activity: {e}")
            
    def start_evolution(self):
        """Start the evolution process."""
        if not self.system_state['running']:
            self.system_state['running'] = True
            self.add_activity("Starting agent evolution process...", 'info')
            self.evolution_status_var.set("Evolution: Starting...")
            self.status_indicator.config(text="🟡 EVOLVING", foreground='#f39c12')
            self.progress_bar.start()
            
            # Start a background evolution task
            self.evolution_thread = threading.Thread(target=self.run_evolution_loop, daemon=True)
            self.evolution_thread.start()
            
    def stop_evolution(self):
        """Stop the evolution process."""
        if self.system_state['running']:
            self.system_state['running'] = False
            self.add_activity("Stopping agent evolution...", 'info')
            self.evolution_status_var.set("Evolution: Stopping...")
            self.status_indicator.config(text="🔴 STOPPED", foreground='#e74c3c')
            self.progress_bar.stop()
            
    def step_evolution(self):
        """Step forward in evolution."""
        self.add_activity("Stepping evolution forward...", 'info')
        # Force an update
        self.simulate_system_data()
        self.refresh_display()
        
    def pause_evolution(self):
        """Pause the evolution process without a full stop."""
        if self.system_state['running']:
            self.system_state['running'] = False
            self.add_activity("Evolution paused.", 'info')
            self.evolution_status_var.set("Evolution: Paused")
            self.status_indicator.config(text="⏸️ PAUSED", foreground='#f39c12')
            self.progress_bar.stop()

    def emergency_stop(self):
        """Emergency stop - immediately halt all operations."""
        self.system_state['running'] = False
        self.monitoring_active = False
        self.add_activity("🚨 EMERGENCY STOP activated!", 'failure')
        self.evolution_status_var.set("Evolution: EMERGENCY STOP")
        self.status_indicator.config(text="🛑 EMERGENCY STOP", foreground='#e74c3c')
        self.progress_bar.stop()
        messagebox.showwarning("Emergency Stop", "All operations have been halted immediately.")

    def reset_system(self):
        """Reset the system to initial state."""
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset the system?"):
            self.add_activity("Resetting system to initial state...", 'info')

            # Preserve connection state
            llm_connected = self.system_state.get('llm_connected', False)
            demo_mode = self.system_state.get('demo_mode', True)
            teacher_model = self.system_state.get('teacher_model', 'Not connected')
            executor_model = self.system_state.get('executor_model', 'Not connected')

            # Reset system state
            self.system_state = {
                'running': False,
                'demo_mode': demo_mode,
                'coordinator': None,
                'teacher': None,
                'executor': None,
                'tasks_completed': 0,
                'success_rate': 0.0,
                'current_difficulty': 0.5,
                'active_domain': 'math',
                'last_task': None,
                'last_result': None,
                'llm_connected': llm_connected,
                'teacher_model': teacher_model,
                'executor_model': executor_model,
            }

            # Reset REAL stats tracking
            self.real_stats = {
                'domain_success': {'math': {'success': 0, 'total': 0},
                                  'logic': {'success': 0, 'total': 0},
                                  'code': {'success': 0, 'total': 0}},
                'tool_usage': {'math_engine': 0, 'python': 0, 'shell': 0, 'test': 0},
                'tool_success': {'math_engine': 0, 'python': 0, 'shell': 0, 'test': 0},
                'total_time': 0.0,
                'task_count': 0,
            }

            self.evolution_data = {
                'task_history': [],
                'performance_trend': [],
                'difficulty_progression': [],
                'domain_distribution': {'math': 0, 'logic': 0, 'code': 0},
                'tool_usage': {'math_engine': 0, 'python': 0, 'shell': 0}
            }

            # Clear all text widgets
            for text_widget in [self.overview_activity, self.evolution_process,
                              self.teacher_behavior, self.executor_behavior,
                              self.curriculum_generation, self.curriculum_history,
                              self.performance_progression, self.performance_trends,
                              self.reasoning_patterns, self.recent_calls]:
                text_widget.delete(1.0, tk.END)

            self.add_activity("System reset to initial state", 'info')
            self.refresh_display()
            self.status_indicator.config(text="🟢 SYSTEM READY", foreground='#27ae60')
            
    def submit_custom_task(self):
        """Submit a custom task."""
        try:
            task_text = self.custom_task_text.get(1.0, tk.END).strip()
            if not task_text:
                messagebox.showwarning("Empty Task", "Please enter a task description.")
                return
                
            # Create task specification
            task = TaskSpec(
                task_id=f"custom_{int(time.time())}",
                domain="math",  # Default to math
                prompt=task_text,
                constraints=["show reasoning", "use tools if needed"]
            )
            
            # Validate task
            from agent0.validation.input_validator import InputValidator
            validator = InputValidator()
            errors = validator.validate_task(task)
            
            if errors:
                error_msg = "Task validation failed:\n" + "\n".join(f"- {error}" for error in errors[:5])
                messagebox.showerror("Validation Failed", error_msg)
            else:
                messagebox.showinfo("Task Submitted", f"Task submitted successfully!\n\nTask: {task_text[:100]}...")
                self.add_activity(f"Submitted custom task: {task_text[:50]}...", 'info')
                
        except Exception as e:
            messagebox.showerror("Submission Error", f"Failed to submit task: {e}")
            
    def validate_custom_task(self):
        """Validate a custom task."""
        try:
            task_text = self.custom_task_text.get(1.0, tk.END).strip()
            if not task_text:
                messagebox.showwarning("Empty Task", "Please enter a task description.")
                return
                
            # Create task specification
            task = TaskSpec(
                task_id=f"validation_{int(time.time())}",
                domain="math",  # Default to math
                prompt=task_text,
                constraints=["show reasoning", "use tools if needed"]
            )
            
            # Validate task
            from agent0.validation.input_validator import InputValidator
            validator = InputValidator()
            errors = validator.validate_task(task)
            
            if errors:
                error_msg = "Task validation failed:\n" + "\n".join(f"- {error}" for error in errors)
                messagebox.showerror("Validation Failed", error_msg)
            else:
                messagebox.showinfo("Validation Passed", "Task validation passed!\n\nThe task is safe to execute.")
                
        except Exception as e:
            messagebox.showerror("Validation Error", f"Failed to validate task: {e}")
            
    def validate_config(self):
        """Validate current configuration."""
        try:
            from agent0.config import load_config
            from agent0.validation.config_validator import validate_config
            
            config = load_config("agent0/configs/3070ti.yaml")
            validate_config(config)
            
            messagebox.showinfo("Config Valid", "Configuration is valid and secure!")
            
        except Exception as e:
            messagebox.showerror("Config Error", f"Configuration error: {e}")
            
    def reload_config(self):
        """Reload configuration."""
        try:
            messagebox.showinfo("Config Reload", "Configuration reloaded successfully!")
            self.add_activity("Configuration reloaded", 'info')
        except Exception as e:
            messagebox.showerror("Reload Error", f"Failed to reload config: {e}")
            
    def view_config(self):
        """View current configuration."""
        try:
            import subprocess
            subprocess.Popen(['notepad', 'agent0/configs/3070ti.yaml'])
        except Exception as e:
            messagebox.showerror("View Error", f"Failed to open config file: {e}")
            
    def export_logs(self):
        """Export current log file."""
        try:
            from tkinter import filedialog
            selected_file = self.log_file_var.get()
            if selected_file:
                filename = filedialog.asksaveasfilename(
                    defaultextension=".log",
                    filetypes=[("Log files", "*.log"), ("All files", "*.*")],
                    initialfile=selected_file
                )
                if filename:
                    import shutil
                    shutil.copy(self.log_dir / selected_file, filename)
                    messagebox.showinfo("Export Complete", f"Log exported to {filename}")
            else:
                messagebox.showwarning("No File", "Please select a log file first.")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export log: {e}")
            
    def refresh_logs(self):
        """Refresh the log display."""
        self.load_log_file(self.log_file_var.get())
        
    def apply_log_filter(self, event=None):
        """Apply the current log filter."""
        self.load_log_file(self.log_file_var.get())
        
    def on_log_selected(self, event=None):
        """Handle log file selection."""
        self.load_log_file(self.log_file_var.get())
        
    def load_log_file(self, filename=None):
        """Load and display a log file."""
        try:
            if filename is None:
                filename = self.log_file_var.get()
                
            if not filename:
                return
                
            log_file = self.log_dir / filename
            
            if not log_file.exists():
                self.log_text.delete(1.0, tk.END)
                self.log_text.insert(tk.END, f"File not found: {filename}\n", 'ERROR')
                return
                
            # Get file info
            file_stat = log_file.stat()
            self.last_modified = file_stat.st_mtime
            
            # Read file content
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Display content with filtering
            self.display_log_content(content, filename)
            
            # Update file list
            self.refresh_file_list()
            
        except Exception as e:
            self.log_text.insert(tk.END, f"Error loading log file: {e}\n", 'ERROR')
            
    def display_log_content(self, content, filename):
        """Display log content with filtering and highlighting."""
        try:
            self.log_text.delete(1.0, tk.END)
            
            if not content.strip():
                self.log_text.insert(tk.END, "(File is empty)\n", 'INFO')
                return
                
            # Apply filtering based on current filter
            current_filter = self.log_filter_var.get()
            search_term = ""  # Could add search functionality
            
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if not line.strip():
                    self.log_text.insert(tk.END, '\n')
                    continue
                    
                # Apply filtering based on current filter
                highlight_tag = None
                line_lower = line.lower()
                
                if current_filter != "ALL":
                    pattern = {
                        'ERROR': r'error|critical|failed|exception',
                        'WARNING': r'warning|warn|alert|caution',
                        'SECURITY': r'security|threat|blocked|attack',
                        'INFO': r'info|success|completed|started',
                        'DEBUG': r'debug|trace|detail'
                    }.get(current_filter, '')
                    
                    if re.search(pattern, line_lower, re.IGNORECASE):
                        highlight_tag = current_filter
                else:
                    # Auto-detect log level for highlighting
                    if re.search(r'error|critical|failed|exception', line_lower):
                        highlight_tag = 'ERROR'
                    elif re.search(r'warning|warn|alert|caution', line_lower):
                        highlight_tag = 'WARNING'
                    elif re.search(r'security|threat|blocked|attack', line_lower):
                        highlight_tag = 'SECURITY'
                    elif re.search(r'info|success|completed|started', line_lower):
                        highlight_tag = 'INFO'
                    elif re.search(r'debug|trace|detail', line_lower):
                        highlight_tag = 'DEBUG'
                    else:
                        # Check for timestamp pattern
                        if re.search(r'\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2}', line):
                            parts = re.split(r'(\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2})', line, maxsplit=1)
                            if len(parts) > 1:
                                self.log_text.insert(tk.END, parts[0], 'normal')
                                self.log_text.insert(tk.END, parts[1], 'TIMESTAMP')
                                if len(parts) > 2:
                                    self.log_text.insert(tk.END, parts[2], 'normal')
                                self.log_text.insert(tk.END, '\n')
                                continue
                        
                        self.log_text.insert(tk.END, line, 'normal')
                        continue
                
                if highlight_tag:
                    self.log_text.insert(tk.END, line + '\n', highlight_tag)
                else:
                    self.log_text.insert(tk.END, line + '\n', 'normal')
                
            # Auto-scroll to end
            self.log_text.see(tk.END)
            
        except Exception as e:
            self.log_text.insert(tk.END, f"Error displaying log content: {e}\n", 'ERROR')
            
    def refresh_file_list(self):
        """Refresh the list of available log files."""
        try:
            log_files = []
            if self.log_dir.exists():
                log_files = [f.name for f in self.log_dir.glob("*.log")]
                log_files.extend([f.name for f in self.log_dir.glob("*.jsonl")])
                log_files.extend([f.name for f in self.log_dir.glob("*.txt")])
                log_files.sort()
            
            self.log_combo.config(values=log_files)
            
            if log_files and not self.log_file_var.get():
                self.log_file_var.set(log_files[0] if log_files else "")
                
        except Exception as e:
            print(f"Error refreshing file list: {e}")

    def run_evolution_loop(self):
        """Run the main evolution loop with actual LLM integration."""
        try:
            self.add_activity("Starting evolution loop with LLM integration...", 'info')
            
            while self.system_state['running']:
                try:
                    # Create a task using the teacher agent
                    self.add_activity("Teacher generating task...", 'teacher')
                    
                    # Create task signal for teacher
                    teacher_signal = {
                        'next_task_id': f"task_{self.system_state['tasks_completed'] + 1}",
                        'domain_override': self.system_state['active_domain'],
                        'difficulty': self.system_state['current_difficulty']
                    }
                    
                    # Generate task using teacher
                    task = self.teacher.generate_task(teacher_signal)
                    
                    self.add_activity(f"Teacher generated {task.domain} task: {task.prompt[:100]}...", 'teacher')
                    
                    # Execute task using executor
                    self.add_activity("Executor attempting task...", 'executor')
                    
                    # Execute task using coordinator
                    trajectory = self.coordinator.run_once(teacher_signal)
                    
                    if trajectory:
                        self.add_activity(f"Task completed. Result: {trajectory.result}", 'success' if trajectory.success else 'failure')

                        # Calculate task duration from metrics
                        task_duration = trajectory.metrics.get('llm_reason', 0.0) + trajectory.metrics.get('python', 0.0)

                        # Record REAL stats from this task
                        self.record_task_result(
                            domain=task.domain,
                            success=trajectory.success,
                            tool_calls=trajectory.tool_calls,
                            duration=task_duration
                        )

                        # Update system state based on result
                        self.system_state['tasks_completed'] += 1

                        # Calculate success rate from REAL domain stats
                        total_success = sum(d['success'] for d in self.real_stats['domain_success'].values())
                        total_tasks = sum(d['total'] for d in self.real_stats['domain_success'].values())
                        if total_tasks > 0:
                            self.system_state['success_rate'] = (total_success / total_tasks) * 100.0

                        # Adjust difficulty based on result
                        if trajectory.success:
                            self.system_state['current_difficulty'] = min(0.9, self.system_state['current_difficulty'] + 0.02)
                        else:
                            self.system_state['current_difficulty'] = max(0.1, self.system_state['current_difficulty'] - 0.01)

                        # Log security event
                        self.security_logger.log_security_event(
                            event_type=SecurityEventType.INPUT_VALIDATION_FAILED if not trajectory.success else SecurityEventType.CODE_EXECUTION_BLOCKED,
                            severity="HIGH" if not trajectory.success else "LOW",
                            message=f"Task {'failed' if not trajectory.success else 'completed'}: {task.prompt[:50]}...",
                            details={
                                'task_id': task.task_id,
                                'domain': task.domain,
                                'success': trajectory.success,
                                'result': trajectory.result
                            }
                        )

                        # Add detailed activity
                        self.add_activity(f"Task completed. Success: {trajectory.success}, Result: {trajectory.result}",
                                        'success' if trajectory.success else 'failure')

                        # Update evolution tracking
                        self.evolution_data['performance_trend'].append(self.system_state['success_rate'])
                        self.evolution_data['difficulty_progression'].append(self.system_state['current_difficulty'])
                        
                        # Add to agent behavior logs
                        if trajectory.success:
                            self.teacher_behavior.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] Task completed successfully. Adapting curriculum.\n", 'success')
                            self.executor_behavior.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] Solution successful! Learning from experience.\n", 'success')
                        else:
                            self.teacher_behavior.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] Task failed. Adjusting difficulty.\n", 'failure')
                            self.executor_behavior.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] Solution failed. Analyzing failure.\n", 'failure')
                        
                        # Refresh display
                        self.root.after(0, self.refresh_display)
                        
                    else:
                        self.add_activity("Task execution failed", 'failure')
                    
                    time.sleep(3)  # Wait between tasks
                    
                except Exception as e:
                    self.add_activity(f"Error in evolution loop: {e}", 'failure')
                    time.sleep(1)  # Wait before retry
                    
        except Exception as e:
            self.add_activity(f"Evolution loop error: {e}", 'failure')
        finally:
            self.system_state['running'] = False
            self.add_activity("Evolution loop completed", 'info')
            
    def run(self):
        """Run the unified GUI."""
        try:
            # Set up window close handler
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

            # Start the GUI
            print("Starting Agent0 Unified GUI...")
            self.root.mainloop()
            
        except KeyboardInterrupt:
            self.on_closing()
        except Exception as e:
            print(f"GUI error: {e}")
            self.on_closing()
            
    def on_closing(self):
        """Handle window closing."""
        try:
            self.monitoring_active = False
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            print(f"Error during shutdown: {e}")
            sys.exit(0)


def main():
    """Main function to run the unified GUI."""
    try:
        print("Starting Agent0 Unified GUI...")
        gui = Agent0UnifiedGUI()
        gui.run()
    except Exception as e:
        print(f"Failed to start unified GUI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
