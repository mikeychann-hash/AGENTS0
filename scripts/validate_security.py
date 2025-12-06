#!/usr/bin/env python3
"""
Security validation script for Agent0.
Runs comprehensive security checks and generates a security report.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def test_code_reviewer():
    """Test the enhanced code reviewer."""
    print("Testing Code Reviewer Security...")
    
    # Set UTF-8 encoding for Windows
    import locale
    if sys.platform == 'win32':
        try:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
        except AttributeError:
            pass  # Fallback for older Python versions
    
    from agent0.safety.code_reviewer import LocalCodeReviewer
    
    reviewer = LocalCodeReviewer()
    
    # Test dangerous code blocking
    dangerous_code = """
import os
import subprocess
result = subprocess.run(['rm', '-rf', '/'], capture_output=True)
eval("malicious_code")
"""
    
    result = reviewer.review_python_code(dangerous_code)
    assert not result["safe"], "Dangerous code should be blocked"
    assert len(result["issues"]) > 0, "Issues should be identified"
    
    # Test safe code allowance
    safe_code = """
def calculate_area(radius):
    return 3.14159 * radius * radius

result = calculate_area(5)
print(f"Area: {result}")
"""
    
    result = reviewer.review_python_code(safe_code)
    assert result["safe"], "Safe code should be allowed"
    
    print("[PASS] Code reviewer security: PASSED")

def test_input_validator():
    """Test the enhanced input validator."""
    print("Testing Input Validator Security...")
    
    from agent0.validation.input_validator import InputValidator
    from agent0.tasks.schema import TaskSpec
    
    validator = InputValidator()
    
    # Test injection blocking
    injection_task = TaskSpec(
        task_id="test_123",
        domain="math",
        prompt="Solve this: eval(__import__('os').system('rm -rf /'))"
    )
    
    errors = validator.validate_task(injection_task)
    assert len(errors) > 0, "Injection attempts should be blocked"
    assert any("Suspicious content" in error for error in errors), "Suspicious content should be detected"
    
    # Test valid task
    valid_task = TaskSpec(
        task_id="valid_123",
        domain="math",
        prompt="Solve for x: 2x + 3 = 7"
    )
    
    errors = validator.validate_task(valid_task)
    assert len(errors) == 0, "Valid tasks should pass validation"
    
    print("[PASS] Input validator security: PASSED")

def test_configuration_validator():
    """Test the configuration validator."""
    print("Testing Configuration Validator...")
    
    from agent0.validation.config_validator import validate_config, ConfigValidationError
    
    # Test valid configuration (with fixed rate limiting)
    valid_config = {
        "models": {
            "teacher": {
                "backend": "ollama",
                "model": "qwen2.5:3b",
                "host": "http://127.0.0.1:11434",
                "context_length": 4096,
                "temperature": 0.7,
                "top_p": 0.9,
                "uncertainty_samples": 3
            },
            "student": {
                "backend": "ollama",
                "model": "qwen2.5:7b",
                "host": "http://127.0.0.1:11434",
                "context_length": 8192,
                "temperature": 0.6,
                "top_p": 0.9,
                "uncertainty_samples": 3
            }
        },
        "resources": {
            "device": "cuda",
            "max_gpu_memory_gb": 8,
            "num_threads": 6,
            "max_tokens_per_task": 512
        },
        "tooling": {
            "enable_python": True,
            "enable_shell": False,
            "enable_math": True,
            "enable_tests": False,
            "timeout_seconds": 30,
            "workdir": "./sandbox",
            "allowed_shell": []
        },
        "rewards": {
            "weight_uncertainty": 0.5,
            "weight_tool_use": 0.3,
            "weight_novelty": 0.2,
            "target_success_rate": 0.5,
            "repetition_similarity_threshold": 0.9
        },
        "logging": {
            "base_dir": "./runs",
            "save_every": 10,
            "flush_every": 1
        },
        "rate_limiting": {
            "max_tasks_per_minute": 10,  # Reduced to be consistent with hourly limit
            "max_tasks_per_hour": 1000
        }
    }
    
    try:
        errors = validate_config(valid_config)
        assert len(errors) == 0, "Valid configuration should pass validation"
    except ConfigValidationError:
        assert False, "Valid configuration should not raise validation error"
    
    # Test invalid configuration
    invalid_config = valid_config.copy()
    invalid_config["models"]["teacher"]["temperature"] = 5.0  # Invalid temperature
    
    try:
        validate_config(invalid_config)
        assert False, "Invalid configuration should raise validation error"
    except ConfigValidationError as e:
        assert "temperature" in str(e), "Temperature error should be detected"
    
    print("[PASS] Configuration validator: PASSED")

def test_file_locking():
    """Test file locking mechanism."""
    print("Testing File Locking...")
    
    import tempfile
    from pathlib import Path
    from agent0.utils.file_lock import file_lock, FileLock
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.jsonl"
        
        # Test basic lock functionality
        lock = FileLock(test_file, timeout=1.0)
        assert lock.acquire(), "Lock should be acquired"
        assert lock.release(), "Lock should be released"
        
        # Test context manager
        with file_lock(test_file, timeout=1.0):
            lock_file = test_file.with_suffix(test_file.suffix + '.lock')
            assert lock_file.exists(), "Lock file should exist during context"
        
        assert not lock_file.exists(), "Lock file should be removed after context"
    
    print("[PASS] File locking: PASSED")

def test_security_logger():
    """Test security logging functionality."""
    print("Testing Security Logger...")
    
    import tempfile
    import shutil
    from pathlib import Path
    from agent0.logging.security_logger import SecurityLogger, SecurityEventType
    
    # Create a temporary directory manually to avoid file locking issues
    tmpdir = Path(tempfile.mkdtemp())
    try:
        log_dir = tmpdir
        security_logger = SecurityLogger(log_dir, enable_monitoring=True)
        
        # Log a security event
        security_logger.log_security_event(
            event_type=SecurityEventType.INPUT_VALIDATION_FAILED,
            severity="HIGH",
            message="Test security event",
            details={"test": "data"}
        )
        
        # Check that event was logged
        summary = security_logger.get_security_summary()
        assert summary['total_events'] > 0, "Security events should be logged"
        assert summary['events_by_type']['input_validation_failed'] > 0, "Specific event type should be logged"
        
        # Generate security report
        report = security_logger.generate_security_report()
        assert "AGENT0 SECURITY REPORT" in report, "Security report should be generated"
    finally:
        # Clean up manually
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass  # Ignore cleanup errors
    
    print("[PASS] Security logger: PASSED")

def test_mathematical_edge_cases():
    """Test mathematical edge case handling."""
    print("Testing Mathematical Edge Cases...")
    
    from agent0.agents.teacher import TeacherAgent
    from agent0.models.factory import create_model
    
    # Create a mock model for testing
    class MockModel:
        def generate(self, prompt, max_tokens=64, temperature=0.7):
            return '{"a": 0, "b": 0, "c": 0}'  # Values that would cause division by zero
    
    # Test teacher agent with edge case parameters
    model_config = {"backend": "mock", "model": "test"}
    teacher = TeacherAgent(model_config)
    teacher.model = MockModel()
    
    # This should not crash despite a=0 (which would cause division by zero)
    student_signal = {
        "next_task_id": "test_task",
        "difficulty": 0.8,
        "domain_override": "math"
    }
    
    try:
        task = teacher.generate_task(student_signal)
        assert task.task_id == "test_task", "Task should be generated successfully"
        print("[PASS] Mathematical edge cases: PASSED")
    except Exception as e:
        print(f"✗ Mathematical edge case test failed: {e}")
        raise

def main():
    """Run all security validation tests."""
    print("=" * 60)
    print("AGENT0 SECURITY VALIDATION")
    print("=" * 60)
    print()
    
    tests = [
        test_code_reviewer,
        test_input_validator,
        test_configuration_validator,
        test_file_locking,
        test_security_logger,
        test_mathematical_edge_cases
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
            print()
        except Exception as e:
            failed += 1
            print(f"[FAIL] {test.__name__}: FAILED")
            print(f"  Error: {e}")
            traceback.print_exc()
            print()
    
    print("=" * 60)
    print("SECURITY VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Tests Passed: {passed}")
    print(f"Tests Failed: {failed}")
    print(f"Total Tests: {passed + failed}")
    
    if failed == 0:
        print()
        print("[SUCCESS] All security validation tests passed!")
        print("The Agent0 codebase is ready for secure deployment.")
        return 0
    else:
        print()
        print("[WARNING] Some security validation tests failed.")
        print("Please review and fix the issues before deployment.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())