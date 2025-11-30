#!/usr/bin/env python3
"""
Agent0 Unified Main GUI - Single Window with Tabs
Minimal version to test syntax
"""

import sys
import tkinter as tk
from tkinter import ttk

def main():
    """Main function to run the minimal GUI."""
    root = tk.Tk()
    root.title("Agent0 Unified Dashboard - Test")
    root.geometry("800x600")
    
    # Create main frame
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Create notebook
    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill=tk.BOTH, expand=True)
    
    # Create tabs
    overview_frame = ttk.Frame(notebook)
    notebook.add(overview_frame, text="Overview")
    
    # Add content to overview tab
    label = ttk.Label(overview_frame, text="Agent0 Unified GUI - Working!")
    label.pack(pady=20)
    
    # Start the GUI
    root.mainloop()

if __name__ == "__main__":
    main()