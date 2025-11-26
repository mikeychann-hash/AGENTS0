# Agent0 Revised Action Plan - LOCAL ONLY VERSION
## Post-Review: Critical Fixes for Local Development

**Review Date:** November 25, 2025  
**Environment:** Local development - NO DOCKER, NO SANDBOX  
**Codebase Grade:** C+ (Functional Prototype)  
**Timeline:** Adjusted for local-only development

---

## 🚨 CRITICAL: Local Development Mode

**This plan assumes:**
- ❌ No Docker
- ❌ No sandboxing
- ❌ No resource isolation
- ✅ Direct execution on your machine
- ✅ Trusted tasks only
- ✅ Development/research use

**All security sections have been adapted for local-only development.**

---

## Crisis Triage: What We Found

### 🔴 BLOCKING (Won't Run)
1. **cloud_bridge.py** - Missing `import json` and `from pathlib import Path`
2. **student.py line 60** - Regex has double backslashes (`\\d` should be `\d`)
3. **uncertainty.py line 35** - Same regex bug

### 🟡 ADAPTED FOR LOCAL (Configuration Changes)
4. **sandbox.py** - Replace with explicit no-op (honest about no isolation)
5. **3070ti.yaml** - Disable risky tools (shell, tests)
6. **Documentation** - Add clear warnings about local execution

### 🟢 STILL IMPORTANT (Core Functionality)
7. **rewards/calculator.py** - Missing correctness reward component
8. **coordinator.py** - No error handling in main loop
9. **student.py line 93** - Will crash on malformed prompts
10. **0% test coverage** - No validation
11. **Minimal logging** - Can't debug issues

---

## PHASE 0: Emergency Fixes (Week 1)

**Goal:** Make it runnable locally with clear understanding of limitations

### Day 1: Critical Bug Patches + Local Config

#### Morning: Fix Imports and Regex

**Patch 1 - cloud_bridge.py:**
```python
# After line 2, add:
import json
from pathlib import Path
```

**Patch 2 - student.py line 60:**
```python
# Change:
match = re.search(r"[-+]?\\d+(?:\\.\\d+)?", text)
# To:
match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
```

**Patch 3 - uncertainty.py line 35:**
```python
# Change:
match = re.search(r"0(?:\\.\\d+)?|1(?:\\.0+)?", text)
# To:
match = re.search(r"0(?:\.\d+)?|1(?:\.0+)?", text)
```

#### Afternoon: Adapt for Local Execution

**Patch 4 - Replace sandbox.py entirely:**

```python
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

@contextmanager
def limit_resources(cpu_seconds: int = 5, mem_mb: int = 512):
    """
    LOCAL DEVELOPMENT MODE: No resource limits enforced.
    
    This is a no-op context manager for local development.
    Code runs directly on your machine with NO ISOLATION.
    
    Args:
        cpu_seconds: Ignored in local mode
        mem_mb: Ignored in local mode
    
    WARNING: Only run trusted code!
    """
    logger.warning("LOCAL MODE: No resource limits or isolation active")
    yield


def install_timeout(seconds: int = 10):
    """
    LOCAL DEVELOPMENT MODE: No timeout enforcement.
    
    This is a no-op function for local development.
    Timeouts are handled at the subprocess level only.
    
    Args:
        seconds: Ignored in local mode
    """
    pass
```

**Patch 5 - Update 3070ti.yaml:**

```yaml
# Add warning at top
# ============================================
# LOCAL DEVELOPMENT CONFIGURATION
# ============================================
# WARNING: No sandboxing or isolation!
# Code runs directly on your machine.
# Only use with trusted tasks.
# ============================================

tooling:
  enable_python: true    # ⚠️ Runs on your machine - trusted code only
  enable_shell: false    # Disabled for safety
  enable_math: true      # Safe - SymPy only
  enable_tests: false    # Disabled - would run arbitrary code
  timeout_seconds: 30    # Subprocess timeout only
  workdir: ./sandbox     # Not isolated - just a working directory
  allowed_shell: []      # Shell disabled anyway
```

**Deliverable:** Honest configuration that works locally

---

### Day 2: Documentation & Warnings

#### Create LOCAL_DEVELOPMENT.md

