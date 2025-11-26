# Agent0 Quick Fix Checklist - LOCAL ONLY VERSION
## DO THIS FIRST - Before Running Anything

**Status:** 🔴 CRITICAL BUGS FOUND  
**Time to Fix:** 2-3 hours  
**Impact:** Blocking - Won't run without these fixes

**Environment:** Local development only - NO SANDBOX, NO DOCKER

---

## ⚠️ STOP - Read This First

The codebase review found **critical bugs** that prevent Agent0 from running correctly. Fix these BEFORE attempting to run smoke tests or the loop.

**IMPORTANT:** This is a LOCAL DEVELOPMENT configuration. Code execution happens directly on your machine with NO ISOLATION. Only run trusted code.

---

## 🔧 Fix #1: Missing Imports (BLOCKING)

**File:** `agent0/router/cloud_bridge.py`  
**Line:** After line 2  
**Issue:** Missing imports cause NameError

**Fix:**
```python
from __future__ import annotations

import json  # ADD THIS LINE
from pathlib import Path  # ADD THIS LINE
from typing import Any, Dict, Optional

# ... rest of file ...
```

**How to Apply:**
```bash
# Open the file in any editor
notepad agent0/router/cloud_bridge.py

# Add the two import lines after line 2
# Save and close
```

**Test:**
```python
python -c "from agent0.router.cloud_bridge import CloudRouter; print('✓ OK')"
```

---

## 🔧 Fix #2: Regex Bug in Student (HIGH PRIORITY)

**File:** `agent0/agents/student.py`  
**Line:** 60  
**Issue:** Double backslashes prevent number matching

**Current (BROKEN):**
```python
match = re.search(r"[-+]?\\d+(?:\\.\\d+)?", text)
```

**Fixed:**
```python
match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
```

**How to Apply:**
1. Open `agent0/agents/student.py`
2. Find line 60 (search for `_extract_number`)
3. Replace the double backslashes with single
4. Save

**Test:**
```python
python -c "from agent0.agents.student import StudentAgent; a = StudentAgent({'backend':'ollama','model':'test'}); print('✓ OK')"
```

---

## 🔧 Fix #3: Regex Bug in Uncertainty (HIGH PRIORITY)

**File:** `agent0/agents/uncertainty.py`  
**Line:** 35  
**Issue:** Same double backslash problem

**Current (BROKEN):**
```python
match = re.search(r"0(?:\\.\\d+)?|1(?:\\.0+)?", text)
```

**Fixed:**
```python
match = re.search(r"0(?:\.\d+)?|1(?:\.0+)?", text)
```

**How to Apply:**
1. Open `agent0/agents/uncertainty.py`
2. Find line 35 (search for `_extract_prob`)
3. Fix the backslashes
4. Save

---

## 🔧 Fix #4: Disable Risky Tools (CONFIGURATION)

**File:** `agent0/configs/3070ti.yaml`  
**Lines:** 31-37  
**Issue:** Reduce risk by limiting tool execution

**Update Configuration:**
```yaml
tooling:
  enable_python: true   # Allowed - runs local Python
  enable_shell: false   # DISABLED - too risky without sandbox
  enable_math: true     # Allowed - SymPy only
  enable_tests: false   # DISABLED - runs arbitrary test code
  timeout_seconds: 30   # Increased timeout for local execution
  workdir: ./sandbox
  allowed_shell: []     # Empty - shell disabled anyway
```

**Note:** Even with `enable_python: true`, code runs directly on your machine. Only use with trusted tasks.

---

## 🔧 Fix #5: Simplify Sandbox (REMOVE BROKEN CODE)

**File:** `agent0/tools/sandbox.py`

