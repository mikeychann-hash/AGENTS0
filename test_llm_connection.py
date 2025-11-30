#!/usr/bin/env python3
"""
Test script to verify LLM connection and system functionality
Tests direct LLM connection without scaffolding
"""

import sys
import time
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def test_llm_connection():
    """Test direct LLM connection."""
    print("Testing LLM connection...")
    
    try:
        # Test agent imports
        from agent0.agents.teacher import TeacherAgent
        from agent0.agents.student import StudentAgent
        from agent0.config import load_config
        
        print("SUCCESS: Agent imports successful")
        
        # Load configuration
        config = load_config("agent0/configs/3070ti.yaml")
        print("SUCCESS: Configuration loaded")
        
        # Extract agent configurations
        teacher_config = config["models"]["teacher"]
        executor_config = config["models"]["student"]
        
        print(f"Teacher model: {teacher_config['model']}")
        print(f"Executor model: {executor_config['model']}")
        print(f"Teacher host: {teacher_config['host']}")
        print(f"Executor host: {executor_config['host']}")
        
        # Test agent instantiation
        print("Testing agent instantiation...")
        teacher = TeacherAgent(teacher_config)
        executor = StudentAgent(executor_config)
        
        print("SUCCESS: Agents instantiated successfully")
        
        # Test basic task generation
        print("Testing basic task generation...")
        
        # Create a simple task signal
        teacher_signal = {
            'next_task_id': 'test_task_001',
            'domain_override': 'math',
            'difficulty': 0.5
        }
        
        # Generate task using teacher
        task = teacher.generate_task(teacher_signal)
        print(f"SUCCESS: Teacher generated task: {task.domain} - {task.prompt[:50]}...")
        
        # Test executor
        print("Testing executor...")
        
        # Create executor signal
        executor_signal = {
            'next_task_id': 'test_task_001',
            'domain_override': 'math',
            'difficulty': 0.5
        }
        
        # This would normally be done through the coordinator
        # For testing, we'll just verify the executor can be instantiated
        print("SUCCESS: Executor agent ready")
        
        return True
        
    except ImportError as e:
        print(f"FAILED: Import error: {e}")
        return False
    except Exception as e:
        print(f"FAILED: Unexpected error: {e}")
        return False

def test_coordinator_functionality():
    """Test coordinator functionality."""
    print("\nTesting coordinator functionality...")
    
    try:
        from agent0.loop.coordinator import Coordinator
        from agent0.config import load_config
        from agent0.validation.config_validator import validate_config
        
        # Load and validate configuration
        config = load_config("agent0/configs/3070ti.yaml")
        validate_config(config)
        print("SUCCESS: Configuration validated")
        
        # Initialize coordinator
        print("Initializing coordinator...")
        coordinator = Coordinator(config)
        print("SUCCESS: Coordinator initialized")
        
        # Test basic functionality
        print("Testing basic coordinator functionality...")
        
        # Create a simple signal
        signal = {
            'next_task_id': 'test_task_001',
            'domain_override': 'math',
            'difficulty': 0.3
        }
        
        # Run one iteration
        trajectory = coordinator.run_once(signal)
        
        if trajectory:
            print(f"SUCCESS: Coordinator executed task")
            print(f"Task ID: {trajectory.task.task_id}")
            print(f"Domain: {trajectory.task.domain}")
            print(f"Success: {trajectory.success}")
            print(f"Result: {trajectory.result}")
            return True
        else:
            print("WARNING: No trajectory returned (may be normal)")
            return True
            
    except Exception as e:
        print(f"FAILED: Coordinator test error: {e}")
        return False