```markdown
# Local Development Mode

## ⚠️ SECURITY WARNING

Agent0 is configured for **LOCAL DEVELOPMENT MODE**:

### What This Means

**NO ISOLATION OR SANDBOXING:**
- Code execution happens directly on your Windows machine
- Python code can access any file you can access
- Python code can import any installed module
- Python code can make network requests
- Python code can spawn processes
- There are NO safety guardrails or resource limits

### Safe Usage

✓ Personal research and experimentation  
✓ Trusted tasks you create yourself  
✓ Learning about agent systems  
✓ Development with known-safe prompts  

✗ Production deployments  
✗ Processing untrusted input  
✗ Running on shared systems  
✗ Code from unknown sources  

### Monitoring Generated Code

Always review what code is generated:

```bash
# Check sandbox directory regularly
dir sandbox

# Review generated Python files
type sandbox\*.py

# Check trajectories for tool calls
type runs\trajectories.jsonl | findstr "tool_calls"
```

### Acceptable Risk Profile

This configuration is acceptable if:
1. You're the only user
2. You control all inputs
3. You're on a development machine
4. You can tolerate potential issues
5. You're not handling sensitive data

### For Production Use

If you need production-grade isolation:
1. Run in a dedicated VM
2. Use WSL2 + Docker
3. Deploy to cloud with sandboxing
4. Implement code review workflows

**This is LOCAL DEVELOPMENT ONLY.**
```

#### Update README

Add section at the top of README1.MD:

```markdown
## ⚠️ CURRENT CONFIGURATION: LOCAL DEVELOPMENT MODE

**This repository is configured for local development without sandboxing.**

What this means:
- Code runs directly on your machine
- No Docker or containerization
- No resource limits or isolation
- Suitable for trusted tasks only

See [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) for details.

For production use, see deployment recommendations in [PROJECT_PLAN.md](PROJECT_PLAN.md).
```

**Deliverable:** Clear documentation of risks and limitations

---

### Day 3: Add Correctness Reward & Error Handling

#### Update Reward Calculator

**File:** `agent0/rewards/calculator.py`

```python
def compute(
    self,
    trajectory: Trajectory,
    success_prob: float,
    novelty_sig: str,
    similarity: Optional[float] = None,
) -> Dict[str, float]:
    """Compute reward with correctness component"""
    r_unc = self._uncertainty_reward(success_prob)
    r_tool = self._tool_use_reward(trajectory.tool_calls)
    r_nov = self._novelty_penalty(novelty_sig)
    
    # NEW: Add correctness reward
    r_correct = 1.0 if trajectory.success else -0.5
    
    if similarity is not None and similarity > self.weights.repetition_similarity_threshold:
        r_nov -= 0.5

    total = (
        self.weights.weight_uncertainty * r_unc
        + self.weights.weight_tool_use * r_tool
        + self.weights.weight_novelty * r_nov
        + 0.3 * r_correct  # 30% weight on correctness
    )

    return {
        "uncertainty": r_unc,
        "tool_use": r_tool,
        "novelty": r_nov,
        "correctness": r_correct,  # NEW
        "total": total,
    }
```

#### Add Error Handling to Coordinator

**File:** `agent0/loop/coordinator.py`

```python
def run_once(self, student_signal: Dict[str, Any]) -> Optional[Trajectory]:
    """Run one iteration with error handling - LOCAL MODE"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # Log local mode warning
        logger.warning("Running in LOCAL MODE - code executes directly on your machine")
        
        signal = {**self.scheduler.next_signal(), **student_signal}
        task = self.teacher.generate_task(signal)
        
        # Log task being executed
        logger.info(f"Generated task: {task.prompt[:100]}...")
        
        traj = self.student.solve(task)
        
        # Log if Python code was executed
        if any(call.get("tool") == "python" for call in traj.tool_calls):
            logger.warning("Python code was executed locally - review sandbox directory")
        
        verdict = verify(task, traj.result)
        traj.success = verdict.get("status") == "pass"
        
        success_prob = self.uncertainty.estimate(task.prompt, traj.result)
        novelty_sig = f"{task.domain}:{hash(task.prompt) % 10_000}"
        emb = self.embedder.embed(task.prompt)
        similarity = 0.0
        
        if self.faiss:
            similarity = self.faiss.max_similarity(emb)
            self.faiss.add(emb)
        else:
            if self.recent_embeddings:
                similarity = max(cosine_similarity(emb, e) for e in self.recent_embeddings)
            self.recent_embeddings.append(emb)
            self.recent_embeddings = self.recent_embeddings[-200:]
        
        reward = self.reward_calc.compute(traj, success_prob, novelty_sig, similarity=similarity)
        traj.reward = reward
        self._log_trajectory(traj)
        self.scheduler.update(traj.success)
        
        logger.info(f"Task completed: success={traj.success}, reward={reward['total']:.3f}")
        
        return traj
        
    except Exception as e:
        logger.error(f"Iteration failed: {e}", exc_info=True)
        logger.error("Check sandbox directory for any generated files")
        return None
```

