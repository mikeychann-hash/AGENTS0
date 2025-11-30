"""
Comprehensive tests for security fixes and improvements in Agent0.
"""

import tempfile
import os
import json
import threading
import time
from pathlib import Path
import pytest

# Add project root to path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent0.safety.code_reviewer import LocalCodeReviewer
from agent0.validation.input_validator import InputValidator
from agent0.tasks.schema import TaskSpec, VerifierSpec
from agent0.tools import python_runner
from agent0.utils.file_lock import file_lock, FileLock


class TestCodeReviewerSecurity:
    """Test the enhanced code reviewer security features."""
    
    def setup_method(self):
        self.reviewer = LocalCodeReviewer()
    
    def test_blocks_dangerous_imports(self):
        """Test that dangerous imports are blocked."""
        dangerous_code = """
import os
import subprocess
import sys
result = subprocess.run(['ls', '-la'], capture_output=True)
"""
        result = self.reviewer.review_python_code(dangerous_code)
        assert not result["safe"]
        assert any("subprocess" in issue for issue in result["issues"])
    
    def test_blocks_dangerous_builtins(self):
        """Test that dangerous builtins are blocked."""
        dangerous_code = """
eval("1 + 1")
exec("print('hello')")
compile("print('hello')", "<string>", "exec")
"""
        result = self.reviewer.review_python_code(dangerous_code)
        assert not result["safe"]
        assert any("eval" in issue for issue in result["issues"])
        assert any("exec" in issue for issue in result["issues"])
    
    def test_blocks_file_operations(self):
        """Test that file operations are detected."""
        file_code = """
f = open('/etc/passwd', 'r')
data = f.read()
f.close()
"""
        result = self.reviewer.review_python_code(file_code)
        assert not result["safe"]
        assert any("open" in issue for issue in result["issues"])
    
    def test_allows_safe_code(self):
        """Test that safe code is allowed."""
        safe_code = """
def calculate_area(radius):
    return 3.14159 * radius * radius

result = calculate_area(5)
print(f"Area: {result}")
"""
        result = self.reviewer.review_python_code(safe_code)
        assert result["safe"]
        assert not result["issues"]
    
    def test_blocks_code_injection_patterns(self):
        """Test that code injection patterns are blocked."""
        injection_code = """
user_input = "__import__('os').system('rm -rf /')"
eval(user_input)
"""
        result = self.reviewer.review_python_code(injection_code)
        assert not result["safe"]
    
    def test_handles_long_code(self):
        """Test that very long code is rejected."""
        long_code = "x = 1\n" * 10001  # > 10KB
        result = self.reviewer.review_python_code(long_code)
        assert not result["safe"]
        assert any("too long" in issue for issue in result["issues"])
    
    def test_handles_syntax_errors(self):
        """Test that syntax errors are handled gracefully."""
        invalid_code = "def broken(:
    print('hello'"
        result = self.reviewer.review_python_code(invalid_code)
        assert not result["safe"]
        assert any("Syntax error" in issue for issue in result["issues"])


class TestInputValidatorSecurity:
    """Test the enhanced input validator security features."""
    
    def setup_method(self):
        self.validator = InputValidator()
    
    def test_validates_task_id(self):
        """Test task_id validation."""
        # Valid task_id
        task = TaskSpec(
            task_id="valid_task_123",
            domain="math",
            prompt="Solve for x: 2x + 3 = 7"
        )
        errors = self.validator.validate_task(task)
        assert not errors
        
        # Invalid task_id
        task.task_id = ""
        errors = self.validator.validate_task(task)
        assert any("Missing or invalid task_id" in error for error in errors)
        
        # Task_id too long
        task.task_id = "a" * 101
        errors = self.validator.validate_task(task)
        assert any("task_id too long" in error for error in errors)
        
        # Task_id with invalid characters
        task.task_id = "invalid@task#"
        errors = self.validator.validate_task(task)
        assert any("invalid characters" in error for error in errors)
    
    def test_blocks_injection_attempts(self):
        """Test that injection attempts are blocked."""
        injection_task = TaskSpec(
            task_id="test_123",
            domain="math",
            prompt="Solve this: eval(__import__('os').system('rm -rf /'))"
        )
        errors = self.validator.validate_task(injection_task)
        assert any("Suspicious content detected" in error for error in errors)
    
    def test_blocks_html_injection(self):
        """Test that HTML injection is blocked."""
        html_task = TaskSpec(
            task_id="test_123",
            domain="math",
            prompt="<script>alert('xss')</script> Solve for x: 2x = 4"
        )
        errors = self.validator.validate_task(html_task)
        assert any("HTML/script tags detected" in error for error in errors)
    
    def test_blocks_sql_injection(self):
        """Test that SQL injection is blocked."""
        sql_task = TaskSpec(
            task_id="test_123",
            domain="math",
            prompt="Solve this; UNION SELECT * FROM users--"
        )
        errors = self.validator.validate_task(sql_task)
        assert any("SQL injection" in error for error in errors)
    
    def test_validates_prompt_length(self):
        """Test prompt length validation."""
        # Too short
        task = TaskSpec(
            task_id="test_123",
            domain="math",
            prompt="x"
        )
        errors = self.validator.validate_task(task)
        assert any("too short" in error for error in errors)
        
        # Too long
        task.prompt = "x" * 2001
        errors = self.validator.validate_task(task)
        assert any("too long" in error for error in errors)
    
    def test_sanitizes_strings(self):
        """Test string sanitization."""
        # Test null byte removal
        sanitized = self.validator.sanitize_string("hello\x00world")
        assert "\x00" not in sanitized
        
        # Test length limiting
        long_string = "x" * 2000
        sanitized = self.validator.sanitize_string(long_string, max_length=100)
        assert len(sanitized) == 100
        
        # Test control character removal
        control_string = "hello\x01\x02world\x03"
        sanitized = self.validator.sanitize_string(control_string)
        assert all(ord(c) >= 32 or c in '\n\t\r' for c in sanitized)


class TestPythonRunnerSecurity:
    """Test the enhanced Python runner security."""
    
    def test_blocks_dangerous_code(self):
        """Test that dangerous code is blocked by the reviewer."""
        dangerous_code = "import os\nos.system('echo pwned')"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = python_runner.run_python(dangerous_code, timeout=5, workdir=tmpdir)
            assert result["status"] == "blocked"
            assert "code review" in result["stderr"].lower()
    
    def test_handles_timeout_properly(self):
        """Test that timeouts are handled correctly."""
        infinite_code = "while True: pass"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            start_time = time.time()
            result = python_runner.run_python(infinite_code, timeout=2, workdir=tmpdir)
            end_time = time.time()
            
            assert result["status"] == "timeout"
            assert end_time - start_time < 3  # Should timeout within 2 seconds + some margin
    
    def test_cleans_up_temp_files(self):
        """Test that temporary files are cleaned up."""
        safe_code = "print('hello world')"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Count files before execution
            files_before = list(tmpdir_path.glob("*.py"))
            
            result = python_runner.run_python(safe_code, timeout=5, workdir=tmpdir)
            assert result["status"] == "ok"
            
            # Count files after execution
            files_after = list(tmpdir_path.glob("*.py"))
            
            # Should have no new Python files (they should be cleaned up)
            assert len(files_after) <= len(files_before)
    
    def test_handles_execution_errors(self):
        """Test that execution errors are handled gracefully."""
        error_code = "raise ValueError('Test error')"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = python_runner.run_python(error_code, timeout=5, workdir=tmpdir)
            # The code should execute but raise an error
            assert result["status"] == "ok"
            assert "ValueError" in result["stderr"]


class TestFileLocking:
    """Test the file locking mechanism."""
    
    def test_basic_file_lock(self):
        """Test basic file locking functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.jsonl"
            
            # Test acquiring and releasing lock
            lock = FileLock(test_file, timeout=1.0)
            assert lock.acquire()
            assert lock.release()
    
    def test_concurrent_file_access(self):
        """Test that file locking prevents concurrent access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "concurrent.jsonl"
            results = []
            
            def write_to_file(data):
                try:
                    with file_lock(test_file, timeout=2.0):
                        # Simulate some work
                        time.sleep(0.1)
                        results.append(data)
                except TimeoutError:
                    results.append("timeout")
            
            # Start multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=write_to_file, args=(f"data_{i}",))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # All operations should succeed (no timeouts)
            assert "timeout" not in results
            assert len(results) == 5
    
    def test_lock_timeout(self):
        """Test that lock acquisition times out properly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "timeout_test.jsonl"
            
            # Acquire lock in one thread
            lock1 = FileLock(test_file, timeout=1.0)
            assert lock1.acquire()
            
            # Try to acquire same lock with short timeout
            lock2 = FileLock(test_file, timeout=0.1)
            assert not lock2.acquire()  # Should timeout
            
            # Release first lock
            lock1.release()
            
            # Now second lock should be acquirable
            assert lock2.acquire()
            lock2.release()
    
    def test_context_manager(self):
        """Test file lock context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "context_test.jsonl"
            
            with file_lock(test_file, timeout=1.0):
                # Lock should be held
                lock_file = test_file.with_suffix(test_file.suffix + '.lock')
                assert lock_file.exists()
            
            # Lock should be released
            lock_file = test_file.with_suffix(test_file.suffix + '.lock')
            assert not lock_file.exists()


class TestIntegrationSecurity:
    """Integration tests for security features working together."""
    
    def test_full_security_pipeline(self):
        """Test the complete security pipeline."""
        validator = InputValidator()
        reviewer = LocalCodeReviewer()
        
        # Create a malicious task
        malicious_task = TaskSpec(
            task_id="attack_123",
            domain="math",
            prompt="Solve this: eval(__import__('subprocess').call(['rm', '-rf', '/']))"
        )
        
        # Step 1: Input validation should catch it
        errors = validator.validate_task(malicious_task)
        assert len(errors) > 0
        assert any("Suspicious content" in error for error in errors)
        
        # Step 2: Even if it got through, code reviewer should catch it
        code_result = reviewer.review_python_code(malicious_task.prompt)
        assert not code_result["safe"]
    
    def test_safe_task_flow(self):
        """Test that legitimate tasks pass all security checks."""
        validator = InputValidator()
        reviewer = LocalCodeReviewer()
        
        # Create a legitimate task
        safe_task = TaskSpec(
            task_id="safe_123",
            domain="math",
            prompt="Solve for x: 2x + 5 = 15"
        )
        
        # Should pass input validation
        errors = validator.validate_task(safe_task)
        assert len(errors) == 0
        
        # Should pass code review (if we were to review the prompt as code)
        code_result = reviewer.review_python_code("print('This is safe math code')")
        assert code_result["safe"]


if __name__ == "__main__":
    # Run basic tests
    test_code_reviewer = TestCodeReviewerSecurity()
    test_code_reviewer.setup_method()
    
    print("Testing code reviewer security...")
    test_code_reviewer.test_blocks_dangerous_imports()
    test_code_reviewer.test_blocks_dangerous_builtins()
    test_code_reviewer.test_allows_safe_code()
    print("✓ Code reviewer security tests passed")
    
    test_input_validator = TestInputValidatorSecurity()
    test_input_validator.setup_method()
    
    print("Testing input validator security...")
    test_input_validator.test_blocks_injection_attempts()
    test_input_validator.test_blocks_html_injection()
    test_input_validator.test_sanitizes_strings()
    print("✓ Input validator security tests passed")
    
    print("All security tests completed successfully!")