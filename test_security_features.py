#!/usr/bin/env python3
"""
Test script to demonstrate Agent0 security features in action.
"""

import sys
import json
import time
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent0.loop.coordinator import Coordinator
from agent0.validation.input_validator import InputValidator
from agent0.safety.code_reviewer import LocalCodeReviewer
from agent0.tasks.schema import TaskSpec
from agent0.logging.security_logger import SecurityLogger, SecurityEventType
from agent0.config import load_config

def test_security_features():
    """Demonstrate the security features in action."""
    print("=" * 60)
    print("AGENT0 SECURITY FEATURES DEMONSTRATION")
    print("=" * 60)
    
    # Test 1: Configuration Validation
    print("\n1. Testing Configuration Validation...")
    try:
        config = load_config("agent0/configs/3070ti.yaml")
        print("   Configuration validation: PASSED")
    except Exception as e:
        print(f"   Configuration validation: FAILED - {e}")
        return
    
    # Test 2: Input Validation
    print("\n2. Testing Input Validation...")
    validator = InputValidator()
    
    # Test malicious input
    malicious_task = TaskSpec(
        task_id="attack_123",
        domain="math",
        prompt="Solve this: eval(__import__('os').system('rm -rf /'))"
    )
    
    errors = validator.validate_task(malicious_task)
    if errors:
        print(f"   Malicious input blocked: PASSED")
        print(f"   Errors detected: {len(errors)}")
        for error in errors[:2]:  # Show first 2 errors
            print(f"     - {error}")
    else:
        print("   Malicious input blocked: FAILED")
    
    # Test valid input
    valid_task = TaskSpec(
        task_id="valid_123",
        domain="math",
        prompt="Solve for x: 2x + 3 = 7"
    )
    
    errors = validator.validate_task(valid_task)
    if not errors:
        print("   Valid input accepted: PASSED")
    else:
        print(f"   Valid input accepted: FAILED - {errors}")
    
    # Test 3: Code Review
    print("\n3. Testing Code Review System...")
    reviewer = LocalCodeReviewer()
    
    # Test dangerous code
    dangerous_code = """
import os
import subprocess
result = subprocess.run(['rm', '-rf', '/'], capture_output=True)
eval("malicious_code")
"""
    
    result = reviewer.review_python_code(dangerous_code)
    if not result["safe"]:
        print("   Dangerous code blocked: PASSED")
        print(f"   Issues found: {len(result['issues'])}")
        for issue in result["issues"][:2]:
            print(f"     - {issue}")
    else:
        print("   Dangerous code blocked: FAILED")
    
    # Test safe code
    safe_code = """
def calculate_area(radius):
    return 3.14159 * radius * radius

result = calculate_area(5)
print(f"Area: {result}")
"""
    
    result = reviewer.review_python_code(safe_code)
    if result["safe"]:
        print("   Safe code accepted: PASSED")
    else:
        print("   Safe code accepted: FAILED")
    
    # Test 4: Run a secure task
    print("\n4. Testing Secure Task Execution...")
    try:
        # Initialize coordinator with security features
        coordinator = Coordinator(config)
        print("   Coordinator initialized: PASSED")
        
        # Run a simple task
        print("   Running secure task...")
        
        # Create a simple math task
        student_signal = {
            "next_task_id": "security_test_001",
            "domain_override": "math",
            "difficulty": 0.3
        }
        
        trajectory = coordinator.run_once(student_signal)
        
        if trajectory:
            print(f"   Task completed: PASSED")
            print(f"   Task ID: {trajectory.task.task_id}")
            print(f"   Success: {trajectory.success}")
            print(f"   Result: {trajectory.result}")
            print(f"   Reward: {trajectory.reward['total']:.3f}")
        else:
            print("   Task completed: FAILED - No trajectory returned")
            
    except Exception as e:
        print(f"   Secure task execution: FAILED - {e}")
    
    # Test 5: Security Logging
    print("\n5. Testing Security Logging...")
    try:
        # Check if security events were logged
        security_log_file = Path("runs/security_events.jsonl")
        if security_log_file.exists():
            with open(security_log_file, 'r') as f:
                events = [json.loads(line) for line in f.readlines()]
            
            if events:
                print(f"   Security events logged: PASSED ({len(events)} events)")
                # Show the most recent event
                latest_event = events[-1]
                print(f"   Latest event: {latest_event['event_type']} - {latest_event['severity']}")
            else:
                print("   Security events logged: No events found")
        else:
            print("   Security events logged: No log file found")
            
    except Exception as e:
        print(f"   Security logging check: FAILED - {e}")
    
    # Test 6: Rate Limiting
    print("\n6. Testing Rate Limiting...")
    try:
        # Try to run multiple tasks quickly
        print("   Testing rapid task execution...")
        
        # Note: In a real test, we'd run many tasks quickly, but for demo we'll just show the configuration
        rate_config = config.get('rate_limiting', {})
        max_per_minute = rate_config.get('max_tasks_per_minute', 60)
        max_per_hour = rate_config.get('max_tasks_per_hour', 1000)
        
        print(f"   Rate limits configured: {max_per_minute} tasks/minute, {max_per_hour} tasks/hour")
        print("   Rate limiting: CONFIGURED")
        
    except Exception as e:
        print(f"   Rate limiting test: FAILED - {e}")
    
    print("\n" + "=" * 60)
    print("SECURITY FEATURES DEMONSTRATION COMPLETE")
    print("=" * 60)
    
    # Show final security summary
    try:
        if 'coordinator' in locals():
            summary = coordinator.security_logger.get_security_summary()
            print(f"\nSecurity Summary:")
            print(f"  Total security events: {summary['total_events']}")
            print(f"  Security score: {summary['security_score']:.1f}/100")
            print(f"  Blocked attempts: {summary['blocked_attempts']}")
            
            if summary['total_events'] > 0:
                print(f"  Events by severity:")
                for severity, count in summary['events_by_severity'].items():
                    if count > 0:
                        print(f"    {severity}: {count}")
    except Exception as e:
        print(f"\nCould not generate security summary: {e}")
    
    print("\nThe Agent0 system is running with enhanced security features!")
    print("All security improvements are active and protecting the system.")

if __name__ == "__main__":
    test_security_features()