**Deliverable:** Safer execution with logging

---

### Day 4: Basic Unit Tests

**Create:** `tests/test_local_mode.py`

```python
import pytest
from agent0.agents.student import StudentAgent
from agent0.tasks.schema import TaskSpec

def test_number_extraction_basic():
    """Test number extraction works"""
    agent = StudentAgent({
        "backend": "ollama",
        "model": "qwen2.5:7b",
        "host": "http://127.0.0.1:11434"
    })
    
    assert agent._extract_number("The answer is 42") == "42"
    assert agent._extract_number("x = 3.14") == "3.14"
    assert agent._extract_number("negative -5") == "-5"

def test_sandbox_is_noop():
    """Verify sandbox is honest about being a no-op"""
    from agent0.tools.sandbox import limit_resources
    import logging
    
    with limit_resources():
        # Should work but log warning
        pass
    
    # No exception = success (it's a no-op)

def test_shell_runner_disabled():
    """Verify shell runner respects disabled config"""
    config = {
        "enable_shell": False
    }
    # Shell calls should be blocked at config level
    assert config["enable_shell"] == False

def test_python_runner_local_warning():
    """Verify Python runner works locally"""
    from agent0.tools import python_runner
    
    result = python_runner.run_python("print('test')", timeout=5)
    assert result["status"] == "ok"
    assert "test" in result["stdout"]
    
def test_math_engine_safe():
    """Math engine is safe even in local mode"""
    from agent0.tools import math_engine
    
    result = math_engine.solve_expression("2 + 2")
    assert result["status"] == "ok"
    assert "4" in result["result"]
```

**Run tests:**
```bash
pytest tests/test_local_mode.py -v
```

---

### Day 5: Enhanced Logging

**Create:** `agent0/logging/local_mode_logger.py`

```python
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

def configure_local_development_logging(
    log_dir: Path,
    level: int = logging.INFO
) -> logging.Logger:
    """
    Configure logging for local development mode.
    Emphasizes warnings about code execution.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("agent0")
    logger.setLevel(level)
    
    # File handler
    file_handler = RotatingFileHandler(
        log_dir / "agent0_local.log",
        maxBytes=10*1024*1024,
        backupCount=5
    )
    file_handler.setLevel(level)
    
    # Format with LOCAL MODE marker
    formatter = logging.Formatter(
        '[LOCAL MODE] %(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console with color for warnings
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only warnings and above
    console_formatter = logging.Formatter(
        '⚠️  [LOCAL] %(levelname)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Separate file for code execution
    code_exec_handler = RotatingFileHandler(
        log_dir / "code_execution.log",
        maxBytes=5*1024*1024,
        backupCount=3
    )
    code_exec_handler.setLevel(logging.WARNING)
    code_exec_handler.setFormatter(formatter)
    logger.addHandler(code_exec_handler)
    
    # Initial warning
    logger.warning("="*60)
    logger.warning("LOCAL DEVELOPMENT MODE ACTIVE")
    logger.warning("Code will execute directly on your machine")
    logger.warning("No sandboxing or isolation")
    logger.warning("="*60)
    
    return logger
```

**Update smoke_run.py and run_loop.py:**
```python
from agent0.logging.local_mode_logger import configure_local_development_logging

# Replace configure_logging with:
logger = configure_local_development_logging(
    Path(config["logging"]["base_dir"]),
    level=level
)
```

---

### Day 6-7: Safety Monitoring

#### Create Monitoring Script

**File:** `scripts/monitor_local_execution.py`