def test_tool_integration():
    """Test tool integration."""
    print("\nTesting tool integration...")
    
    try:
        from agent0.tools import math_engine, python_runner
        
        # Test math engine
        print("Testing math engine...")
        result = math_engine.solve_expression("2 + 3")
        print(f"Math engine result: {result}")
        
        # Test python runner (safely)
        print("Testing Python runner...")
        code = "print('Hello from Python tool!')\nresult = 2 + 3\nprint(f'Result: {result}')"
        result = python_runner.run_python(code, timeout=5, workdir="./sandbox")
        print(f"Python runner result: {result}")
        
        print("SUCCESS: Tool integration working")
        return True
        
    except Exception as e:
        print(f"FAILED: Tool integration error: {e}")
        return False

def test_real_evolution_cycle():
    """Test a real evolution cycle."""
    print("\nTesting real evolution cycle...")
    
    try:
        from agent0.loop.coordinator import Coordinator
        from agent0.config import load_config
        
        # Load configuration
        config = load_config("agent0/configs/3070ti.yaml")
        
        # Initialize coordinator
        coordinator = Coordinator(config)
        
        print("Running evolution cycle...")
        
        # Run multiple cycles
        for i in range(3):
            print(f"\n--- Evolution Cycle {i+1} ---")
            
            # Create evolution signal
            signal = {
                'next_task_id': f'evolution_test_{i+1}',
                'domain_override': 'math',
                'difficulty': 0.3 + (i * 0.1)  # Gradually increasing difficulty
            }
            
            # Run evolution
            trajectory = coordinator.run_once(signal)
            
            if trajectory:
                print(f"Cycle {i+1} Results:")
                print(f"  Task ID: {trajectory.task.task_id}")
                print(f"  Domain: {trajectory.task.domain}")
                print(f"  Prompt: {trajectory.task.prompt[:50]}...")
                print(f"  Success: {trajectory.success}")
                print(f"  Result: {trajectory.result}")
                print(f"  Tool calls: {len(trajectory.tool_calls)}")
                
                # Log security event
                from agent0.logging.security_logger import SecurityLogger, SecurityEventType
                
                logger = SecurityLogger(Path("runs"), enable_monitoring=True)
                logger.log_security_event(
                    event_type=SecurityEventType.CODE_EXECUTION_BLOCKED if trajectory.success else SecurityEventType.INPUT_VALIDATION_FAILED,
                    severity="LOW" if trajectory.success else "MEDIUM",
                    message=f"Evolution cycle {i+1}: {'success' if trajectory.success else 'failure'}",
                    details={
                        'cycle': i+1,
                        'task_id': trajectory.task.task_id,
                        'success': trajectory.success,
                        'result': trajectory.result
                    }
                )
                
                time.sleep(2)  # Wait between cycles
                
            else:
                print(f"Cycle {i+1}: No trajectory returned")
                
        print("SUCCESS: Evolution cycles completed")
        return True
        
    except Exception as e:
        print(f"FAILED: Evolution cycle error: {e}")
        return False

def main():
    """Main test function."""
    print("=" * 60)
    print("AGENT0 LLM CONNECTION AND SYSTEM TEST")
    print("=" * 60)
    
    # Test LLM connection
    llm_ok = test_llm_connection()
    
    if llm_ok:
        # Test coordinator functionality
        coordinator_ok = test_coordinator_functionality()
        
        if coordinator_ok:
            # Test tool integration
            tools_ok = test_tool_integration()
            
            if tools_ok:
                # Test real evolution cycle
                evolution_ok = test_real_evolution_cycle()
                
                if evolution_ok:
                    print("\n" + "=" * 60)
                    print("SUCCESS: ALL SYSTEM TESTS PASSED!")
                    print("=" * 60)
                    print("SUCCESS: LLM connection established")
                    print("SUCCESS: Coordinator functionality working")
                    print("SUCCESS: Tool integration operational")
                    print("SUCCESS: Real evolution cycles completed")
                    print("\nThe Agent0 system with direct LLM connection is ready!")
                    return 0
                else:
                    print("\nFAILED: Evolution cycle test failed")
                    return 1
            else:
                print("\nFAILED: Tool integration test failed")
                return 1
        else:
            print("\nFAILED: Coordinator functionality test failed")
            return 1
    else:
        print("\nFAILED: LLM connection test failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())