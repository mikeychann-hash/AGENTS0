#!/usr/bin/env python3
"""
Agent0 Unified Main GUI - Single Window with Tabs
Fixed version with clean syntax
"""

import sys
import json
import time
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


class Agent0UnifiedGUI:
    """Unified GUI for Agent0 with all components in tabs."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Agent0 Unified Dashboard - Agent Co-Evolution System")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        
        # Initialize core system components
        self.initialize_system()
        
        # System state
        self.system_state = {
            'running': False,
            'coordinator': None,
            'tasks_completed': 0,
            'success_rate': 0.0,
            'current_difficulty': 0.5,
            'active_domain': 'math',
            'llm_connected': False
        }
        
        # Evolution tracking
        self.evolution_data = {
            'interaction_history': [],
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
        
    def initialize_system(self):
        """Initialize the core Agent0 system with direct LLM connection."""
        try:
            print("Initializing Agent0 system with direct LLM connection...")
            
            # Load configuration
            from agent0.config import load_config
            config = load_config("agent0/configs/3070ti.yaml")
            
            # Initialize security logger
            self.log_dir = Path("runs")
            self.security_logger = SecurityLogger(self.log_dir, enable_monitoring=True)
            
            print("✅ Security logger initialized")
            
            # Initialize coordinator
            print("Initializing coordinator...")
            self.coordinator = Coordinator(config)
            
            print("✅ Coordinator initialized successfully")
            
            # Set system as connected
            self.system_state['llm_connected'] = True
            self.system_state['teacher_model'] = config['models']['teacher']['model']
            self.system_state['executor_model'] = config['models']['student']['model']
            
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
        main_frame.pack(fill=tk.BOTH, expand=True)
        
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
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Title
        title_label = ttk.Label(header_frame, text="🤖 Agent0 Unified Dashboard", 
                               style='Header.TLabel')
        title_label.pack(side=tk.LEFT)
        
        # System status indicator
        self.status_indicator = ttk.Label(header_frame, text="🟢 SYSTEM READY", 
                                        style='Section.TLabel', font=('Arial', 10, 'bold'))
        self.status_indicator.pack(side=tk.RIGHT, padx=(0, 20))
        
        # Subtitle
        subtitle_label = ttk.Label(header_frame, text="Self-evolving agents through teacher-executor co-evolution with tool integration", 
                                  style='Section.TLabel', font=('Arial', 10))
        subtitle_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Control buttons
        control_frame = ttk.Frame(header_frame, style='Main.TFrame')
        control_frame.pack(side=tk.RIGHT)
        
        self.start_btn = ttk.Button(control_frame, text="Start Evolution", 
                                   command=self.start_evolution, style='Success.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(control_frame, text="Stop Evolution", 
                                  command=self.stop_evolution, style='Danger.TButton')
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.step_btn = ttk.Button(control_frame, text="Step Forward", 
                                  command=self.step_evolution, style='Main.TButton')
        self.step_btn.pack(side=tk.LEFT)
        
    def create_main_content(self, parent):
        """Create the main content with notebook tabs."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
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
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
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
            frame.pack(fill=tk.X, pady=3, padx=5)
            
            self.overview_vars[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", style='Metric.TLabel')
            label_widget.pack(side=tk.LEFT, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.overview_vars[key], 
                                   style='Value.TLabel')
            value_widget.pack(side=tk.LEFT)
        
        # Quick actions frame
        actions_frame = ttk.LabelFrame(overview_frame, text="Quick Actions", padding="10")
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Evolution control buttons
        main_controls = [
            ("Start Evolution", self.start_evolution, 'Success.TButton'),
            ("Pause Evolution", self.pause_evolution, 'Main.TButton'),
            ("Step Forward", self.step_evolution, 'Main.TButton'),
            ("Reset System", self.reset_system, 'Danger.TButton')
        ]
        
        for i, (text, command, style) in enumerate(main_controls):
            btn = ttk.Button(actions_frame, text=text, command=command, style=style, width=20)
            btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Real-time activity frame
        activity_frame = ttk.LabelFrame(overview_frame, text="Real-Time Activity", padding="10")
        activity_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.overview_activity = scrolledtext.ScrolledText(activity_frame, height=10, width=50, wrap=tk.WORD)
        self.overview_activity.pack(fill=tk.BOTH, expand=True)
        
        # Configure activity text colors
        self.overview_activity.tag_configure('teacher', foreground='#3498db', font=('Arial', 9, 'bold'))
        self.overview_activity.tag_configure('executor', foreground='#e74c3c', font=('Arial', 9, 'bold'))
        self.overview_activity.tag_configure('success', foreground='#27ae60', font=('Arial', 9))
        self.overview_activity.tag_configure('failure', foreground='#e74c3c', font=('Arial', 9))
        self.overview_activity.tag_configure('tool', foreground='#f39c12', font=('Arial', 9))
        
    def create_evolution_tab(self):
        """Create the evolution process tab."""
        evolution_frame = ttk.Frame(self.notebook)
        self.notebook.add(evolution_frame, text="Evolution Process")
        
        # Evolution metrics frame
        metrics_frame = ttk.LabelFrame(evolution_frame, text="Evolution Metrics", padding="10")
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.LEFT)
        
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
            frame.pack(fill=tk.X, pady=3, padx=5)
            
            self.evolution_vars[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", style='Metric.TLabel')
            label_widget.pack(side=tk.LEFT, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.evolution_vars[key], 
                                   style='Value.TLabel')
            value_widget.pack(side=tk.LEFT)
        
        # Evolution process display
        process_frame = ttk.LabelFrame(evolution_frame, text="Evolution Process", padding="10")
        process_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.RIGHT)
        
        self.evolution_process = scrolledtext.ScrolledText(process_frame, height=10, width=40, wrap=tk.WORD)
        self.evolution_process.pack(fill=tk.BOTH, expand=True)
        
        # Configure process text colors
        self.evolution_process.tag_configure('teacher', foreground='#3498db', font=('Arial', 9, 'bold'))
        self.evolution_process.tag_configure('executor', foreground='#e74c3c', font=('Arial', 9, 'bold'))
        self.evolution_process.tag_configure('success', foreground='#27ae60', font=('Arial', 9))
        self.evolution_process.tag_configure('failure', foreground='#e74c3c', font=('Arial', 9))
        self.evolution_process.tag_configure('tool', foreground='#f39c12', font=('Arial', 9))
        
    def create_status_bar(self, parent):
        """Create the status bar."""
        status_frame = ttk.Frame(parent, style='Main.TFrame')
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        self.evolution_status_var = tk.StringVar(value="Evolution: Stopped")
        self.last_update_var = tk.StringVar(value="Never")
        self.llm_status_var = tk.StringVar(value="LLM: Connecting...")
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)
        
        evolution_status_label = ttk.Label(status_frame, textvariable=self.evolution_status_var)
        evolution_status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        llm_status_label = ttk.Label(status_frame, textvariable=self.llm_status_var)
        llm_status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Progress indicator
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, mode='indeterminate')
        self.progress_bar.pack(side=tk.LEFT, padx=(20, 0), fill=tk.X, expand=True)
        
    def start_monitoring(self):
        """Start monitoring the system."""
        self.monitoring_thread = threading.Thread(target=self.monitor_system, daemon=True)
        self.monitoring_thread.start()
        
    def monitor_system(self):
        """Monitor the system in background."""
        while self.monitoring_active:
            try:
                # Simulate system monitoring
                self.simulate_system_data()
                
                # Update GUI
                self.root.after(0, self.refresh_display)
                
            except Exception as e:
                print(f"Error monitoring system: {e}")
            
            time.sleep(2)  # Update every 2 seconds
            
    def simulate_system_data(self):
        """Simulate system data for demonstration."""
        # Update system state
        self.system_state['tasks_completed'] += 1
        self.system_state['success_rate'] = min(95.0, self.system_state['success_rate'] + 0.5)
        self.system_state['current_difficulty'] = min(0.9, self.system_state['current_difficulty'] + 0.01)
        
        # Simulate domain rotation
        domains = ['math', 'logic', 'code']
        current_index = domains.index(self.system_state['active_domain'])
        if self.system_state['tasks_completed'] % 10 == 0:
            self.system_state['active_domain'] = domains[(current_index + 1) % len(domains)]
        
        # Add activity
        self.add_activity(f"Teacher generated {self.system_state['active_domain']} task at difficulty {self.system_state['current_difficulty']:.3f}", 'teacher')
        self.add_activity(f"Executor attempted task with tool integration", 'executor')
        
        if self.system_state['tasks_completed'] % 3 == 0:
            self.add_activity(f"Task completed successfully! Success rate: {self.system_state['success_rate']:.1f}%", 'success')
        else:
            self.add_activity(f"Task failed. Learning from experience...", 'failure')
        
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
        """Refresh the display with current data."""
        try:
            # Update overview
            self.overview_vars['teacher_model'].set(f"{self.system_state['teacher_model']}")
            self.overview_vars['executor_model'].set(f"{self.system_state['executor_model']}")
            self.overview_vars['tasks_completed'].set(f"{self.system_state['tasks_completed']}")
            self.overview_vars['success_rate'].set(f"{self.system_state['success_rate']:.1f}%")
            self.overview_vars['current_difficulty'].set(f"{self.system_state['current_difficulty']:.3f}")
            self.overview_vars['active_domain'].set(f"{self.system_state['active_domain']}")
            
            # Update evolution
            self.evolution_vars['coevolution_cycles'].set(f"{len(self.evolution_data['task_history'])}")
            self.evolution_vars['success_trend'].set(f"{self.system_state['success_rate']:.1f}% ↑")
            self.evolution_vars['difficulty_progress'].set(f"{self.system_state['current_difficulty']:.3f} ↑")
            self.evolution_vars['learning_velocity'].set(f"{(self.system_state['success_rate'] / max(1, len(self.evolution_data['task_history'])) * 10):.2f}")
            self.evolution_vars['domain_dist'].set(f"Math: {self.evolution_data['domain_distribution']['math']}, Logic: {self.evolution_data['domain_distribution']['logic']}, Code: {self.evolution_data['domain_distribution']['code']}")
            self.evolution_vars['tool_efficiency'].set(f"{85.0:.1f}%")  # Simulated
            
            # Update status bar
            self.evolution_status_var.set(f"Evolution: Active - {self.system_state['tasks_completed']} tasks")
            self.last_update_var.set(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
            
            # Update status indicator
            if self.system_state['success_rate'] > 80:
                self.status_indicator.config(text="🟢 SYSTEM EXCELLENT", foreground='#27ae60')
            elif self.system_state['success_rate'] > 60:
                self.status_indicator.config(text="🟡 SYSTEM GOOD", foreground='#f39c12')
            else:
                self.status_indicator.config(text="🔴 SYSTEM NEEDS ATTENTION", foreground='#e74c3c')
            
        except Exception as e:
            print(f"Error refreshing display: {e}")
            
    def add_activity(self, message, tag='info'):
        """Add activity to the activity logs."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Add to overview activity
            self.overview_activity.insert(tk.END, f"[{timestamp}] {message}\n", tag)
            self.overview_activity.see(tk.END)
            
            # Keep only last 100 lines
            lines = self.overview_activity.get(1.0, tk.END).count('\n')
            if lines > 100:
                self.overview_activity.delete(1.0, f"{lines-100}.0")
                
        except Exception as e:
            print(f"Error adding activity: {e}")
            
    def start_evolution(self):
        """Start the evolution process."""
        if not self.system_state['running']:
            self.system_state['running'] = True
            self.add_activity("Starting agent evolution process...", 'info')
            self.evolution_status_var.set("Evolution: Active")
            self.status_indicator.config(text="🟡 EVOLVING", foreground='#f39c12')
            
            # Start background evolution
            self.evolution_thread = threading.Thread(target=self.run_evolution_loop, daemon=True)
            self.evolution_thread.start()
            
    def stop_evolution(self):
        """Stop the evolution process."""
        if self.system_state['running']:
            self.system_state['running'] = False
            self.add_activity("Stopping agent evolution...", 'info')
            self.evolution_status_var.set("Evolution: Stopped")
            self.status_indicator.config(text="🔴 STOPPED", foreground='#e74c3c')
            
    def step_evolution(self):
        """Step forward in evolution."""
        self.add_activity("Stepping evolution forward...", 'info')
        # Force an update
        self.simulate_system_data()
        self.refresh_display()
            
    def reset_system(self):
        """Reset the system to initial state."""
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset the system?"):
            self.add_activity("Resetting system to initial state...", 'info')
            
            # Reset system state
            self.system_state = {
                'running': False,
                'tasks_completed': 0,
                'success_rate': 0.0,
                'current_difficulty': 0.5,
                'active_domain': 'math',
                'llm_connected': False
            }
            
            # Clear all text widgets
            for text_widget in [self.overview_activity, self.evolution_process]:
                text_widget.delete(1.0, tk.END)
            
            self.add_activity("System reset to initial state", 'info')
            self.refresh_display()
            self.status_indicator.config(text="🟢 SYSTEM READY", foreground='#27ae60')
            
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