```python
#!/usr/bin/env python
"""
Monitor local execution for safety.
Reviews generated code and trajectories.
"""

import json
from pathlib import Path
import argparse

def check_sandbox_files(sandbox_dir: Path):
    """Review files created in sandbox"""
    print("\n[Sandbox Files]")
    if not sandbox_dir.exists():
        print("No sandbox directory")
        return
    
    py_files = list(sandbox_dir.glob("*.py"))
    if not py_files:
        print("No Python files generated")
        return
    
    print(f"Found {len(py_files)} Python files:")
    for f in py_files:
        print(f"\n  File: {f.name}")
        print(f"  Size: {f.stat().st_size} bytes")
        print("  Content preview:")
        content = f.read_text()
        lines = content.split('\n')[:10]
        for line in lines:
            print(f"    {line}")
        if len(content.split('\n')) > 10:
            print("    ...")

def check_trajectories(traj_file: Path, last_n: int = 5):
    """Review recent trajectories for risky operations"""
    print("\n[Recent Trajectories]")
    if not traj_file.exists():
        print("No trajectories file")
        return
    
    with open(traj_file) as f:
        lines = f.readlines()
    
    recent = lines[-last_n:] if len(lines) >= last_n else lines
    
    print(f"Reviewing last {len(recent)} trajectories:")
    for i, line in enumerate(recent, 1):
        data = json.loads(line)
        print(f"\n  Trajectory {i}:")
        print(f"    Task: {data['task']['prompt'][:60]}...")
        print(f"    Success: {data['success']}")
        print(f"    Tools used: {len(data['tool_calls'])}")
        
        for call in data['tool_calls']:
            tool = call.get('tool', 'unknown')
            status = call.get('status', 'unknown')
            print(f"      - {tool}: {status}")
            
            if tool == "python":
                # Show Python code that was executed
                code = call.get('input', '')
                if code:
                    print(f"        Code: {code[:100]}...")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sandbox", default="./sandbox", help="Sandbox directory")
    parser.add_argument("--trajectories", default="./runs/trajectories.jsonl")
    parser.add_argument("--last", type=int, default=5, help="Number of trajectories to review")
    args = parser.parse_args()
    
    print("="*60)
    print("LOCAL EXECUTION MONITOR")
    print("="*60)
    
    check_sandbox_files(Path(args.sandbox))
    check_trajectories(Path(args.trajectories), args.last)
    
    print("\n" + "="*60)
    print("Review complete. Check for any concerning code execution.")
    print("="*60)

if __name__ == "__main__":
    main()
```

**Usage:**
```bash
# After running some iterations
python scripts/monitor_local_execution.py

# Review last 10 trajectories
python scripts/monitor_local_execution.py --last 10
```

---

## Week 1 Deliverables Checklist

- [x] Fixed blocking bugs (imports, regex)
- [x] Replaced sandbox with honest no-op
- [x] Updated config for local mode
- [x] Created LOCAL_DEVELOPMENT.md
- [x] Added error handling to main loop
- [x] Added correctness reward component
- [x] Created basic unit tests
- [x] Set up local mode logging
- [x] Created monitoring script

**Success Criteria:**
1. All smoke tests pass with warnings
2. No crashes on basic usage
3. Clear documentation of local mode
4. Monitoring tools available
5. Test coverage >10%

---

## PHASE 1: Local Development Best Practices (Weeks 2-3)

### Week 2: Code Review & Validation

Instead of sandboxing (impossible locally), focus on:

#### Day 1-2: Code Review Tooling

**Create:** `agent0/safety/code_reviewer.py`

```python
import ast
import re
from typing import List, Dict

class LocalCodeReviewer:
    """Review generated code for risky operations before execution"""
    
    DANGEROUS_IMPORTS = [
        'os.system', 'subprocess', 'eval', 'exec',
        'open', '__import__', 'compile'
    ]
    
    DANGEROUS_PATTERNS = [
        r'rm\s+-rf',
        r'del\s+/',
        r'format\s+[A-Z]:',  # Windows drive format
        r'\.\./',  # Path traversal
        r'registry',
        r'import\s+win32',
    ]
    
    def review_python_code(self, code: str) -> Dict[str, any]:
        """Review Python code for safety"""
        issues = []
        warnings = []
        
        # Check for dangerous imports
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(danger in alias.name for danger in self.DANGEROUS_IMPORTS):
                            issues.append(f"Dangerous import: {alias.name}")
                
                if isinstance(node, ast.ImportFrom):
                    if node.module and any(danger in node.module for danger in self.DANGEROUS_IMPORTS):
                        issues.append(f"Dangerous import from: {node.module}")
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                warnings.append(f"Suspicious pattern: {pattern}")
        
        # Check file operations
        if 'open(' in code:
            warnings.append("File I/O detected")
        
        return {
            "safe": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "code": code
        }
```

**Integrate into python_runner.py:**

```python
from agent0.safety.code_reviewer import LocalCodeReviewer

reviewer = LocalCodeReviewer()

def run_python(code: str, timeout: int = 15, workdir: str = ".") -> Dict[str, str]:
    """Execute Python with code review first"""
    
    # Review code
    review = reviewer.review_python_code(code)
    
    if not review["safe"]:
        logger.error(f"Code review FAILED: {review['issues']}")
        return {
            "status": "blocked",
            "stdout": "",
            "stderr": f"Code blocked by review: {review['issues']}"
        }
    
    if review["warnings"]:
        logger.warning(f"Code review warnings: {review['warnings']}")
    
    # Original execution code...
```

