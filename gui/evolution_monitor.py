#!/usr/bin/env python3
"""
Agent0 Evolution Monitor - Agent Co-evolution Tracking
Focuses on the teacher-executor co-evolution process and learning dynamics
"""

import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
    import tkinter.font as tkfont
except ImportError:
    print("Error: tkinter not available. Please install python3-tk")
    sys.exit(1)


class EvolutionMonitor:
    """Monitor for tracking Agent0's teacher-executor co-evolution process."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Agent0 Evolution Monitor - Co-evolution Tracking")
        self.root.geometry("1000x700")
        self.root.configure(bg='#2c3e50')  # Dark theme for monitoring
        
        # Evolution state
        self.evolution_state = {
            'teacher_model': 'qwen2.5:3b',
            'executor_model': 'qwen2.5:7b',
            'co_evolution_cycle': 0,
            'teacher_tasks_generated': 0,
            'executor_tasks_attempted': 0,
            'success_rate': 0.0,
            'current_difficulty': 0.5,
            'active_domain': 'math',
            'last_interaction': None,
            'is_evolution_active': False
        }
        
        # Co-evolution tracking
        self.co_evolution_data = {
            'interaction_history': [],
            'difficulty_progression': [],
            'domain_evolution': {'math': 0, 'logic': 0, 'code': 0},
            'teacher_adaptations': [],
            'executor_improvements': [],
            'tool_integration': {'math_engine': 0, 'python': 0, 'shell': 0}
        }
        
        # Setup GUI
        self.setup_gui()
        
        # Start monitoring
        self.monitoring_active = True
        self.start_monitoring()
        
    def setup_gui(self):
        """Set up the evolution monitoring GUI."""
        # Configure style for dark theme
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('Evolution.TFrame', background='#2c3e50')
        style.configure('Teacher.TFrame', background='#3498db')
        style.configure('Executor.TFrame', background='#e74c3c')
        style.configure('CoEvolution.TLabel', background='#2c3e50', foreground='white', font=('Arial', 12, 'bold'))
        style.configure('Header.TLabel', background='#2c3e50', foreground='#ecf0f1', font=('Arial', 16, 'bold'))
        style.configure('Evolution.TButton', background='#34495e', foreground='white')
        
        # Create main container
        main_frame = ttk.Frame(self.root, style='Evolution.TFrame', padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Create header with co-evolution status
        self.create_header(main_frame)
        
        # Create main content
        self.create_main_content(main_frame)
        
        # Create status bar
        self.create_status_bar(main_frame)
        
    def create_header(self, parent):
        """Create the header with co-evolution status indicator."""
        header_frame = ttk.Frame(parent, style='Evolution.TFrame')
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Title
        title_label = ttk.Label(header_frame, text="🔄 Agent0 Evolution Monitor", 
                               style='Header.TLabel', font=('Arial', 18, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Co-evolution status indicator
        self.coevolution_frame = ttk.Frame(header_frame, relief=tk.RAISED, borderwidth=3)
        self.coevolution_frame.grid(row=0, column=1, sticky=tk.E, padx=(0, 20))
        
        self.coevolution_label = ttk.Label(self.coevolution_frame, text="CO-EVOLUTION: ACTIVE", 
                                         font=('Arial', 14, 'bold'), foreground='white',
                                         background='#27ae60')
        self.coevolution_label.grid(row=0, column=0, padx=20, pady=10)
        
        # Cycle counter
        self.cycle_label = ttk.Label(header_frame, text="Cycle: 0", 
                                   style='CoEvolution.TLabel', font=('Arial', 10))
        self.cycle_label.grid(row=1, column=1, sticky=tk.E, padx=(0, 20))
        
        # Subtitle
        subtitle_label = ttk.Label(header_frame, text="Teacher ↔ Executor Co-evolution Tracking", 
                                  style='CoEvolution.TLabel', font=('Arial', 10))
        subtitle_label.grid(row=1, column=0, sticky=tk.W)
        
    def create_main_content(self, parent):
        """Create the main content area."""
        # Create paned window for resizable sections
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Left panel - Agent metrics
        metrics_frame = ttk.Frame(paned, style='Evolution.TFrame')
        paned.add(metrics_frame, weight=1)
        
        self.create_metrics_panel(metrics_frame)
        
        # Right panel - Co-evolution dynamics
        dynamics_frame = ttk.Frame(paned, style='Evolution.TFrame')
        paned.add(dynamics_frame, weight=2)
        
        self.create_dynamics_panel(dynamics_frame)
        
    def create_metrics_panel(self, parent):
        """Create the agent metrics panel."""
        # Title
        title_label = ttk.Label(parent, text="Agent Metrics", 
                               style='CoEvolution.TLabel', font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Teacher metrics
        teacher_frame = ttk.LabelFrame(parent, text="Teacher Agent (Curriculum)", padding="10",
                                     style='Teacher.TFrame')
        teacher_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.teacher_metrics = {}
        teacher_items = [
            ('Model', 'teacher_model', '#3498db'),
            ('Tasks Generated', 'teacher_tasks', '#3498db'),
            ('Avg Difficulty', 'teacher_difficulty', '#3498db'),
            ('Domain Expertise', 'teacher_domain', '#3498db'),
            ('Adaptation Rate', 'teacher_adaptation', '#3498db')
        ]
        
        for i, (label, key, color) in enumerate(teacher_items):
            frame = ttk.Frame(teacher_frame)
            frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=3, padx=5)
            
            self.teacher_metrics[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", font=("Arial", 10, "bold"))
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.teacher_metrics[key], 
                                   font=("Arial", 10), foreground=color)
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Executor metrics
        executor_frame = ttk.LabelFrame(parent, text="Executor Agent (Solver)", padding="10",
                                        style='Executor.TFrame')
        executor_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.executor_metrics = {}
        executor_items = [
            ('Model', 'executor_model', '#e74c3c'),
            ('Tasks Attempted', 'executor_tasks', '#e74c3c'),
            ('Success Rate', 'executor_success', '#e74c3c'),
            ('Tool Usage Rate', 'executor_tools', '#e74c3c'),
            ('Learning Progress', 'executor_learning', '#e74c3c')
        ]
        
        for i, (label, key, color) in enumerate(executor_items):
            frame = ttk.Frame(executor_frame)
            frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=3, padx=5)
            
            self.executor_metrics[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", font=("Arial", 10, "bold"))
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.executor_metrics[key], 
                                   font=("Arial", 10), foreground=color)
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Co-evolution metrics
        coevolution_frame = ttk.LabelFrame(parent, text="Co-Evolution Metrics", padding="10",
                                         style='Evolution.TFrame')
        coevolution_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.coevolution_metrics = {}
        coevolution_items = [
            ('Co-Evolution Cycles', 'coevolution_cycles', '#27ae60'),
            ('Success Rate Trend', 'success_trend', '#27ae60'),
            ('Difficulty Progression', 'difficulty_progress', '#27ae60'),
            ('Domain Distribution', 'domain_dist', '#27ae60'),
            ('Learning Velocity', 'learning_velocity', '#27ae60')
        ]
        
        for i, (label, key, color) in enumerate(coevolution_items):
            frame = ttk.Frame(coevolution_frame)
            frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=3, padx=5)
            
            self.coevolution_metrics[key] = tk.StringVar(value="Loading...")
            
            label_widget = ttk.Label(frame, text=f"{label}:", font=("Arial", 10, "bold"))
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.coevolution_metrics[key], 
                                   font=("Arial", 10), foreground=color)
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
    def create_dynamics_panel(self, parent):
        """Create the co-evolution dynamics panel."""
        # Title
        title_label = ttk.Label(parent, text="Co-Evolution Dynamics", 
                               style='CoEvolution.TLabel', font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Real-time interaction display
        interaction_frame = ttk.LabelFrame(parent, text="Real-Time Agent Interactions", padding="10",
                                         style='Evolution.TFrame')
        interaction_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.interaction_text = scrolledtext.ScrolledText(interaction_frame, height=20, width=60, wrap=tk.WORD)
        self.interaction_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure interaction text colors for teacher vs executor
        self.interaction_text.tag_configure('teacher_action', foreground='#3498db', font=('Arial', 9, 'bold'))
        self.interaction_text.tag_configure('executor_action', foreground='#e74c3c', font=('Arial', 9, 'bold'))
        self.interaction_text.tag_configure('task_generation', foreground='#27ae60', font=('Arial', 9))
        self.interaction_text.tag_configure('solution_attempt', foreground='#f39c12', font=('Arial', 9))
        self.interaction_text.tag_configure('feedback_loop', foreground='#9b59b6', font=('Arial', 9))
        self.interaction_text.tag_configure('adaptation', foreground='#1abc9c', font=('Arial', 9, 'bold'))
        
        # Learning dynamics frame
        dynamics_frame = ttk.LabelFrame(parent, text="Learning Dynamics", padding="10",
                                      style='Evolution.TFrame')
        dynamics_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.dynamics_text = scrolledtext.ScrolledText(dynamics_frame, height=10, width=60, wrap=tk.WORD)
        self.dynamics_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure dynamics text colors
        self.dynamics_text.tag_configure('difficulty_change', foreground='#f39c12', font=('Arial', 9, 'bold'))
        self.dynamics_text.tag_configure('domain_switch', foreground='#1abc9c', font=('Arial', 9, 'bold'))
        self.dynamics_text.tag_configure('tool_integration', foreground='#9b59b6', font=('Arial', 9))
        self.dynamics_text.tag_configure('reasoning_evolution', foreground='#34495e', font=('Arial', 9))
        
        # Grid configuration
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=3)  # Interactions get more space
        parent.rowconfigure(2, weight=2)  # Dynamics gets less space
        
    def create_status_bar(self, parent):
        """Create the status bar."""
        status_frame = ttk.Frame(parent, style='Evolution.TFrame')
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        self.evolution_status_var = tk.StringVar(value="Evolution: Monitoring")
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
        """Start monitoring the co-evolution process."""
        self.monitoring_thread = threading.Thread(target=self.monitor_coevolution, daemon=True)
        self.monitoring_thread.start()
        
    def monitor_coevolution(self):
        """Monitor the co-evolution process in background."""
        while self.monitoring_active:
            try:
                # Simulate co-evolution monitoring
                self.simulate_coevolution_data()
                
                # Update GUI
                self.root.after(0, self.refresh_coevolution_display)
                
            except Exception as e:
                print(f"Error monitoring co-evolution: {e}")
            
            time.sleep(2)  # Update every 2 seconds
            
    def simulate_coevolution_data(self):
        """Simulate co-evolution data for demonstration."""
        # Update evolution state
        self.evolution_state['co_evolution_cycle'] += 1
        self.evolution_state['teacher_tasks_generated'] += 1
        self.evolution_state['executor_tasks_attempted'] += 1
        self.evolution_state['success_rate'] = min(95.0, self.evolution_state['success_rate'] + 0.3)
        self.evolution_state['current_difficulty'] = min(0.9, self.evolution_state['current_difficulty'] + 0.005)
        self.evolution_state['is_evolution_active'] = True
        
        # Simulate domain rotation
        domains = ['math', 'logic', 'code']
        current_index = domains.index(self.evolution_state['active_domain'])
        if self.evolution_state['co_evolution_cycle'] % 15 == 0:
            self.evolution_state['active_domain'] = domains[(current_index + 1) % len(domains)]
            self.evolution_state['last_interaction'] = f"Domain switched to {self.evolution_state['active_domain']}"
        
        # Add co-evolution interactions
        self.add_interaction(f"Teacher proposes {self.evolution_state['active_domain']} task at difficulty {self.evolution_state['current_difficulty']:.3f}", 'teacher_action')
        self.add_interaction(f"Executor attempts solution with tool integration", 'executor_action')
        
        if self.evolution_state['co_evolution_cycle'] % 3 == 0:
            self.add_interaction(f"Task completed successfully! Success rate: {self.evolution_state['success_rate']:.1f}%", 'solution_attempt')
            self.add_dynamics(f"Teacher adapts curriculum based on executor performance", 'adaptation')
        else:
            self.add_interaction(f"Task failed. Teacher adjusts difficulty level", 'feedback_loop')
            self.add_dynamics(f"Difficulty decreased to {self.evolution_state['current_difficulty']:.3f} for learning", 'difficulty_change')
        
        # Update co-evolution data
        self.co_evolution_data['interaction_history'].append({
            'cycle': self.evolution_state['co_evolution_cycle'],
            'domain': self.evolution_state['active_domain'],
            'difficulty': self.evolution_state['current_difficulty'],
            'success': self.evolution_state['co_evolution_cycle'] % 3 == 0
        })
        
        self.co_evolution_data['difficulty_progression'].append(self.evolution_state['current_difficulty'])
        self.co_evolution_data['domain_evolution'][self.evolution_state['active_domain']] += 1
        
    def refresh_coevolution_display(self):
        """Refresh the co-evolution display with current data."""
        try:
            # Update metrics
            self.teacher_metrics['teacher_model'].set(f"{self.evolution_state['teacher_model']}")
            self.teacher_metrics['teacher_tasks'].set(f"{self.evolution_state['teacher_tasks_generated']}")
            self.teacher_metrics['teacher_difficulty'].set(f"{self.evolution_state['current_difficulty']:.3f}")
            self.teacher_metrics['teacher_domain'].set(f"{self.evolution_state['active_domain']}")
            self.teacher_metrics['teacher_adaptation'].set(f"{min(100.0, self.evolution_state['success_rate']):.1f}%")
            
            self.executor_metrics['executor_model'].set(f"{self.evolution_state['executor_model']}")
            self.executor_metrics['executor_tasks'].set(f"{self.evolution_state['executor_tasks_attempted']}")
            self.executor_metrics['executor_success'].set(f"{self.evolution_state['success_rate']:.1f}%")
            self.executor_metrics['executor_tools'].set(f"{self.evolution_state['executor_tasks_attempted'] * 0.7:.0f}")  # Simulated
            self.executor_metrics['executor_learning'].set(f"{min(100.0, self.evolution_state['success_rate']):.1f}%")
            
            self.coevolution_metrics['coevolution_cycles'].set(f"{self.evolution_state['co_evolution_cycle']}")
            self.coevolution_metrics['success_trend'].set(f"{self.evolution_state['success_rate']:.1f}% ↑")
            self.coevolution_metrics['difficulty_progress'].set(f"{self.evolution_state['current_difficulty']:.3f} ↑")
            self.coevolution_metrics['domain_dist'].set(f"Math: {self.co_evolution_data['domain_evolution']['math']}, Logic: {self.co_evolution_data['domain_evolution']['logic']}, Code: {self.co_evolution_data['domain_evolution']['code']}")
            self.coevolution_metrics['learning_velocity'].set(f"{(self.evolution_state['success_rate'] / max(1, self.evolution_state['co_evolution_cycle']) * 10):.2f}")  # Simulated
            
            # Update status bar
            self.evolution_status_var.set(f"Evolution: Active - Cycle {self.evolution_state['co_evolution_cycle']}")
            self.last_update_var.set(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"Error refreshing co-evolution display: {e}")
            
    def add_interaction(self, message, tag='info'):
        """Add interaction to the interaction log."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.interaction_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
            self.interaction_text.see(tk.END)
            
            # Keep only last 100 lines
            lines = self.interaction_text.get(1.0, tk.END).count('\n')
            if lines > 100:
                self.interaction_text.delete(1.0, f"{lines-100}.0")
                
        except Exception as e:
            print(f"Error adding interaction: {e}")
            
    def add_dynamics(self, message, tag='info'):
        """Add dynamics to the dynamics log."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.dynamics_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
            self.dynamics_text.see(tk.END)
            
            # Keep only last 50 lines
            lines = self.dynamics_text.get(1.0, tk.END).count('\n')
            if lines > 50:
                self.dynamics_text.delete(1.0, f"{lines-50}.0")
                
        except Exception as e:
            print(f"Error adding dynamics: {e}")
            
    def run(self):
        """Run the evolution monitor."""
        try:
            # Set up window close handler
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # Start monitoring
            self.root.mainloop()
            
        except KeyboardInterrupt:
            self.on_closing()
        except Exception as e:
            print(f"Evolution monitor error: {e}")
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
    """Main function to run the evolution monitor."""
    try:
        print("Starting Agent0 Evolution Monitor...")
        monitor = EvolutionMonitor()
        monitor.run()
    except Exception as e:
        print(f"Failed to start evolution monitor: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()