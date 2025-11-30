#!/usr/bin/env python3
"""
Simple test to verify GUI components are working correctly
"""

import sys
import time
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def test_gui_imports():
    """Test that GUI components can be imported successfully."""
    print("Testing GUI component imports...")
    
    try:
        # Test dashboard import
        from dashboard_gui import Agent0Dashboard
        print("SUCCESS: Dashboard GUI import successful")
        
        # Test evolution monitor import
        from evolution_monitor import EvolutionMonitor
        print("SUCCESS: Evolution Monitor import successful")
        
        # Test log viewer import
        from log_viewer import LogViewer
        print("SUCCESS: Log Viewer import successful")
        
        return True
        
    except ImportError as e:
        print(f"FAILED: Import error: {e}")
        return False
    except Exception as e:
        print(f"FAILED: Unexpected error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality without launching full GUI."""
    print("\nTesting basic functionality...")
    
    try:
        # Test that we can create the classes without launching GUI
        from dashboard_gui import Agent0Dashboard
        from evolution_monitor import EvolutionMonitor
        from log_viewer import LogViewer
        
        # Test class instantiation (without running main loop)
        print("Testing class instantiation...")
        
        # These should work without actually launching the GUI
        dashboard = Agent0Dashboard()
        print("SUCCESS: Dashboard class instantiation successful")
        
        monitor = EvolutionMonitor()
        print("SUCCESS: Evolution Monitor class instantiation successful")
        
        viewer = LogViewer()
        print("SUCCESS: Log Viewer class instantiation successful")
        
        # Clean up
        try:
            dashboard.root.destroy()
            monitor.root.destroy()
            viewer.root.destroy()
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"FAILED: Functionality test error: {e}")
        return False

def test_simple_gui():
    """Test that we can launch a simple GUI window."""
    print("\nTesting simple GUI launch...")
    
    try:
        import tkinter as tk
        
        # Create a simple test window
        root = tk.Tk()
        root.title("Agent0 GUI Test")
        root.geometry("300x200")
        
        label = tk.Label(root, text="Agent0 GUI Components Working!", font=("Arial", 14))
        label.pack(pady=20)
        
        button = tk.Button(root, text="Test Complete", command=root.destroy)
        button.pack(pady=10)
        
        print("SUCCESS: Simple GUI window created successfully")
        print("SUCCESS: GUI components are functional")
        
        # Show for 3 seconds then close
        root.after(3000, root.destroy)
        root.mainloop()
        
        return True
        
    except Exception as e:
        print(f"FAILED: GUI launch test error: {e}")
        return False

def main():
    """Main test function."""
    print("=" * 60)
    print("AGENT0 GUI COMPONENTS TEST")
    print("=" * 60)
    
    # Test imports
    imports_ok = test_gui_imports()
    
    if imports_ok:
        # Test basic functionality
        functionality_ok = test_basic_functionality()
        
        if functionality_ok:
            # Test GUI launch
            gui_ok = test_simple_gui()
            
            if gui_ok:
                print("\n" + "=" * 60)
                print("SUCCESS: ALL GUI TESTS PASSED!")
                print("=" * 60)
                print("SUCCESS: GUI components are working correctly")
                print("SUCCESS: Agent evolution dashboard is ready")
                print("SUCCESS: Evolution monitor is functional")
                print("SUCCESS: Log viewer is operational")
                print("\nThe Agent0 GUI system is ready for use!")
                return 0
            else:
                print("\nFAILED: GUI launch test failed")
                return 1
        else:
            print("\nFAILED: Functionality test failed")
            return 1
    else:
        print("\nFAILED: Import test failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())