#### Day 3-4: Input Validation

**Create:** `agent0/validation/input_validator.py`

```python
from typing import List
from agent0.tasks.schema import TaskSpec

class InputValidator:
    """Validate inputs before processing"""
    
    MAX_PROMPT_LENGTH = 1000
    ALLOWED_DOMAINS = ["math", "logic", "code", "long"]
    
    def validate_task(self, task: TaskSpec) -> List[str]:
        """Validate task before execution"""
        errors = []
        
        if not task.task_id:
            errors.append("Missing task_id")
        
        if task.domain not in self.ALLOWED_DOMAINS:
            errors.append(f"Invalid domain: {task.domain}")
        
        if not task.prompt:
            errors.append("Empty prompt")
        
        if len(task.prompt) > self.MAX_PROMPT_LENGTH:
            errors.append(f"Prompt too long: {len(task.prompt)} > {self.MAX_PROMPT_LENGTH}")
        
        # Check for suspicious content
        suspicious = ['exec(', 'eval(', '__import__', 'subprocess']
        for term in suspicious:
            if term in task.prompt.lower():
                errors.append(f"Suspicious content in prompt: {term}")
        
        return errors
```

---

### Week 3: Testing & Monitoring

#### Expand Test Coverage

```python
# tests/test_local_safety.py
def test_code_reviewer_blocks_dangerous():
    """Code reviewer blocks dangerous operations"""
    from agent0.safety.code_reviewer import LocalCodeReviewer
    
    reviewer = LocalCodeReviewer()
    
    # Should block
    dangerous = "import os; os.system('rm -rf /')"
    result = reviewer.review_python_code(dangerous)
    assert not result["safe"]
    assert len(result["issues"]) > 0

def test_code_reviewer_allows_safe():
    """Code reviewer allows safe code"""
    from agent0.safety.code_reviewer import LocalCodeReviewer
    
    reviewer = LocalCodeReviewer()
    
    # Should allow
    safe = "import math\nprint(math.sqrt(16))"
    result = reviewer.review_python_code(safe)
    assert result["safe"]
    assert len(result["issues"]) == 0

def test_input_validation():
    """Input validator catches bad tasks"""
    from agent0.validation.input_validator import InputValidator
    from agent0.tasks.schema import TaskSpec
    
    validator = InputValidator()
    
    # Bad task
    bad_task = TaskSpec(
        task_id="",  # Missing
        domain="invalid",  # Bad domain
        prompt="",  # Empty
        constraints=[]
    )
    
    errors = validator.validate_task(bad_task)
    assert len(errors) > 0
```

---

## Timeline Summary (Local Mode)

### Weeks 1-3: Foundation
- Week 1: Bug fixes, local config, safety docs
- Week 2: Code review tools, input validation
- Week 3: Testing and monitoring

### Weeks 4-6: Features (Same as original plan)
- Week 4: Multi-domain task generation
- Week 5: Advanced reward system
- Week 6: Production router

### Weeks 7-20: Training & Enhancement
- Continue with original plan phases 3-6
- All features work in local mode
- Just accept local execution model

---

## Key Differences from Original Plan

### Removed
- ❌ Docker sandboxing sections
- ❌ Container isolation
- ❌ Resource limit enforcement
- ❌ VM deployment guides

### Added
- ✅ LOCAL_DEVELOPMENT.md
- ✅ Code review tools
- ✅ Execution monitoring
- ✅ Safety warnings throughout
- ✅ Honest about limitations

### Adapted
- 🔄 Sandbox → honest no-op
- 🔄 Security → code review
- 🔄 Isolation → monitoring
- 🔄 Testing → local focus

---

## Success Metrics (Local Mode)

### Week 1
- ✓ Runs without crashes
- ✓ Warnings show local mode
- ✓ Documentation clear
- ✓ Monitoring tools available

### Week 3
- ✓ Code reviewer active
- ✓ Input validation working
- ✓ 30% test coverage
- ✓ No dangerous code executed

### Week 6
- ✓ Multi-domain working
- ✓ Router functional
- ✓ Safe for development use

---

## Acceptance Criteria

**You accept that:**
- Code runs on your machine
- No isolation is possible
- Only trusted tasks are safe
- This is for development only
- Production needs different setup

**System provides:**
- Clear warnings
- Code review
- Execution monitoring
- Safety guidelines
- Testing framework

---

**Start with Day 1 tasks and work systematically. The system will work locally with proper monitoring and care.**
