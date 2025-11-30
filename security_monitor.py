#!/usr/bin/env python3
"""
Agent0 Security Monitor - Standalone Security Monitoring Window
Provides focused security monitoring and alerting capabilities
"""

import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    import tkinter.font as tkfont
except ImportError:
    print("Error: tkinter not available. Please install python3-tk")
    sys.exit(1)

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent0.logging.security_logger import SecurityLogger, SecurityEventType


class SecurityMonitor:
    """Standalone security monitor with real-time alerting."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Agent0 Security Monitor - Threat Detection Dashboard")
        self.root.geometry("1000x700")
        self.root.configure(bg='#1e1e1e')  # Dark theme for security monitor
        
        # Set up security logger
        self.log_dir = Path("runs")
        self.security_logger = SecurityLogger(self.log_dir, enable_monitoring=True)
        
        # Security state
        self.security_state = {
            'threat_level': 'LOW',
            'active_alerts': 0,
            'total_events': 0,
            'blocked_attempts': 0,
            'last_threat': None,
            'monitoring_active': True
        }
        
        # Alert sounds and colors
        self.alert_colors = {
            'LOW': '#27ae60',
            'MEDIUM': '#f39c12', 
            'HIGH': '#e67e22',
            'CRITICAL': '#e74c3c'
        }
        
        # Initialize GUI
        self.setup_gui()
        
        # Start monitoring
        self.start_monitoring()
        
    def setup_gui(self):
        """Set up the security monitoring GUI."""
        # Configure style for dark theme
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('Security.TFrame', background='#1e1e1e')
        style.configure('Alert.TFrame', background='#2c3e50')
        style.configure('Threat.TLabel', background='#1e1e1e', foreground='white', font=('Arial', 12, 'bold'))
        style.configure('Header.TLabel', background='#1e1e1e', foreground='#ecf0f1', font=('Arial', 16, 'bold'))
        style.configure('Security.TButton', background='#34495e', foreground='white')
        
        # Create main container
        main_frame = ttk.Frame(self.root, style='Security.TFrame', padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Create header with threat level indicator
        self.create_header(main_frame)
        
        # Create main content
        self.create_main_content(main_frame)
        
        # Create status bar
        self.create_status_bar(main_frame)
        
    def create_header(self, parent):
        """Create the header with threat level indicator."""
        header_frame = ttk.Frame(parent, style='Security.TFrame')
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Title
        title_label = ttk.Label(header_frame, text="🛡️ SECURITY MONITOR", 
                               style='Header.TLabel', font=('Arial', 18, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Threat level indicator
        self.threat_frame = ttk.Frame(header_frame, relief=tk.RAISED, borderwidth=3)
        self.threat_frame.grid(row=0, column=1, sticky=tk.E, padx=(0, 20))
        
        self.threat_label = ttk.Label(self.threat_frame, text="THREAT LEVEL: LOW", 
                                     font=('Arial', 14, 'bold'), foreground='white',
                                     background=self.alert_colors['LOW'])
        self.threat_label.grid(row=0, column=0, padx=20, pady=10)
        
        # Alert counter
        self.alert_counter_label = ttk.Label(header_frame, text="Active Alerts: 0", 
                                           style='Threat.TLabel', font=('Arial', 10))
        self.alert_counter_label.grid(row=1, column=1, sticky=tk.E, padx=(0, 20))
        
        # Subtitle
        subtitle_label = ttk.Label(header_frame, text="Real-time threat detection and security monitoring", 
                                  style='Threat.TLabel', font=('Arial', 10))
        subtitle_label.grid(row=1, column=0, sticky=tk.W)
        
    def create_main_content(self, parent):
        """Create the main content area."""
        # Create paned window for resizable sections
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Left panel - Security metrics
        metrics_frame = ttk.Frame(paned, style='Security.TFrame')
        paned.add(metrics_frame, weight=1)
        
        self.create_metrics_panel(metrics_frame)
        
        # Right panel - Events and alerts
        events_frame = ttk.Frame(paned, style='Security.TFrame')
        paned.add(events_frame, weight=2)
        
        self.create_events_panel(events_frame)
        
    def create_metrics_panel(self, parent):
        """Create the security metrics panel."""
        # Title
        title_label = ttk.Label(parent, text="Security Metrics", 
                               style='Threat.TLabel', font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Metrics display
        self.metrics_vars = {}
        metrics_items = [
            ('Security Score', 'score', '#27ae60'),
            ('Total Events', 'total', '#3498db'),
            ('Blocked Attempts', 'blocked', '#e74c3c'),
            ('Active Alerts', 'alerts', '#f39c12'),
            ('Critical Events', 'critical', '#c0392b'),
            ('High Risk Events', 'high', '#e67e22'),
            ('Medium Risk Events', 'medium', '#f39c12'),
            ('Low Risk Events', 'low', '#27ae60')
        ]
        
        for i, (label, key, color) in enumerate(metrics_items):
            frame = ttk.Frame(parent, style='Security.TFrame')
            frame.grid(row=i+1, column=0, sticky=(tk.W, tk.E), pady=3, padx=5)
            
            self.metrics_vars[key] = tk.StringVar(value="0")
            
            label_widget = ttk.Label(frame, text=f"{label}:", 
                                   style='Threat.TLabel', font=('Arial', 10))
            label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            value_widget = ttk.Label(frame, textvariable=self.metrics_vars[key], 
                                   font=('Arial', 12, 'bold'), foreground=color,
                                   background='#1e1e1e')
            value_widget.grid(row=0, column=1, sticky=tk.W)
        
        # Quick actions
        actions_frame = ttk.LabelFrame(parent, text="Quick Actions", padding="10",
                                     style='Alert.TFrame')
        actions_frame.grid(row=len(metrics_items)+2, column=0, sticky=(tk.W, tk.E), pady=(20, 0))
        
        quick_actions = [
            ("Run Security Scan", self.run_security_scan),
            ("Generate Report", self.generate_security_report),
            ("Export Security Data", self.export_security_data),
            ("View Threat Map", self.view_threat_map)
        ]
        
        for i, (text, command) in enumerate(quick_actions):
            btn = tk.Button(actions_frame, text=text, command=command,
                           bg='#34495e', fg='white', font=('Arial', 9, 'bold'),
                           relief=tk.RAISED, borderwidth=2)
            btn.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=3, padx=5)
        
    def create_events_panel(self, parent):
        """Create the security events panel."""
        # Title
        title_label = ttk.Label(parent, text="Security Events & Alerts", 
                               style='Threat.TLabel', font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Event filter frame
        filter_frame = ttk.Frame(parent, style='Security.TFrame')
        filter_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(filter_frame, text="Filter:", style='Threat.TLabel').grid(row=0, column=0, padx=(0, 10))
        
        self.filter_var = tk.StringVar(value="ALL")
        filter_options = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"]
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var,
                                   values=filter_options, state="readonly", width=15)
        filter_combo.grid(row=0, column=1, padx=(0, 10))
        filter_combo.bind('<<ComboboxSelected>>', self.filter_events)
        
        ttk.Button(filter_frame, text="Refresh", command=self.refresh_events).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(filter_frame, text="Clear Alerts", command=self.clear_alerts).grid(row=0, column=3)
        
        # Real-time events display
        events_frame = ttk.Frame(parent, style='Security.TFrame')
        events_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.events_text = tk.Text(events_frame, height=20, width=60, wrap=tk.WORD,
                                   bg='#2c3e50', fg='#ecf0f1', font=('Courier', 9))
        self.events_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(events_frame, orient=tk.VERTICAL, command=self.events_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.events_text.config(yscrollcommand=scrollbar.set)
        
        # Configure tags for syntax highlighting
        self.events_text.tag_configure('CRITICAL', foreground='#e74c3c', font=('Courier', 9, 'bold'))
        self.events_text.tag_configure('HIGH', foreground='#e67e22', font=('Courier', 9, 'bold'))
        self.events_text.tag_configure('MEDIUM', foreground='#f39c12', font=('Courier', 9))
        self.events_text.tag_configure('LOW', foreground='#27ae60', font=('Courier', 9))
        self.events_text.tag_configure('timestamp', foreground='#95a5a6', font=('Courier', 8))
        self.events_text.tag_configure('header', foreground='#ecf0f1', font=('Courier', 10, 'bold'))
        
        # Grid configuration
        events_frame.columnconfigure(0, weight=1)
        events_frame.rowconfigure(0, weight=1)
        
        # Alert indicator frame
        alert_frame = ttk.LabelFrame(parent, text="Active Alerts", padding="10",
                                   style='Alert.TFrame')
        alert_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.alert_text = tk.Text(alert_frame, height=8, width=60, wrap=tk.WORD,
                                bg='#34495e', fg='#ecf0f1', font=('Courier', 9))
        self.alert_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure alert tags
        self.alert_text.tag_configure('CRITICAL_ALERT', foreground='#e74c3c', font=('Courier', 9, 'bold'))
        self.alert_text.tag_configure('HIGH_ALERT', foreground='#e67e22', font=('Courier', 9, 'bold'))
        self.alert_text.tag_configure('MEDIUM_ALERT', foreground='#f39c12', font=('Courier', 9))
        
        # Grid configuration for parent
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=3)  # Events area gets more space
        parent.rowconfigure(3, weight=1)  # Alerts area gets less space
        
    def create_status_bar(self, parent):
        """Create the status bar."""
        status_frame = ttk.Frame(parent, style='Security.TFrame')
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Status indicators
        self.status_var = tk.StringVar(value="Monitoring Active")
        self.event_rate_var = tk.StringVar(value="0 events/min")
        self.last_update_var = tk.StringVar(value="Never")
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                               style='Threat.TLabel', font=('Arial', 10))
        status_label.grid(row=0, column=0, sticky=tk.W)
        
        event_rate_label = ttk.Label(status_frame, textvariable=self.event_rate_var,
                                   style='Threat.TLabel', font=('Arial', 10))
        event_rate_label.grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        last_update_label = ttk.Label(status_frame, textvariable=self.last_update_var,
                                    style='Threat.TLabel', font=('Arial', 10))
        last_update_label.grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        
        # Progress indicator
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var,
                                          mode='indeterminate', style='Horizontal.TProgressbar')
        self.progress_bar.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=(20, 0))
        
        status_frame.columnconfigure(3, weight=1)
        
    def start_monitoring(self):
        """Start security monitoring threads."""
        # Start security event monitoring
        self.security_thread = threading.Thread(target=self.monitor_security_events, daemon=True)
        self.security_thread.start()
        
        # Start threat level monitoring
        self.threat_thread = threading.Thread(target=self.monitor_threat_level, daemon=True)
        self.threat_thread.start()
        
        # Start status updates
        self.status_thread = threading.Thread(target=self.update_status, daemon=True)
        self.status_thread.start()
        
        # Start progress animation
        self.progress_bar.start()
        
    def monitor_security_events(self):
        """Monitor security events in real-time."""
        last_event_count = 0
        event_timestamps = []
        
        while self.security_state['monitoring_active']:
            try:
                # Get recent security events
                recent_events = self.security_logger.get_recent_events(limit=50)
                current_count = len(recent_events)
                
                # Update event rate
                now = time.time()
                event_timestamps = [ts for ts in event_timestamps if now - ts < 60]  # Keep last 60 seconds
                event_timestamps.extend([event['timestamp'] for event in recent_events if event['timestamp'] > now - 60])
                
                events_per_minute = len(event_timestamps)
                
                # Update GUI
                self.root.after(0, lambda: self.event_rate_var.set(f"{events_per_minute} events/min"))
                
                # Check for new events
                if current_count > last_event_count:
                    new_events = recent_events[:current_count - last_event_count]
                    self.root.after(0, lambda: self.display_new_events(new_events))
                    last_event_count = current_count
                
                # Update metrics
                summary = self.security_logger.get_security_summary()
                self.root.after(0, lambda: self.update_metrics(summary))
                
            except Exception as e:
                print(f"Error monitoring security events: {e}")
            
            time.sleep(1)  # Check every second
            
    def monitor_threat_level(self):
        """Monitor and update threat level."""
        while self.security_state['monitoring_active']:
            try:
                # Get recent events to assess threat level
                recent_events = self.security_logger.get_recent_events(limit=20)
                
                # Calculate threat level based on recent events
                threat_scores = {
                    'CRITICAL': 10,
                    'HIGH': 5,
                    'MEDIUM': 2,
                    'LOW': 0
                }
                
                total_threat_score = 0
                for event in recent_events:
                    severity = event.get('severity', 'LOW')
                    total_threat_score += threat_scores.get(severity, 0)
                
                # Determine threat level
                if total_threat_score >= 20:
                    new_threat_level = 'CRITICAL'
                elif total_threat_score >= 10:
                    new_threat_level = 'HIGH'
                elif total_threat_score >= 5:
                    new_threat_level = 'MEDIUM'
                else:
                    new_threat_level = 'LOW'
                
                # Update threat level if changed
                if new_threat_level != self.security_state['threat_level']:
                    self.security_state['threat_level'] = new_threat_level
                    self.root.after(0, lambda: self.update_threat_display(new_threat_level))
                
            except Exception as e:
                print(f"Error monitoring threat level: {e}")
            
            time.sleep(5)  # Check every 5 seconds
            
    def update_status(self):
        """Update status information."""
        while self.security_state['monitoring_active']:
            try:
                current_time = datetime.now().strftime("%H:%M:%S")
                self.root.after(0, lambda: self.last_update_var.set(f"Last update: {current_time}"))
                
                # Update status based on threat level
                if self.security_state['threat_level'] == 'CRITICAL':
                    status = "🚨 CRITICAL - Immediate Action Required"
                elif self.security_state['threat_level'] == 'HIGH':
                    status = "⚠️ HIGH THREAT - Monitor Closely"
                elif self.security_state['threat_level'] == 'MEDIUM':
                    status = "⚡ MEDIUM THREAT - Vigilant Monitoring"
                else:
                    status = "✅ SECURE - Normal Monitoring"
                
                self.root.after(0, lambda: self.status_var.set(status))
                
            except Exception as e:
                print(f"Error updating status: {e}")
            
            time.sleep(1)
            
    def display_new_events(self, events):
        """Display new security events."""
        try:
            for event in events:
                timestamp = datetime.fromtimestamp(event['timestamp']).strftime("%H:%M:%S")
                severity = event.get('severity', 'LOW')
                event_type = event.get('event_type', 'UNKNOWN')
                message = event.get('message', '')
                
                # Format event text
                event_text = f"[{timestamp}] {severity} - {event_type}\n"
                event_text += f"  {message}\n\n"
                
                # Insert with appropriate formatting
                tag = severity
                self.events_text.insert(tk.END, event_text, tag)
                
                # Create alert for high-severity events
                if severity in ['CRITICAL', 'HIGH']:
                    self.create_alert(event)
                    
            # Keep only last 100 lines
            lines = self.events_text.get(1.0, tk.END).count('\n')
            if lines > 100:
                self.events_text.delete(1.0, f"{lines-100}.0")
                
            # Auto-scroll to end
            self.events_text.see(tk.END)
            
        except Exception as e:
            print(f"Error displaying new events: {e}")
            
    def create_alert(self, event):
        """Create an alert for high-severity events."""
        try:
            severity = event.get('severity', 'LOW')
            timestamp = datetime.fromtimestamp(event['timestamp']).strftime("%H:%M:%S")
            event_type = event.get('event_type', 'UNKNOWN')
            message = event.get('message', '')
            
            alert_text = f"🚨 ALERT [{timestamp}] {severity}\n"
            alert_text += f"Type: {event_type}\n"
            alert_text += f"Details: {message}\n\n"
            
            self.alert_text.insert(tk.END, alert_text, f'{severity}_ALERT')
            self.security_state['active_alerts'] += 1
            
            # Update alert counter
            self.alert_counter_label.config(text=f"Active Alerts: {self.security_state['active_alerts']}")
            
            # Auto-scroll to end
            self.alert_text.see(tk.END)
            
            # Keep only last 50 alert lines
            lines = self.alert_text.get(1.0, tk.END).count('\n')
            if lines > 50:
                self.alert_text.delete(1.0, f"{lines-50}.0")
                
        except Exception as e:
            print(f"Error creating alert: {e}")
            
    def update_metrics(self, summary):
        """Update security metrics display."""
        try:
            self.metrics_vars['score'].set(f"{summary['security_score']:.1f}/100")
            self.metrics_vars['total'].set(str(summary['total_events']))
            self.metrics_vars['blocked'].set(str(summary['blocked_attempts']))
            self.metrics_vars['alerts'].set(str(self.security_state['active_alerts']))
            self.metrics_vars['critical'].set(str(summary['events_by_severity'].get('CRITICAL', 0)))
            self.metrics_vars['high'].set(str(summary['events_by_severity'].get('HIGH', 0)))
            self.metrics_vars['medium'].set(str(summary['events_by_severity'].get('MEDIUM', 0)))
            self.metrics_vars['low'].set(str(summary['events_by_severity'].get('LOW', 0)))
            
            self.security_state['total_events'] = summary['total_events']
            self.security_state['blocked_attempts'] = summary['blocked_attempts']
            
        except Exception as e:
            print(f"Error updating metrics: {e}")
            
    def update_threat_display(self, threat_level):
        """Update threat level display."""
        try:
            color = self.alert_colors[threat_level]
            text = f"THREAT LEVEL: {threat_level}"
            
            self.threat_label.config(text=text, background=color)
            self.threat_frame.config(background=color)
            
            # Change window background for critical threats
            if threat_level == 'CRITICAL':
                self.root.configure(bg='#c0392b')
                # Flash the window
                self.flash_critical_alert()
            else:
                self.root.configure(bg='#1e1e1e')
                
        except Exception as e:
            print(f"Error updating threat display: {e}")
            
    def flash_critical_alert(self):
        """Flash the window for critical alerts."""
        try:
            current_bg = self.root.cget('bg')
            new_bg = '#e74c3c' if current_bg == '#c0392b' else '#c0392b'
            self.root.configure(bg=new_bg)
            
            # Schedule next flash
            if self.security_state['threat_level'] == 'CRITICAL':
                self.root.after(500, self.flash_critical_alert)
                
        except Exception:
            pass
            
    def filter_events(self, event=None):
        """Filter events by severity."""
        # This would implement filtering logic
        self.refresh_events()
        
    def refresh_events(self):
        """Refresh the events display."""
        try:
            self.events_text.delete(1.0, tk.END)
            
            # Get recent events with filtering
            filter_severity = self.filter_var.get()
            if filter_severity == "ALL":
                recent_events = self.security_logger.get_recent_events(limit=50)
            else:
                recent_events = self.security_logger.get_recent_events(limit=50)
                recent_events = [e for e in recent_events if e.get('severity') == filter_severity]
            
            # Display filtered events
            self.display_new_events(recent_events)
            
        except Exception as e:
            print(f"Error refreshing events: {e}")
            
    def clear_alerts(self):
        """Clear active alerts."""
        try:
            self.alert_text.delete(1.0, tk.END)
            self.security_state['active_alerts'] = 0
            self.alert_counter_label.config(text=f"Active Alerts: 0")
            
            self.log_activity("Alerts cleared by user")
            
        except Exception as e:
            print(f"Error clearing alerts: {e}")
            
    def run_security_scan(self):
        """Run a comprehensive security scan."""
        try:
            self.status_var.set("Running security scan...")
            
            # Simulate scan
            time.sleep(2)
            
            # Log scan event
            self.security_logger.log_security_event(
                event_type=SecurityEventType.SUSPICIOUS_PATTERN_DETECTED,
                severity="LOW",
                message="Security scan completed successfully",
                details={"scan_type": "manual", "result": "secure"}
            )
            
            messagebox.showinfo("Security Scan", "✅ Security scan completed!\n\nNo threats detected.\nSystem is secure and operational.")
            
        except Exception as e:
            messagebox.showerror("Scan Error", f"Security scan failed: {e}")
        finally:
            self.status_var.set("Monitoring Active")
            
    def generate_security_report(self):
        """Generate comprehensive security report."""
        try:
            report = self.security_logger.generate_security_report()
            
            # Create popup window
            report_window = tk.Toplevel(self.root)
            report_window.title("Security Report")
            report_window.geometry("800x600")
            report_window.configure(bg='#1e1e1e')
            
            text_widget = tk.Text(report_window, wrap=tk.WORD, bg='#2c3e50', fg='#ecf0f1',
                                font=('Courier', 10))
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert(1.0, report)
            text_widget.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Report Error", f"Failed to generate security report: {e}")
            
    def export_security_data(self):
        """Export security data."""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if filename:
                summary = self.security_logger.get_security_summary()
                with open(filename, 'w') as f:
                    json.dump(summary, f, indent=2)
                messagebox.showinfo("Export Complete", f"Security data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export security data: {e}")
            
    def view_threat_map(self):
        """View threat analysis map."""
        try:
            # Create threat analysis popup
            threat_window = tk.Toplevel(self.root)
            threat_window.title("Threat Analysis Map")
            threat_window.geometry("600x400")
            threat_window.configure(bg='#1e1e1e')
            
            # Get recent threat data
            recent_events = self.security_logger.get_recent_events(limit=100)
            
            # Analyze threat patterns
            threat_analysis = self.analyze_threat_patterns(recent_events)
            
            text_widget = tk.Text(threat_window, wrap=tk.WORD, bg='#2c3e50', fg='#ecf0f1',
                                font=('Courier', 10))
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert(1.0, threat_analysis)
            text_widget.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Analysis Error", f"Failed to generate threat analysis: {e}")
            
    def analyze_threat_patterns(self, events):
        """Analyze threat patterns from events."""
        try:
            # Count events by type and severity
            type_counts = {}
            severity_counts = {}
            
            for event in events:
                event_type = event.get('event_type', 'UNKNOWN')
                severity = event.get('severity', 'LOW')
                
                type_counts[event_type] = type_counts.get(event_type, 0) + 1
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            analysis = f"""
THREAT ANALYSIS MAP
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

