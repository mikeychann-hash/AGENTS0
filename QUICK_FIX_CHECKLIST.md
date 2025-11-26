# Agent0 Quick Fix Checklist
## DO THIS FIRST - Before Running Anything

**Status:** 🔴 CRITICAL BUGS FOUND  
**Time to Fix:** 2-3 hours  
**Impact:** Blocking - Won't run without these fixes

---

## ⚠️ STOP - Read This First

The codebase review found **critical bugs** that prevent Agent0 from running correctly. Fix these BEFORE attempting to run smoke tests or the loop.

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

## 🛡️ Fix #4: Disable Shell Runner (SECURITY)

**File:** `agent0/configs/3070ti.yaml`  
**Lines:** 31-32  
**Issue:** Shell runner has command injection vulnerability

**Current:**
```yaml
tooling:
  enable_python: true
  enable_shell: true  # DANGEROUS
```

**Fixed:**
```yaml
tooling:
  enable_python: true
  enable_shell: false  # Disabled for security
```

---

## 📝 Fix #5: Add Error Handling (CRITICAL)

**File:** `agent0/loop/coordinator.py`  
**Method:** `run_once`  
**Issue:** No error handling - crashes on any failure

**Add this wrapper:**
```python
def run_once(self, student_signal: Dict[str, Any]) -> Optional[Trajectory]:
    """Run one iteration with error handling"""
    try:
        signal = {**self.scheduler.next_signal(), **student_signal}
        task = self.teacher.generate_task(signal)
        traj = self.student.solve(task)
        
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
        
        return traj
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Iteration failed: {e}", exc_info=True)
        return None
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

### 3. Coordinator Init Test
```bash
python -c "from agent0.loop.coordinator import Coordinator; import yaml; c=yaml.safe_load(open('agent0/configs/3070ti.yaml')); coord=Coordinator(c); print('✓ Coordinator OK')"
```

### 4. Smoke Test
```bash
python -m agent0.scripts.smoke_run --config agent0/configs/3070ti.yaml
```

**Expected Output:**
- No import errors
- No crashes
- Trajectory logged
- "success=True/False" in output

---

## 🚨 Known Limitations After Fixes

Even after these fixes, be aware:

1. **Sandbox doesn't work on Windows**
   - No CPU/memory limits enforced
   - Full filesystem access
   - Can spawn processes

2. **Python runner is not isolated**
   - Can import any module
   - Can read/write files
   - Can make network calls

3. **Teacher generates only linear equations**
   - Math domain only
   - Simple `ax + b = c` format

4. **No logprobs from Ollama**
   - Uncertainty estimation uses fallback
   - Self-critique method only

5. **Test coverage is 0%**
   - No automated validation
   - Manual testing required

---

## 📋 Quick Start After Fixes

Once all fixes are applied:

```bash
# 1. Verify Ollama is running
curl http://localhost:11434/api/tags

# 2. Pull models if needed
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b

# 3. Run smoke test
python -m agent0.scripts.smoke_run --config agent0/configs/3070ti.yaml

# 4. Run short loop (5 iterations)
python -m agent0.scripts.run_loop --config agent0/configs/3070ti.yaml --steps 5

# 5. Check trajectories
cat runs/trajectories.jsonl | tail -5
```

---

## 🎯 Next Steps

After verifying the fixes work:

1. **Read CODEBASE_REVIEW.md** - Understand all issues
2. **Read REVISED_ACTION_PLAN.md** - See the full roadmap
3. **Follow Phase 0 Day 2** - Create SECURITY.md
4. **Continue with Week 1** - Add tests and logging

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

---

## 📞 Getting Help

If you're stuck:
1. Check error message for file/line number
2. Compare that file to fixes above
3. Search for the specific error in logs
4. Review CODEBASE_REVIEW.md for that component

**Common Issues:**
- "NameError: name 'json' is not defined" → Fix #1 not applied
- "No matching groups" in regex → Fix #2 or #3 not applied  
- Hangs on execution → Ollama not running
- "Connection refused" → Check Ollama port

---

## ⏱️ Time Estimate

- **Reading this doc:** 5 minutes
- **Applying fixes:** 15-20 minutes
- **Verification:** 10-15 minutes
- **First successful run:** 5-10 minutes

**Total:** 35-50 minutes to working system

---

## 🎉 Success Indicators

You'll know everything works when:

✅ All import tests pass  
✅ Smoke test completes without crash  
✅ `runs/trajectories.jsonl` has content  
✅ Log shows "success=True" or "success=False"  
✅ No Python exceptions in output  

**Then you're ready for the full roadmap!**

---

*Priority: Fix these before reading anything else or running any code.*  
*Estimated fixes: 30-45 minutes*  
*Impact: Changes system from broken to functional*
