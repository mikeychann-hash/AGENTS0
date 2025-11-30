#!/usr/bin/env python3
"""
Agent0 Log Viewer - Simple log file viewer
Provides real-time log file viewing with filtering and search capabilities
"""

import sys
import re
import time
from pathlib import Path
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
    import tkinter.font as tkfont
except ImportError:
    print("Error: tkinter not available. Please install python3-tk")
    sys.exit(1)


class LogViewer:
    """Simple log file viewer with real-time updates and filtering."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Agent0 Log Viewer")
        self.root.geometry("900x600")
        self.root.configure(bg='#f5f5f5')
        
        # Log directory
        self.log_dir = Path("runs")
        self.current_file = None
        self.last_modified = 0
        self.auto_refresh = False
        self.refresh_interval = 1000  # milliseconds
        
        # Filter settings
        self.filter_patterns = {
            'ERROR': r'error|critical|failed|exception',
            'WARNING': r'warning|warn|alert|caution',
            'SECURITY': r'security|threat|blocked|attack',
            'INFO': r'info|success|completed|started',
            'DEBUG': r'debug|trace|detail'
        }
        
        self.setup_gui()
        
    def setup_gui(self):
        """Set up the GUI interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Create header
        self.create_header(main_frame)
        
        # Create control panel
        self.create_control_panel(main_frame)
        
        # Create log display
        self.create_log_display(main_frame)
        
        # Create status bar
        self.create_status_bar(main_frame)
        
        # Load initial file list
        self.refresh_file_list()
        
    def create_header(self, parent):
        """Create the header section."""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Title
        title_font = tkfont.Font(family="Arial", size=14, weight="bold")
        title_label = ttk.Label(header_frame, text="Agent0 Log Viewer", font=title_font)
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Subtitle
        subtitle_label = ttk.Label(header_frame, text="Real-time log file viewing and analysis", 
                                  font=("Arial", 10), foreground="#7f8c8d")
        subtitle_label.grid(row=1, column=0, sticky=tk.W)
        
        # Auto-refresh indicator
        self.refresh_indicator = ttk.Label(header_frame, text="●", foreground="#95a5a6", font=("Arial", 12))
        self.refresh_indicator.grid(row=0, column=1, sticky=tk.E, padx=(0, 10))
        
        header_frame.columnconfigure(1, weight=1)
        
    def create_control_panel(self, parent):
        """Create the control panel with file selection and filters."""
        control_frame = ttk.LabelFrame(parent, text="Controls", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # File selection
        file_frame = ttk.Frame(control_frame)
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(file_frame, text="Log File:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.file_var = tk.StringVar()
        self.file_combo = ttk.Combobox(file_frame, textvariable=self.file_var, 
                                     state="readonly", width=40)
        self.file_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        self.file_combo.bind('<<ComboboxSelected>>', self.on_file_selected)
        
        ttk.Button(file_frame, text="Refresh List", command=self.refresh_file_list).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(file_frame, text="Open File", command=self.open_file_dialog).grid(row=0, column=3, padx=(0, 10))
        
        # Filter controls
        filter_frame = ttk.Frame(control_frame)
        filter_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Label(filter_frame, text="Filter:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.filter_var = tk.StringVar(value="ALL")
        filter_options = ["ALL", "ERROR", "WARNING", "SECURITY", "INFO", "DEBUG"]
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var,
                                   values=filter_options, state="readonly", width=15)
        filter_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        filter_combo.bind('<<ComboboxSelected>>', self.apply_filter)
        
        ttk.Button(filter_frame, text="Apply Filter", command=self.apply_filter).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(filter_frame, text="Clear Filter", command=self.clear_filter).grid(row=0, column=3, padx=(0, 10))
        
        # Search controls
        search_frame = ttk.Frame(control_frame)
        search_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        search_entry.bind('<Return>', self.perform_search)
        
        ttk.Button(search_frame, text="Search", command=self.perform_search).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(search_frame, text="Clear Search", command=self.clear_search).grid(row=0, column=3)
        
        # Auto-refresh controls
        refresh_frame = ttk.Frame(control_frame)
        refresh_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.auto_refresh_var = tk.BooleanVar(value=False)
        refresh_check = ttk.Checkbutton(refresh_frame, text="Auto-refresh", 
                                      variable=self.auto_refresh_var,
                                      command=self.toggle_auto_refresh)
        refresh_check.grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        self.refresh_rate_var = tk.StringVar(value="1s")
        refresh_rate_combo = ttk.Combobox(refresh_frame, textvariable=self.refresh_rate_var,
                                        values=["1s", "2s", "5s", "10s", "30s"], 
                                        state="readonly", width=8)
        refresh_rate_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        refresh_rate_combo.bind('<<ComboboxSelected>>', self.update_refresh_rate)
        
        ttk.Button(refresh_frame, text="Refresh Now", command=self.refresh_display).grid(row=0, column=2)
        
    def create_log_display(self, parent):
        """Create the log display area."""
        log_frame = ttk.LabelFrame(parent, text="Log Content", padding="10")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Create text widget with scrollbar
        self.log_text = scrolledtext.ScrolledText(log_frame, height=25, width=80, wrap=tk.NONE,
                                                 bg='#1e1e1e', fg='#ecf0f1', font=('Courier', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure tags for syntax highlighting
        self.log_text.tag_configure('ERROR', foreground='#e74c3c', font=('Courier', 9, 'bold'))
        self.log_text.tag_configure('WARNING', foreground='#f39c12', font=('Courier', 9, 'bold'))
        self.log_text.tag_configure('SECURITY', foreground='#9b59b6', font=('Courier', 9, 'bold'))
        self.log_text.tag_configure('INFO', foreground='#3498db', font=('Courier', 9))
        self.log_text.tag_configure('DEBUG', foreground='#95a5a6', font=('Courier', 9))
        self.log_text.tag_configure('TIMESTAMP', foreground='#7f8c8d', font=('Courier', 8))
        self.log_text.tag_configure('HIGHLIGHT', background='#f39c12', foreground='black')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Horizontal scrollbar for long lines
        h_scrollbar = ttk.Scrollbar(log_frame, orient=tk.HORIZONTAL, command=self.log_text.xview)
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.log_text.config(xscrollcommand=h_scrollbar.set)
        
        # Grid configuration
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Context menu
        self.create_context_menu()
        
    def create_context_menu(self):
        """Create right-click context menu."""
        self.context_menu = tk.Menu(self.log_text, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_selected)
        self.context_menu.add_command(label="Select All", command=self.select_all)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Find Next", command=self.find_next)
        self.context_menu.add_command(label="Find Previous", command=self.find_previous)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Export Selected", command=self.export_selected)
        
        self.log_text.bind("<Button-3>", self.show_context_menu)
        
    def create_status_bar(self, parent):
        """Create the status bar."""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        self.file_info_var = tk.StringVar(value="No file loaded")
        self.line_count_var = tk.StringVar(value="0 lines")
        self.file_size_var = tk.StringVar(value="0 KB")
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.grid(row=0, column=0, sticky=tk.W)
        
        file_info_label = ttk.Label(status_frame, textvariable=self.file_info_var)
        file_info_label.grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        line_count_label = ttk.Label(status_frame, textvariable=self.line_count_var)
        line_count_label.grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        
        file_size_label = ttk.Label(status_frame, textvariable=self.file_size_var)
        file_size_label.grid(row=0, column=3, sticky=tk.W, padx=(20, 0))
        
        # Progress indicator
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var,
                                          mode='indeterminate', length=100)
        self.progress_bar.grid(row=0, column=4, sticky=(tk.W, tk.E), padx=(20, 0))
        
        status_frame.columnconfigure(4, weight=1)
        
    def refresh_file_list(self):
        """Refresh the list of available log files."""
        try:
            log_files = []
            if self.log_dir.exists():
                log_files = [f.name for f in self.log_dir.glob("*.log")]
                log_files.extend([f.name for f in self.log_dir.glob("*.jsonl")])
                log_files.extend([f.name for f in self.log_dir.glob("*.txt")])
                log_files.sort()
            
            self.file_combo.config(values=log_files)
            
            if log_files and not self.file_var.get():
                self.file_var.set(log_files[0] if log_files else "")
                self.on_file_selected()
                
            self.status_var.set(f"Found {len(log_files)} log files")
            
        except Exception as e:
            self.status_var.set(f"Error refreshing file list: {e}")
            
    def on_file_selected(self, event=None):
        """Handle file selection."""
        try:
            filename = self.file_var.get()
            if filename:
                self.load_log_file(filename)
                
        except Exception as e:
            self.status_var.set(f"Error selecting file: {e}")
            
    def load_log_file(self, filename=None):
        """Load and display a log file."""
        try:
            if filename is None:
                filename = self.file_var.get()
                
            if not filename:
                return
                
            log_file = self.log_dir / filename
            
            if not log_file.exists():
                self.log_text.delete(1.0, tk.END)
                self.log_text.insert(tk.END, f"File not found: {filename}\n", 'ERROR')
                self.status_var.set(f"File not found: {filename}")
                return
                
            # Get file info
            file_stat = log_file.stat()
            self.last_modified = file_stat.st_mtime
            file_size = file_stat.st_size
            
            # Read file content
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Display content
            self.display_content(content, filename)
            
            # Update status
            line_count = content.count('\n') + 1
            self.current_file = filename
            self.file_info_var.set(f"File: {filename}")
            self.line_count_var.set(f"{line_count} lines")
            self.file_size_var.set(f"{file_size / 1024:.1f} KB")
            self.status_var.set(f"Loaded {filename}")
            
            # Start auto-refresh if enabled
            if self.auto_refresh_var.get():
                self.schedule_auto_refresh()
                
        except Exception as e:
            self.status_var.set(f"Error loading file: {e}")
            
    def display_content(self, content, filename):
        """Display content with syntax highlighting."""
        try:
            self.log_text.delete(1.0, tk.END)
            
            if not content.strip():
                self.log_text.insert(tk.END, "(File is empty)\n", 'INFO')
                return
                
            # Apply highlighting based on current filter
            current_filter = self.filter_var.get()
            search_term = self.search_var.get().lower()
            
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if not line.strip():
                    self.log_text.insert(tk.END, '\n')
                    continue
                    
                # Determine highlighting based on filter
                highlight_tag = None
                line_lower = line.lower()
                
                if current_filter != "ALL":
                    pattern = self.filter_patterns.get(current_filter, '')
                    if re.search(pattern, line_lower, re.IGNORECASE):
                        highlight_tag = current_filter
                
                # Apply search highlighting
                if search_term and search_term in line_lower:
                    # Highlight the search term
                    parts = re.split(f'({re.escape(search_term)})', line, flags=re.IGNORECASE)
                    self.log_text.insert(tk.END, '\n'.join(parts[:2]) + '\n' if len(parts) > 1 else line + '\n')
                    
                    # Apply search highlight to matching parts
                    if len(parts) > 1:
                        start_idx = f"{i+1}.0"
                        for j, part in enumerate(parts[1:], 1):
                            if part.lower() == search_term.lower():
                                match_start = f"{i+1}.{sum(len(p) for p in parts[:j])}"
                                match_end = f"{i+1}.{sum(len(p) for p in parts[:j+1])}"
                                self.log_text.tag_add('HIGHLIGHT', match_start, match_end)
                else:
                    # Apply filter-based highlighting
                    if highlight_tag:
                        self.log_text.insert(tk.END, line + '\n', highlight_tag)
                    else:
                        # Auto-detect log level for highlighting
                        self.auto_highlight_line(line + '\n')
                        
        except Exception as e:
            self.log_text.insert(tk.END, f"Error displaying content: {e}\n", 'ERROR')
            
    def auto_highlight_line(self, line):
        """Automatically apply highlighting based on log content."""
        line_lower = line.lower()
        
        # Check for specific patterns
        if re.search(r'error|critical|failed|exception', line_lower):
            self.log_text.insert(tk.END, line, 'ERROR')
        elif re.search(r'warning|warn|alert|caution', line_lower):
            self.log_text.insert(tk.END, line, 'WARNING')
        elif re.search(r'security|threat|blocked|attack', line_lower):
            self.log_text.insert(tk.END, line, 'SECURITY')
        elif re.search(r'info|success|completed|started', line_lower):
            self.log_text.insert(tk.END, line, 'INFO')
        elif re.search(r'debug|trace|detail', line_lower):
            self.log_text.insert(tk.END, line, 'DEBUG')
        else:
            # Check for timestamp pattern
            if re.search(r'\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2}', line):
                parts = re.split(r'(\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2})', line, maxsplit=1)
                if len(parts) > 1:
                    self.log_text.insert(tk.END, parts[0], 'normal')
                    self.log_text.insert(tk.END, parts[1], 'TIMESTAMP')
                    if len(parts) > 2:
                        self.log_text.insert(tk.END, parts[2], 'normal')
                else:
                    self.log_text.insert(tk.END, line, 'normal')
            else:
                self.log_text.insert(tk.END, line, 'normal')
                
    def apply_filter(self, event=None):
        """Apply the current filter to the displayed content."""
        if self.current_file:
            self.load_log_file(self.current_file)
            
    def clear_filter(self):
        """Clear the current filter."""
        self.filter_var.set("ALL")
        self.apply_filter()
        
    def perform_search(self, event=None):
        """Perform search in the log content."""
        search_term = self.search_var.get().strip()
        if search_term and self.current_file:
            self.load_log_file(self.current_file)
            
    def clear_search(self):
        """Clear the search term."""
        self.search_var.set("")
        if self.current_file:
            self.load_log_file(self.current_file)
            
    def find_next(self):
        """Find next occurrence of search term."""
        search_term = self.search_var.get().strip()
        if not search_term:
            return
            
        try:
            current_pos = self.log_text.index(tk.INSERT)
            found_pos = self.log_text.search(search_term, current_pos, tk.END, nocase=True)
            
            if found_pos:
                line, col = found_pos.split('.')
                end_pos = f"{line}.{int(col) + len(search_term)}"
                self.log_text.tag_add('HIGHLIGHT', found_pos, end_pos)
                self.log_text.mark_set(tk.INSERT, end_pos)
                self.log_text.see(found_pos)
            else:
                # Wrap around to beginning
                found_pos = self.log_text.search(search_term, "1.0", tk.END, nocase=True)
                if found_pos:
                    line, col = found_pos.split('.')
                    end_pos = f"{line}.{int(col) + len(search_term)}"
                    self.log_text.tag_add('HIGHLIGHT', found_pos, end_pos)
                    self.log_text.mark_set(tk.INSERT, end_pos)
                    self.log_text.see(found_pos)
                else:
                    self.status_var.set(f"Search term '{search_term}' not found")
                    
        except Exception as e:
            self.status_var.set(f"Search error: {e}")
            
    def find_previous(self):
        """Find previous occurrence of search term."""
        search_term = self.search_var.get().strip()
        if not search_term:
            return
            
        try:
            current_pos = self.log_text.index(tk.INSERT)
            found_pos = self.log_text.search(search_term, "1.0", current_pos, nocase=True, backwards=True)
            
            if found_pos:
                line, col = found_pos.split('.')
                end_pos = f"{line}.{int(col) + len(search_term)}"
                self.log_text.tag_add('HIGHLIGHT', found_pos, end_pos)
                self.log_text.mark_set(tk.INSERT, found_pos)
                self.log_text.see(found_pos)
            else:
                # Wrap around to end
                found_pos = self.log_text.search(search_term, "1.0", tk.END, nocase=True, backwards=True)
                if found_pos:
                    line, col = found_pos.split('.')
                    end_pos = f"{line}.{int(col) + len(search_term)}"
                    self.log_text.tag_add('HIGHLIGHT', found_pos, end_pos)
                    self.log_text.mark_set(tk.INSERT, found_pos)
                    self.log_text.see(found_pos)
                else:
                    self.status_var.set(f"Search term '{search_term}' not found")
                    
        except Exception as e:
            self.status_var.set(f"Search error: {e}")
            
    def toggle_auto_refresh(self):
        """Toggle auto-refresh functionality."""
        if self.auto_refresh_var.get():
            self.schedule_auto_refresh()
            self.status_var.set("Auto-refresh enabled")
        else:
            self.status_var.set("Auto-refresh disabled")
            
    def update_refresh_rate(self, event=None):
        """Update the auto-refresh rate."""
        rate_str = self.refresh_rate_var.get()
        rate_map = {"1s": 1000, "2s": 2000, "5s": 5000, "10s": 10000, "30s": 30000}
        self.refresh_interval = rate_map.get(rate_str, 1000)
        
        if self.auto_refresh_var.get():
            self.schedule_auto_refresh()
            
    def schedule_auto_refresh(self):
        """Schedule the next auto-refresh."""
        if self.auto_refresh_var.get() and self.current_file:
            self.refresh_display()
            self.root.after(self.refresh_interval, self.schedule_auto_refresh)
            
            # Update refresh indicator
            self.update_refresh_indicator()
            
    def update_refresh_indicator(self):
        """Update the refresh indicator animation."""
        try:
            colors = ["#95a5a6", "#7f8c8d", "#95a5a6", "#bdc3c7"]
            current_color = self.refresh_indicator.cget('foreground')
            next_index = (colors.index(current_color) + 1) % len(colors)
            self.refresh_indicator.config(foreground=colors[next_index])
            
            if self.auto_refresh_var.get():
                self.root.after(250, self.update_refresh_indicator)
                
        except Exception:
            pass
            
    def refresh_display(self):
        """Refresh the current display."""
        if self.current_file:
            try:
                log_file = self.log_dir / self.current_file
                if log_file.exists():
                    current_modified = log_file.stat().st_mtime
                    
                    # Check if file was modified
                    if current_modified > self.last_modified:
                        self.last_modified = current_modified
                        self.load_log_file(self.current_file)
                        self.status_var.set(f"Refreshed {self.current_file}")
                    else:
                        self.status_var.set(f"No changes in {self.current_file}")
                        
            except Exception as e:
                self.status_var.set(f"Refresh error: {e}")
                
    def open_file_dialog(self):
        """Open file dialog to select a log file."""
        try:
            from tkinter import filedialog
            filename = filedialog.askopenfilename(
                initialdir=self.log_dir,
                title="Select Log File",
                filetypes=[
                    ("Log files", "*.log"),
                    ("JSON files", "*.jsonl"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )
            
            if filename:
                # Add to combo box if not already there
                current_files = list(self.file_combo.cget('values'))
                file_name_only = Path(filename).name
                
                if file_name_only not in current_files:
                    current_files.append(file_name_only)
                    self.file_combo.config(values=current_files)
                
                self.file_var.set(file_name_only)
                self.on_file_selected()
                
        except Exception as e:
            self.status_var.set(f"File dialog error: {e}")
            
    def copy_selected(self):
        """Copy selected text to clipboard."""
        try:
            selected_text = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.status_var.set("Selected text copied to clipboard")
        except tk.TclError:
            self.status_var.set("No text selected")
            
    def select_all(self):
        """Select all text in the log display."""
        self.log_text.tag_add(tk.SEL, 1.0, tk.END)
        self.log_text.mark_set(tk.INSERT, 1.0)
        self.log_text.see(tk.INSERT)
        
    def export_selected(self):
        """Export selected text."""
        try:
            from tkinter import filedialog
            selected_text = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(selected_text)
                self.status_var.set(f"Exported selected text to {filename}")
                
        except tk.TclError:
            self.status_var.set("No text selected for export")
        except Exception as e:
            self.status_var.set(f"Export error: {e}")
            
    def show_context_menu(self, event):
        """Show context menu on right-click."""
        self.context_menu.tk_popup(event.x_root, event.y_root)
        
    def run(self):
        """Run the log viewer."""
        try:
            # Set up window close handler
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # Start the GUI
            self.root.mainloop()
            
        except KeyboardInterrupt:
            self.on_closing()
        except Exception as e:
            print(f"Log viewer error: {e}")
            self.on_closing()
            
    def on_closing(self):
        """Handle window closing."""
        try:
            self.auto_refresh_var.set(False)  # Stop auto-refresh
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            print(f"Error during shutdown: {e}")
            sys.exit(0)


def main():
    """Main function to run the log viewer."""
    try:
        print("Starting Agent0 Log Viewer...")
        viewer = LogViewer()
        viewer.run()
    except Exception as e:
        print(f"Failed to start log viewer: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()