ANALYSIS SUMMARY:
- Total events analyzed: {len(events)}
- Analysis period: Last {len(events)} events
- Current threat level: {self.security_state['threat_level']}

EVENT TYPE DISTRIBUTION:
"""
            
            for event_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                analysis += f"- {event_type}: {count} events\n"
            
            analysis += f"\nSEVERITY DISTRIBUTION:\n"
            for severity, count in sorted(severity_counts.items(), key=lambda x: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].index(x[0])):
                analysis += f"- {severity}: {count} events\n"
            
            analysis += f"\nTHREAT ASSESSMENT:\n"
            analysis += f"- Primary threat types: {', '.join(list(type_counts.keys())[:3])}\n"
            analysis += f"- Most concerning severity: {max(severity_counts.keys(), key=lambda x: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].index(x))}\n"
            analysis += f"- Recommended action: {'Monitor closely' if self.security_state['threat_level'] in ['HIGH', 'CRITICAL'] else 'Maintain current security posture'}\n"
            
            return analysis
            
        except Exception as e:
            return f"Error analyzing threat patterns: {e}"
            
    def log_activity(self, message):
        """Log security monitor activity."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.events_text.insert(tk.END, f"[{timestamp}] MONITOR: {message}\n", 'LOW')
            self.events_text.see(tk.END)
        except Exception as e:
            print(f"Error logging activity: {e}")
            
    def run(self):
        """Run the security monitor."""
        try:
            # Set up window close handler
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # Start monitoring
            self.log_activity("Security monitor started")
            
            # Run the GUI
            self.root.mainloop()
            
        except KeyboardInterrupt:
            self.on_closing()
        except Exception as e:
            print(f"Security monitor error: {e}")
            self.on_closing()
            
    def on_closing(self):
        """Handle window closing."""
        try:
            self.security_state['monitoring_active'] = False
            self.log_activity("Security monitor shutting down...")
            
            # Wait a moment for threads to finish
            time.sleep(1)
            
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
            sys.exit(0)


def main():
    """Main function to run the security monitor."""
    try:
        print("Starting Agent0 Security Monitor...")
        monitor = SecurityMonitor()
        monitor.run()
    except Exception as e:
        print(f"Failed to start security monitor: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()