#!/usr/bin/env python3
"""
Agent0 Dashboard - Agent Evolution and Learning Interface
Focuses on the co-evolution process between teacher and executor agents
"""

import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

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


class Agent0Dashboard:
    """Dashboard for monitoring Agent0's self-evolving agent system."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Agent0 Framework - Agent Evolution Dashboard")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Set up logging
        self.log_dir = Path("runs")
        self.security_logger = SecurityLogger(self.log_dir, enable_monitoring=True)
        
        # Agent system state
        self.agent_state = {
            'teacher_model': 'qwen2.5:3b',
            'executor_model': 'qwen2.5:7b',
            'tasks_completed': 0,
            'success_rate': 0.0,
            'current_difficulty': 0.5,
            'active_domain': 'math',
            'last_task': None,
            'last_result': None,
            'is_running': False
        }
        
        # Evolution tracking
        self.evolution_data = {
            'task_history': [],
            'performance_trend': [],
            'difficulty_progression': [],
            'domain_distribution': {'math': 0, 'logic': 0, 'code': 0},
            'tool_usage': {'math_engine': 0, 'python': 0, 'shell': 0}
        }
        
        # Initialize GUI
        self.setup_gui()
        
        # Start monitoring
        self.monitoring_active = True
        self.start_monitoring()
        
    def setup_gui(self):
        """Set up the main GUI interface."""
        # Create main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Header
        self.create_header(main_frame)
        
        # Main content area
        self.create_main_content(main_frame)
        
        # Status bar
        self.create_status_bar(main_frame)
        
    def create_header(self, parent):
        """Create the header section."""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Title
        title_font = tkfont.Font(family="Arial", size=16, weight="bold")
        title_label = ttk.Label(header_frame, text="Agent0 Framework - Agent Evolution Dashboard", 
                               font=title_font, foreground="#2c3e50")
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Agent status indicator
        self.agent_status_label = ttk.Label(header_frame, text="🤖 EVOLVING", 
                                           font=tkfont.Font(family="Arial", size=12, weight="bold"),
                                           foreground="#3498db")
        self.agent_status_label.grid(row=0, column=1, sticky=tk.E, padx=20)
        
        # Subtitle
        subtitle_font = tkfont.Font(family="Arial", size=10)
        subtitle_label = ttk.Label(header_frame, text="Self-evolving agents through teacher-executor co-evolution", 
                                  font=subtitle_font, foreground="#7f8c8d")
        subtitle_label.grid(row=1, column=0, columnspan=2, sticky=tk.W)
        
    def create_main_content(self, parent):
        """Create the main content area with tabs."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Create tabs focused on agent evolution
        self.create_evolution_tab()
        self.create_agents_tab()
        self.create_curriculum_tab()
        self.create_performance_tab()
        self.create_tools_tab()
        
    def create_evolution_tab(self):
        """Create the evolution overview tab."""
        evolution_frame = ttk.Frame(self.notebook)
        self.notebook.add(evolution_frame, text="Evolution Overview")
        
        # Evolution metrics frame
        metrics_frame = ttk.LabelFrame(evolution_frame, text="Evolution Metrics", padding="10")
        metrics_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Key evolution indicators
        self.evolution_vars = {}
        evolution_items = [
            ('Teacher Model', 'teacher', '#3498db'),
            ('Executor Model', 'executor', '#e74c3c'),
            ('Tasks Completed', 'tasks', '#27ae60'),
            ('Success Rate', 'success', '#f39c12'),
            ('Current Difficulty', 'difficulty', '#9b59b6'),
            ('Active Domain', 'domain', '#1abc9c')
        ]
        
        for i, (label, key, color) in enumerate(evolution_items):
            frame = ttk.Frame(metrics_frame)
            frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=2)
            
            self.evolution_vars[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", font=("Arial", 10, "bold"))
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.evolution_vars[key], 
                                   font=("Arial", 10), foreground=color)
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Co-evolution process frame
        process_frame = ttk.LabelFrame(evolution_frame, text="Co-Evolution Process", padding="10")
        process_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Process visualization
        self.process_text = scrolledtext.ScrolledText(process_frame, height=8, width=50, wrap=tk.WORD)
        self.process_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure process text colors
        self.process_text.tag_configure('teacher', foreground='#3498db', font=('Arial', 9, 'bold'))
        self.process_text.tag_configure('executor', foreground='#e74c3c', font=('Arial', 9, 'bold'))
        self.process_text.tag_configure('success', foreground='#27ae60', font=('Arial', 9))
        self.process_text.tag_configure('failure', foreground='#e74c3c', font=('Arial', 9))
        self.process_text.tag_configure('tool', foreground='#f39c12', font=('Arial', 9))
        
        # Quick actions
        actions_frame = ttk.LabelFrame(evolution_frame, text="Quick Actions", padding="10")
        actions_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        action_buttons = [
            ("Start Evolution", self.start_evolution),
            ("Pause Evolution", self.pause_evolution),
            ("Step Forward", self.step_evolution),
            ("Reset Evolution", self.reset_evolution)
        ]
        
        for i, (text, command) in enumerate(action_buttons):
            btn = ttk.Button(actions_frame, text=text, command=command, width=20)
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Recent evolution activity
        activity_frame = ttk.LabelFrame(evolution_frame, text="Recent Evolution Activity", padding="10")
        activity_frame.grid(row=0, column=1, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.activity_text = scrolledtext.ScrolledText(activity_frame, height=15, width=50, wrap=tk.WORD)
        self.activity_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure activity text colors
        self.activity_text.tag_configure('teacher_action', foreground='#3498db')
        self.activity_text.tag_configure('executor_action', foreground='#e74c3c')
        self.activity_text.tag_configure('success', foreground='#27ae60')
        self.activity_text.tag_configure('failure', foreground='#e74c3c')
        self.activity_text.tag_configure('tool_usage', foreground='#f39c12')
        
        # Grid configuration
        evolution_frame.columnconfigure(0, weight=1)
        evolution_frame.columnconfigure(1, weight=2)
        evolution_frame.rowconfigure(0, weight=1)
        evolution_frame.rowconfigure(1, weight=1)
        
    def create_agents_tab(self):
        """Create the agents detail tab."""
        agents_frame = ttk.Frame(self.notebook)
        self.notebook.add(agents_frame, text="Agents")
        
        # Teacher agent frame
        teacher_frame = ttk.LabelFrame(agents_frame, text="Teacher Agent (Curriculum Generator)", padding="10")
        teacher_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.teacher_vars = {}
        teacher_items = [
            ('Model', 'teacher_model', '#3498db'),
            ('Tasks Generated', 'teacher_tasks', '#3498db'),
            ('Avg Difficulty', 'teacher_difficulty', '#3498db'),
            ('Success Rate', 'teacher_success', '#3498db'),
            ('Domain Expertise', 'teacher_domain', '#3498db')
        ]
        
        for i, (label, key, color) in enumerate(teacher_items):
            frame = ttk.Frame(teacher_frame)
            frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=2)
            
            self.teacher_vars[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", font=("Arial", 10, "bold"))
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.teacher_vars[key], 
                                   font=("Arial", 10), foreground=color)
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Teacher behavior display
        self.teacher_behavior_text = scrolledtext.ScrolledText(teacher_frame, height=8, width=40, wrap=tk.WORD)
        self.teacher_behavior_text.grid(row=len(teacher_items), column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        # Executor agent frame
        executor_frame = ttk.LabelFrame(agents_frame, text="Executor Agent (Task Solver)", padding="10")
        executor_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.executor_vars = {}
        executor_items = [
            ('Model', 'executor_model', '#e74c3c'),
            ('Tasks Attempted', 'executor_tasks', '#e74c3c'),
            ('Success Rate', 'executor_success', '#e74c3c'),
            ('Tool Usage Rate', 'executor_tools', '#e74c3c'),
            ('Learning Progress', 'executor_learning', '#e74c3c')
        ]
        
        for i, (label, key, color) in enumerate(executor_items):
            frame = ttk.Frame(executor_frame)
            frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=2)
            
            self.executor_vars[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", font=("Arial", 10, "bold"))
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.executor_vars[key], 
                                   font=("Arial", 10), foreground=color)
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Executor behavior display
        self.executor_behavior_text = scrolledtext.ScrolledText(executor_frame, height=8, width=40, wrap=tk.WORD)
        self.executor_behavior_text.grid(row=len(executor_items), column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        # Agent interaction frame
        interaction_frame = ttk.LabelFrame(agents_frame, text="Agent Interaction", padding="10")
        interaction_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.interaction_text = scrolledtext.ScrolledText(interaction_frame, height=10, width=80, wrap=tk.WORD)
        self.interaction_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure interaction text colors
        self.interaction_text.tag_configure('teacher', foreground='#3498db', font=('Arial', 9, 'bold'))
        self.interaction_text.tag_configure('executor', foreground='#e74c3c', font=('Arial', 9, 'bold'))
        self.interaction_text.tag_configure('task', foreground='#27ae60', font=('Arial', 9))
        self.interaction_text.tag_configure('result', foreground='#f39c12', font=('Arial', 9))
        self.interaction_text.tag_configure('feedback', foreground='#9b59b6', font=('Arial', 9))
        
        # Grid configuration
        agents_frame.columnconfigure(0, weight=1)
        agents_frame.columnconfigure(1, weight=1)
        agents_frame.rowconfigure(0, weight=1)
        
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
            
            label_widget = ttk.Label(frame, text=f"{label}:", font=("Arial", 10, "bold"))
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.curriculum_vars[key], 
                                   font=("Arial", 10), foreground=color)
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Task generation frame
        generation_frame = ttk.LabelFrame(curriculum_frame, text="Task Generation", padding="10")
        generation_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.generation_text = scrolledtext.ScrolledText(generation_frame, height=8, width=40, wrap=tk.WORD)
        self.generation_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Curriculum history frame
        history_frame = ttk.LabelFrame(curriculum_frame, text="Curriculum History", padding="10")
        history_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.history_text = scrolledtext.ScrolledText(history_frame, height=15, width=50, wrap=tk.WORD)
        self.history_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure history text colors
        self.history_text.tag_configure('domain_switch', foreground='#1abc9c', font=('Arial', 9, 'bold'))
        self.history_text.tag_configure('difficulty_change', foreground='#f39c12', font=('Arial', 9, 'bold'))
        self.history_text.tag_configure('success_feedback', foreground='#27ae60', font=('Arial', 9))
        self.history_text.tag_configure('failure_feedback', foreground='#e74c3c', font=('Arial', 9))
        
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
            
            label_widget = ttk.Label(frame, text=f"{label}:", font=("Arial", 10, "bold"))
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.performance_vars[key], 
                                   font=("Arial", 10), foreground=color)
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Learning progression frame
        progression_frame = ttk.LabelFrame(performance_frame, text="Learning Progression", padding="10")
        progression_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.progression_text = scrolledtext.ScrolledText(progression_frame, height=8, width=40, wrap=tk.WORD)
        self.progression_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Trend analysis frame
        trends_frame = ttk.LabelFrame(performance_frame, text="Trend Analysis", padding="10")
        trends_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.trends_text = scrolledtext.ScrolledText(trends_frame, height=15, width=50, wrap=tk.WORD)
        self.trends_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure trends text colors
        self.trends_text.tag_configure('improvement', foreground='#27ae60', font=('Arial', 9, 'bold'))
        self.trends_text.tag_configure('decline', foreground='#e74c3c', font=('Arial', 9, 'bold'))
        self.trends_text.tag_configure('stable', foreground='#95a5a6', font=('Arial', 9))
        self.trends_text.tag_configure('insight', foreground='#f39c12', font=('Arial', 9, 'bold'))
        
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
            
            label_widget = ttk.Label(frame, text=f"{label}:", font=("Arial", 10, "bold"))
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.tools_vars[key], 
                                   font=("Arial", 10), foreground=color)
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Reasoning patterns frame
        reasoning_frame = ttk.LabelFrame(tools_frame, text="Reasoning Patterns", padding="10")
        reasoning_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.reasoning_text = scrolledtext.ScrolledText(reasoning_frame, height=8, width=40, wrap=tk.WORD)
        self.reasoning_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Recent tool calls frame
        calls_frame = ttk.LabelFrame(tools_frame, text="Recent Tool Calls", padding="10")
        calls_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.calls_text = scrolledtext.ScrolledText(calls_frame, height=15, width=50, wrap=tk.WORD)
        self.calls_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure calls text colors
        self.calls_text.tag_configure('tool_call', foreground='#f39c12', font=('Arial', 9, 'bold'))
        self.calls_text.tag_configure('tool_result', foreground='#27ae60', font=('Arial', 9))
        self.calls_text.tag_configure('tool_error', foreground='#e74c3c', font=('Arial', 9))
        self.calls_text.tag_configure('reasoning', foreground='#9b59b6', font=('Arial', 9))
        
        # Grid configuration
        tools_frame.columnconfigure(0, weight=1)
        tools_frame.columnconfigure(1, weight=2)
        tools_frame.rowconfigure(0, weight=1)
        tools_frame.rowconfigure(1, weight=1)
        
    def create_status_bar(self, parent):
        """Create the status bar."""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        self.evolution_status_var = tk.StringVar(value="Evolution: Stopped")
        self.last_update_var = tk.StringVar(value="Never")
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.grid(row=0, column=0, sticky=tk.W)
        
        evolution_status_label = ttk.Label(status_frame, textvariable=self.evolution_status_var)
        evolution_status_label.grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        last_update_label = ttk.Label(status_frame, textvariable=self.last_update_var)
        last_update_label.grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        
        # Progress indicator
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var,
                                          mode='indeterminate')
        self.progress_bar.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=(20, 0))
        
        status_frame.columnconfigure(3, weight=1)
        
    def start_monitoring(self):
        """Start monitoring the agent evolution process."""
        self.monitoring_thread = threading.Thread(target=self.monitor_evolution, daemon=True)
        self.monitoring_thread.start()
        
    def monitor_evolution(self):
        """Monitor the agent evolution process in background."""
        while self.monitoring_active:
            try:
                # Simulate monitoring agent evolution
                self.simulate_evolution_data()
                
                # Update GUI
                self.root.after(0, self.refresh_evolution_display)
                
            except Exception as e:
                print(f"Error monitoring evolution: {e}")
            
            time.sleep(2)  # Update every 2 seconds
            
    def simulate_evolution_data(self):
        """Simulate evolution data for demonstration."""
        # Update agent state
        self.agent_state['tasks_completed'] += 1
        self.agent_state['success_rate'] = min(95.0, self.agent_state['success_rate'] + 0.5)
        self.agent_state['current_difficulty'] = min(0.9, self.agent_state['current_difficulty'] + 0.01)
        
        # Simulate domain rotation
        domains = ['math', 'logic', 'code']
        current_index = domains.index(self.agent_state['active_domain'])
        if self.agent_state['tasks_completed'] % 10 == 0:
            self.agent_state['active_domain'] = domains[(current_index + 1) % len(domains)]
        
        # Add evolution activity
        self.add_evolution_activity(f"Teacher generated {self.agent_state['active_domain']} task at difficulty {self.agent_state['current_difficulty']:.2f}", 'teacher_action')
        self.add_evolution_activity(f"Executor attempted task with tool integration", 'executor_action')
        
        if self.agent_state['tasks_completed'] % 3 == 0:
            self.add_evolution_activity(f"Task completed successfully! Success rate: {self.agent_state['success_rate']:.1f}%", 'success')
        else:
            self.add_evolution_activity(f"Task failed. Learning from experience...", 'failure')
        
        # Update evolution data
        self.evolution_data['task_history'].append({
            'task_id': f"task_{self.agent_state['tasks_completed']}",
            'domain': self.agent_state['active_domain'],
            'difficulty': self.agent_state['current_difficulty'],
            'success': self.agent_state['tasks_completed'] % 3 == 0
        })
        
        self.evolution_data['performance_trend'].append(self.agent_state['success_rate'])
        self.evolution_data['difficulty_progression'].append(self.agent_state['current_difficulty'])
        self.evolution_data['domain_distribution'][self.agent_state['active_domain']] += 1
        
    def refresh_evolution_display(self):
        """Refresh the evolution display with current data."""
        try:
            # Update evolution metrics
            self.evolution_vars['teacher'].set(f"{self.agent_state['teacher_model']}")
            self.evolution_vars['executor'].set(f"{self.agent_state['executor_model']}")
            self.evolution_vars['tasks'].set(f"{self.agent_state['tasks_completed']}")
            self.evolution_vars['success'].set(f"{self.agent_state['success_rate']:.1f}%")
            self.evolution_vars['difficulty'].set(f"{self.agent_state['current_difficulty']:.2f}")
            self.evolution_vars['domain'].set(f"{self.agent_state['active_domain']}")
            
            # Update teacher behavior
            self.teacher_vars['teacher_model'].set(f"{self.agent_state['teacher_model']}")
            self.teacher_vars['teacher_tasks'].set(f"{self.agent_state['tasks_completed']}")
            self.teacher_vars['teacher_difficulty'].set(f"{self.agent_state['current_difficulty']:.2f}")
            self.teacher_vars['teacher_success'].set(f"{self.agent_state['success_rate']:.1f}%")
            self.teacher_vars['teacher_domain'].set(f"{self.agent_state['active_domain']}")
            
            # Update executor behavior
            self.executor_vars['executor_model'].set(f"{self.agent_state['executor_model']}")
            self.executor_vars['executor_tasks'].set(f"{self.agent_state['tasks_completed']}")
            self.executor_vars['executor_success'].set(f"{self.agent_state['success_rate']:.1f}%")
            self.executor_vars['executor_tools'].set(f"{self.agent_state['tasks_completed'] * 0.7:.0f}")  # Simulated
            self.executor_vars['executor_learning'].set(f"{min(100.0, self.agent_state['success_rate']):.1f}%")
            
            # Update curriculum
            self.curriculum_vars['curriculum_domain'].set(f"{self.agent_state['active_domain']}")
            self.curriculum_vars['curriculum_difficulty'].set(f"{self.agent_state['current_difficulty']:.2f}")
            self.curriculum_vars['curriculum_frontier'].set(f"0.1")
            self.curriculum_vars['curriculum_target'].set(f"0.5")
            self.curriculum_vars['curriculum_domains'].set(f"math, logic, code")
            
            # Update performance
            self.performance_vars['overall_success'].set(f"{self.agent_state['success_rate']:.1f}%")
            self.performance_vars['math_success'].set(f"{self.agent_state['success_rate'] * 0.9:.1f}%")  # Simulated
            self.performance_vars['logic_success'].set(f"{self.agent_state['success_rate'] * 0.85:.1f}%")  # Simulated
            self.performance_vars['code_success'].set(f"{self.agent_state['success_rate'] * 0.8:.1f}%")  # Simulated
            self.performance_vars['avg_time'].set(f"{(10 - self.agent_state['current_difficulty'] * 5):.1f}s")  # Simulated
            self.performance_vars['tool_efficiency'].set(f"{85.0:.1f}%")  # Simulated
            
            # Update tools
            self.tools_vars['math_usage'].set(f"{self.agent_state['tasks_completed'] * 0.4:.0f}")  # Simulated
            self.tools_vars['python_usage'].set(f"{self.agent_state['tasks_completed'] * 0.6:.0f}")  # Simulated
            self.tools_vars['shell_usage'].set(f"{self.agent_state['tasks_completed'] * 0.1:.0f}")  # Simulated
            self.tools_vars['test_usage'].set(f"{self.agent_state['tasks_completed'] * 0.2:.0f}")  # Simulated
            self.tools_vars['tools_success'].set(f"{self.agent_state['success_rate']:.1f}%")
            self.tools_vars['tools_time'].set(f"{(8 - self.agent_state['current_difficulty'] * 3):.1f}s")  # Simulated
            
            # Update status bar
            self.evolution_status_var.set(f"Evolution: Active - {self.agent_state['tasks_completed']} tasks")
            self.last_update_var.set(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"Error refreshing evolution display: {e}")
            
    def add_evolution_activity(self, message, tag='info'):
        """Add activity to the evolution log."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.activity_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
            self.activity_text.see(tk.END)
            
            # Keep only last 100 lines
            lines = self.activity_text.get(1.0, tk.END).count('\n')
            if lines > 100:
                self.activity_text.delete(1.0, f"{lines-100}.0")
                
        except Exception as e:
            print(f"Error adding evolution activity: {e}")
            
    def start_evolution(self):
        """Start the evolution process."""
        self.agent_state['is_running'] = True
        self.add_evolution_activity("Starting agent evolution process...", 'info')
        self.evolution_status_var.set("Evolution: Starting...")
        
    def pause_evolution(self):
        """Pause the evolution process."""
        self.agent_state['is_running'] = False
        self.add_evolution_activity("Pausing agent evolution...", 'info')
        self.evolution_status_var.set("Evolution: Paused")
        
    def step_evolution(self):
        """Step forward in evolution."""
        self.add_evolution_activity("Stepping evolution forward...", 'info')
        # Force an update
        self.simulate_evolution_data()
        self.refresh_evolution_display()
        
    def reset_evolution(self):
        """Reset evolution to initial state."""
        self.agent_state = {
            'teacher_model': 'qwen2.5:3b',
            'executor_model': 'qwen2.5:7b',
            'tasks_completed': 0,
            'success_rate': 0.0,
            'current_difficulty': 0.5,
            'active_domain': 'math',
            'last_task': None,
            'last_result': None,
            'is_running': False
        }
        
        self.evolution_data = {
            'task_history': [],
            'performance_trend': [],
            'difficulty_progression': [],
            'domain_distribution': {'math': 0, 'logic': 0, 'code': 0},
            'tool_usage': {'math_engine': 0, 'python': 0, 'shell': 0}
        }
        
        self.activity_text.delete(1.0, tk.END)
        self.add_evolution_activity("Evolution reset to initial state", 'info')
        self.refresh_evolution_display()
        
    def create_status_bar(self, parent):
        """Create the status bar."""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        self.evolution_status_var = tk.StringVar(value="Evolution: Stopped")
        self.last_update_var = tk.StringVar(value="Never")
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.grid(row=0, column=0, sticky=tk.W)
        
        evolution_status_label = ttk.Label(status_frame, textvariable=self.evolution_status_var)
        evolution_status_label.grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        last_update_label = ttk.Label(status_frame, textvariable=self.last_update_var)
        last_update_label.grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        
        # Progress indicator
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var,
                                          mode='indeterminate')
        self.progress_bar.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=(20, 0))
        
        status_frame.columnconfigure(3, weight=1)
        
    def start_monitoring(self):
        """Start monitoring the agent evolution process."""
        self.monitoring_thread = threading.Thread(target=self.monitor_evolution, daemon=True)
        self.monitoring_thread.start()
        
    def monitor_evolution(self):
        """Monitor the agent evolution process in background."""
        while self.monitoring_active:
            try:
                # Simulate monitoring agent evolution
                self.simulate_evolution_data()
                
                # Update GUI
                self.root.after(0, self.refresh_evolution_display)
                
            except Exception as e:
                print(f"Error monitoring evolution: {e}")
            
            time.sleep(2)  # Update every 2 seconds
            
    def run(self):
        """Run the dashboard."""
        try:
            # Set up window close handler
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # Start the GUI
            self.root.mainloop()
            
        except KeyboardInterrupt:
            self.on_closing()
        except Exception as e:
            print(f"Dashboard error: {e}")
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
    """Main function to run the dashboard."""
    try:
        print("Starting Agent0 Evolution Dashboard...")
        dashboard = Agent0Dashboard()
        dashboard.run()
    except Exception as e:
        print(f"Failed to start dashboard: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()