**Replace entire file with:**
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
    
    WARNING: Only run trusted code!
    """
    logger.warning("Running in local mode - NO RESOURCE LIMITS OR ISOLATION")
    yield


def install_timeout(seconds: int = 10):
    """
    LOCAL DEVELOPMENT MODE: No timeout enforcement.
    
    This is a no-op function for local development.
    """
    logger.warning("Running in local mode - NO TIMEOUT ENFORCEMENT")
    pass
```

**Why:** The original sandbox code doesn't work on Windows and gives false security. Better to be explicit that there's no isolation.

---

## 📝 Fix #6: Add Local Development Warning

**Create new file:** `agent0/LOCAL_DEVELOPMENT.md`

```markdown
# Local Development Mode

## ⚠️ SECURITY WARNING

Agent0 is running in **LOCAL DEVELOPMENT MODE**:

- ✗ No sandboxing
- ✗ No resource limits
- ✗ No filesystem isolation
- ✗ No network restrictions
- ✗ No process isolation

## What This Means

**Code execution happens DIRECTLY on your machine:**
- Python code can import any module
- Python code can read/write any file you can access
- Python code can make network requests
- Python code can spawn processes
- There are NO safety guardrails

## Safe Usage

**ONLY run Agent0 with:**
- Tasks you create yourself
- Trusted prompts
- Known-safe test cases

**DO NOT:**
- Use untrusted prompts
- Run code from unknown sources
- Execute tasks that could damage your system
- Use in production environments

## Acceptable Use Cases

✓ Personal research and experimentation  
✓ Learning about agent systems  
✓ Prototyping and development  
✓ Testing with known-safe tasks  

✗ Production deployments  
✗ Processing untrusted input  
✗ Running on shared systems  
✗ Handling sensitive data  

## Recommendations

For production use, consider:
1. Running in a dedicated VM
2. Using WSL2 + Docker for isolation
3. Deploying to cloud with proper sandboxing
4. Implementing code review for all generated tasks

**This configuration is for LOCAL DEVELOPMENT ONLY.**
```

---

## 📝 Fix #7: Update Configuration Comments

**File:** `agent0/configs/3070ti.yaml`

**Add at the top:**
```yaml
# ============================================
# LOCAL DEVELOPMENT CONFIGURATION
# ============================================
# WARNING: No sandboxing or isolation!
# Code runs directly on your machine.
# Only use with trusted tasks.
# ============================================

# 3070 Ti-friendly defaults (8 GB VRAM target)
# Local development mode - NO DOCKER/SANDBOX
models:
  teacher:
    backend: ollama
    model: qwen2.5:3b
    host: http://127.0.0.1:11434
    context_length: 4096
    temperature: 0.7
    top_p: 0.9
    uncertainty_samples: 3
  student:
    backend: ollama
    model: qwen2.5:7b
    host: http://127.0.0.1:11434
    context_length: 8192
    temperature: 0.6
    top_p: 0.9
    uncertainty_samples: 3

resources:
  device: cuda
  max_gpu_memory_gb: 8
  num_threads: 6
  max_tokens_per_task: 512

tooling:
  # LOCAL MODE: Limited tools for safety
  enable_python: true    # ⚠️ Runs on your machine
  enable_shell: false    # Disabled - too risky
  enable_math: true      # Safe - SymPy only
  enable_tests: false    # Disabled - runs code
  timeout_seconds: 30
  workdir: ./sandbox     # Working directory (not isolated)
  allowed_shell: []      # Shell disabled

rewards:
  weight_uncertainty: 0.5
  weight_tool_use: 0.3
  weight_novelty: 0.2
  target_success_rate: 0.5
  repetition_similarity_threshold: 0.9

logging:
  base_dir: ./runs
  save_every: 10
  flush_every: 1

router:
  enable: true
  cloud_confidence_threshold: 0.7
  local_confidence_threshold: 0.4
  cache_path: ./runs/router_cache.json
  cloud_command: ""

embedding:
  use_transformer: true
  model_name: all-MiniLM-L6-v2
```

---

## ✅ Verification Checklist

After applying all fixes, run these tests:

### 1. Import Test
```bash
python -c "from agent0.router.cloud_bridge import CloudRouter; print('✓ Import OK')"
```

### 2. Config Load Test
```bash
python -c "import yaml; c=yaml.safe_load(open('agent0/configs/3070ti.yaml')); print('✓ Config OK')"
```

### 3. Sandbox Module Test
```bash
python -c "from agent0.tools.sandbox import limit_resources; print('✓ Sandbox module OK')"
```

### 4. Coordinator Init Test
```bash
python -c "from agent0.loop.coordinator import Coordinator; import yaml; c=yaml.safe_load(open('agent0/configs/3070ti.yaml')); coord=Coordinator(c); print('✓ Coordinator OK')"
```

### 5. Smoke Test
```bash
python -m agent0.scripts.smoke_run --config agent0/configs/3070ti.yaml
```

**Expected Output:**
- Warning: "Running in local mode - NO RESOURCE LIMITS OR ISOLATION"
- No import errors
- No crashes
- Trajectory logged
- "success=True/False" in output

---

## 🚨 Understanding Local Development Mode

### What Works
✅ Task generation (teacher agent)  
✅ Task solving (student agent)  
✅ Math engine (SymPy - safe)  
✅ Python code execution (on your machine)  
✅ Reward calculation  
✅ Trajectory logging  
✅ PEFT training  
✅ Router logic  

### What's Disabled
❌ Shell commands (too risky)  
❌ Test execution (runs code)  
❌ Resource limits (impossible without Docker)  
❌ Filesystem isolation (impossible without Docker)  
❌ Network restrictions (impossible without Docker)  

### What You Should Know
⚠️ Python runner executes code directly  
⚠️ Temp files created in ./sandbox directory  
⚠️ No CPU/memory limits enforced  
⚠️ No process isolation  
⚠️ Full access to your filesystem  
⚠️ Can make network requests  

**This is acceptable for:**
- Personal development
- Trusted tasks only
- Learning and experimentation
- Testing on your own machine

**This is NOT acceptable for:**
- Production systems
- Untrusted input
- Shared environments
- Sensitive data processing

---

## 📋 Quick Start After Fixes

Once all fixes are applied:

```bash
# 1. Verify Ollama is running
curl http://localhost:11434/api/tags

# 2. Pull models if needed
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b

# 3. Read the local development warning
cat agent0/LOCAL_DEVELOPMENT.md

# 4. Run smoke test (will show security warnings)
python -m agent0.scripts.smoke_run --config agent0/configs/3070ti.yaml

# 5. Run short loop (5 iterations)
python -m agent0.scripts.run_loop --config agent0/configs/3070ti.yaml --steps 5

# 6. Check trajectories
cat runs/trajectories.jsonl | tail -5

# 7. Review generated Python code in sandbox directory
ls sandbox/
```

---

## 🎯 Safe Usage Guidelines

### Creating Safe Tasks

**Safe Math Tasks:**
```python
# Teacher generates: "Solve for x: 2x + 3 = 11"
# Student uses SymPy or math - this is safe
```

**Safe Code Tasks (review output):**
```python
# Always review what code was generated
# Check ./sandbox/ directory for temp files
# Examine generated code before trusting results
```

### Unsafe Scenarios to Avoid

**Don't let the model generate:**
- File deletion commands
- System modification code
- Network requests to unknown hosts
- Process spawning
- Recursive operations without bounds

**Monitor the sandbox directory:**
```bash
# Regularly check what's being created
ls -la sandbox/

# Review generated Python files
cat sandbox/*.py
```

---

## 💬 If Something Goes Wrong

### Import Errors
- Check you added both `json` and `Path` imports
- Verify file saved correctly
- Restart Python interpreter

### Regex Still Not Matching
- Make sure you changed `\\d` to `\d`
- Check both student.py and uncertainty.py
- Python uses raw strings (r"...") for regex

### Ollama Connection Failed
- Run `ollama serve` in separate terminal
- Check port 11434 is not blocked
- Verify models pulled with `ollama list`

### Smoke Test Crashes
- Read the error message carefully
- Check which file/line caused crash
- Compare to fixes above
- Look for typos in edits

### Security Concerns
- This is local development mode only
- Don't use with untrusted input
- Monitor what code is generated
- Consider VM isolation for risky experiments

---

## 📞 Getting Help

If you're stuck:
1. Check error message for file/line number
2. Compare that file to fixes above
3. Search for the specific error in logs
4. Review warnings in output about local mode

**Common Issues:**
- "NameError: name 'json' is not defined" → Fix #1 not applied
- "No matching groups" in regex → Fix #2 or #3 not applied  
- Hangs on execution → Ollama not running
- "Connection refused" → Check Ollama port
- Warnings about no isolation → Expected in local mode

---

## ⏱️ Time Estimate

- **Reading this doc:** 10 minutes
- **Applying fixes:** 20-25 minutes
- **Verification:** 10-15 minutes
- **First successful run:** 5-10 minutes

**Total:** 45-60 minutes to working system

---

## 🎉 Success Indicators

You'll know everything works when:

✅ All import tests pass  
✅ Smoke test completes without crash  
✅ Warning about local mode appears (expected!)  
✅ `runs/trajectories.jsonl` has content  
✅ Log shows "success=True" or "success=False"  
✅ No Python exceptions in output  
✅ Sandbox directory contains temp files  

**You'll also see warnings about no isolation - this is EXPECTED and CORRECT!**

---

## 🔒 Security Acceptance

By using Agent0 in local development mode, you accept:

- [ ] I understand code runs directly on my machine
- [ ] I understand there is no sandboxing or isolation
- [ ] I will only use trusted, safe tasks
- [ ] I will not process untrusted input
- [ ] I will monitor generated code
- [ ] I understand this is for development only

**If you need production-grade isolation, you must:**
- Use a dedicated VM
- Implement Docker containers
- Deploy to isolated cloud environment
- Or accept these limitations

---

*Priority: Fix these before running any code.*  
*Environment: Local development - NO SANDBOX*  
*Estimated fixes: 45-60 minutes*  
*Impact: Changes system from broken to functional (locally)*
