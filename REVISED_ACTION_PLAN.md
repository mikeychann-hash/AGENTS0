# Agent0 Revised Action Plan
## Post-Review: Critical Fixes First

**Review Date:** November 25, 2025  
**Codebase Grade:** C+ (Functional Prototype)  
**Critical Issues:** 12 blocking, 25+ high priority  
**Timeline Adjustment:** +4 weeks for fixes and testing

---

## Crisis Triage: What We Found

### 🔴 BLOCKING (Won't Run)
1. **cloud_bridge.py** - Missing `import json` and `from pathlib import Path`
2. **student.py line 60** - Regex has double backslashes (`\\d` should be `\d`)
3. **uncertainty.py line 35** - Same regex bug

### 🟠 CRITICAL (Security/Safety)
4. **sandbox.py** - Resource limits don't work on Windows
5. **shell_runner.py** - Command injection via `shell=True`
6. **python_runner.py** - No filesystem isolation
7. **verifier.py** - Template injection vulnerability

### 🟡 HIGH PRIORITY (Core Functionality)
8. **rewards/calculator.py** - Missing correctness reward component
9. **coordinator.py** - No error handling in main loop
10. **student.py line 93** - Will crash on malformed prompts
11. **0% test coverage** - No validation
12. **Minimal logging** - Can't debug issues

---

## PHASE 0: Emergency Fixes (Week 1)

**Goal:** Make it runnable and document limitations

### Day 1: Critical Bug Patches

#### Morning: Fix Imports and Regex
```bash
# 1. Fix cloud_bridge.py
cd agent0/router
# Add missing imports at line 3
```

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

#### Afternoon: Add Error Handling
```python
# coordinator.py - Wrap run_once in try-catch
def run_once(self, student_signal: Dict[str, Any]) -> Optional[Trajectory]:
    try:
        signal = {**self.scheduler.next_signal(), **student_signal}
        task = self.teacher.generate_task(signal)
        # ... rest of method
        return traj
    except Exception as e:
        logger.error(f"Loop iteration failed: {e}", exc_info=True)
        return None
```

**Deliverable:** Basic error handling script

---

### Day 2: Security Documentation

#### Create SECURITY.md

```markdown
# Security Limitations

## CRITICAL: This is a Research Prototype

Agent0 has significant security limitations:

### ⚠️ DO NOT USE IN PRODUCTION

1. **Code Execution**: Arbitrary Python/shell code execution
2. **Sandbox Broken**: No isolation on Windows
3. **File System**: Full filesystem access
4. **Network**: Unrestricted network access

### Windows Users

Resource limits (CPU/memory) DO NOT WORK on Windows.
- Use WSL2 + Docker for actual isolation
- Or accept unlimited resource usage

### Required for Production

- [ ] Docker-based sandboxing
- [ ] Input sanitization
- [ ] Command validation
- [ ] Network isolation
- [ ] Audit logging
```

#### Disable Dangerous Features

**Update 3070ti.yaml:**
```yaml
tooling:
  enable_python: true
  enable_shell: false  # DISABLED - security risk
  enable_math: true
  enable_tests: false  # DISABLED until sandboxed
```

**Deliverable:** Security documentation + safer defaults

---

### Day 3: Add Correctness Reward

**File:** `agent0/rewards/calculator.py`

```python
def compute(
    self,
    trajectory: Trajectory,
    success_prob: float,
    novelty_sig: str,
    similarity: Optional[float] = None,
) -> Dict[str, float]:
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
        + 0.3 * r_correct  # NEW COMPONENT
    )

    return {
        "uncertainty": r_unc,
        "tool_use": r_tool,
        "novelty": r_nov,
        "correctness": r_correct,  # NEW
        "total": total,
    }
```

**Deliverable:** Correctness-aware reward system

---

### Day 4: Basic Unit Tests

**Create:** `tests/test_critical_paths.py`

```python
import pytest
from agent0.agents.student import StudentAgent
from agent0.tasks.schema import TaskSpec

def test_number_extraction_basic():
    """Test that number extraction works for simple cases"""
    agent = StudentAgent({
        "backend": "ollama",
        "model": "qwen2.5:7b",
        "host": "http://127.0.0.1:11434"
    })
    
    assert agent._extract_number("The answer is 42") == "42"
    assert agent._extract_number("x = 3.14") == "3.14"
    assert agent._extract_number("negative -5") == "-5"

def test_number_extraction_edge_cases():
    """Test edge cases that were broken"""
    agent = StudentAgent({"backend": "ollama", "model": "test"})
    
    # Should handle no number
    assert agent._extract_number("no number here") is None
    
    # Should handle multiple numbers (takes first)
    result = agent._extract_number("2 + 3 = 5")
    assert result in ["2", "3", "5"]  # At least finds one

def test_prompt_parsing_safety():
    """Test that malformed prompts don't crash"""
    agent = StudentAgent({"backend": "ollama", "model": "test"})
    
    # This used to crash on split(":")
    task = TaskSpec(
        task_id="test",
        domain="math",
        prompt="Solve x + 2 = 5",  # No colon!
        constraints=[],
        verifier=None
    )
    
    # Should not raise exception
    try:
        traj = agent.solve(task)
        assert traj is not None
    except IndexError:
        pytest.fail("Crashed on malformed prompt")
```

**Run tests:**
```bash
pytest tests/test_critical_paths.py -v
```

**Deliverable:** Basic test infrastructure

---

### Day 5: Logging Infrastructure

**Create:** `agent0/logging/detailed_setup.py`

```python
import logging
from pathlib import Path
from typing import Optional

def configure_detailed_logging(
    log_dir: Path,
    level: int = logging.INFO,
    enable_console: bool = True
) -> logging.Logger:
    """Enhanced logging with file rotation and structured output"""
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("agent0")
    logger.setLevel(level)
    
    # File handler with rotation
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_dir / "agent0.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(level)
    
    # Structured format
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Log to errors separately
    error_handler = RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=5*1024*1024,
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger
```

**Deliverable:** Production logging setup

---

### Day 6-7: Smoke Test Marathon

#### Create Comprehensive Smoke Tests

**File:** `tests/test_smoke.py`

```python
import pytest
import yaml
from pathlib import Path
from agent0.loop.coordinator import Coordinator

@pytest.fixture
def config():
    config_path = Path("agent0/configs/3070ti.yaml")
    with config_path.open() as f:
        return yaml.safe_load(f)

def test_ollama_connection(config):
    """Verify Ollama is accessible"""
    import requests
    host = config["models"]["teacher"]["host"]
    response = requests.get(f"{host}/api/tags")
    assert response.status_code == 200

def test_models_available(config):
    """Verify required models are pulled"""
    import requests
    host = config["models"]["teacher"]["host"]
    response = requests.get(f"{host}/api/tags")
    models = [m["name"] for m in response.json()["models"]]
    
    assert "qwen2.5:3b" in models
    assert "qwen2.5:7b" in models

def test_coordinator_initialization(config):
    """Coordinator can initialize without crashing"""
    coord = Coordinator(config)
    assert coord.teacher is not None
    assert coord.student is not None
    assert coord.reward_calc is not None

def test_single_iteration(config):
    """Full iteration completes without crashing"""
    coord = Coordinator(config)
    traj = coord.run_once({"next_task_id": "test-001"})
    
    assert traj is not None
    assert traj.task is not None
    assert traj.result is not None

def test_trajectory_logging(config):
    """Trajectories are written to disk"""
    coord = Coordinator(config)
    traj_file = Path(config["logging"]["base_dir"]) / "trajectories.jsonl"
    
    # Clear old data
    if traj_file.exists():
        traj_file.unlink()
    
    coord.run_once({"next_task_id": "log-test"})
    
    assert traj_file.exists()
    assert traj_file.stat().st_size > 0

def test_error_recovery(config):
    """System handles malformed tasks gracefully"""
    coord = Coordinator(config)
    
    # Malformed signal
    result = coord.run_once({
        "next_task_id": "error-test",
        "prompt_override": "Invalid task with no verifier"
    })
    
    # Should not crash, should return something
    assert result is not None
```

**Run full smoke test suite:**
```bash
# Run all tests
pytest tests/ -v --tb=short

# Run with coverage
pytest tests/ --cov=agent0 --cov-report=html
```

**Deliverable:** Verified working system + test results

---

## Week 1 Deliverables Checklist

- [x] Fixed blocking bugs (imports, regex)
- [x] Added error handling to main loop
- [x] Created security documentation
- [x] Disabled dangerous features by default
- [x] Added correctness reward component
- [x] Created basic unit tests
- [x] Set up proper logging
- [x] Run comprehensive smoke tests
- [x] Document all findings

**Success Criteria:**
1. All smoke tests pass
2. No crashes on basic usage
3. Security limitations documented
4. Test coverage >10%

---

## PHASE 1: Stabilization (Weeks 2-3)

**Goal:** Production-grade error handling and validation

### Week 2: Error Handling and Validation

#### Day 1-2: Input Validation

**Create:** `agent0/validation/`

```python
# task_validator.py
from typing import Dict, List
from agent0.tasks.schema import TaskSpec

class TaskValidator:
    def validate_task(self, task: TaskSpec) -> List[str]:
        """Returns list of validation errors"""
        errors = []
        
        if not task.task_id:
            errors.append("task_id is required")
        
        if not task.domain in ["math", "logic", "code", "long"]:
            errors.append(f"Invalid domain: {task.domain}")
        
        if not task.prompt:
            errors.append("prompt cannot be empty")
        
        if ":" not in task.prompt and task.domain == "math":
            errors.append("Math prompts must contain equation")
        
        return errors
    
    def validate_or_raise(self, task: TaskSpec) -> None:
        errors = self.validate_task(task)
        if errors:
            raise ValueError(f"Task validation failed: {errors}")
```

**Add validation to coordinator:**
```python
# coordinator.py
from agent0.validation.task_validator import TaskValidator

class Coordinator:
    def __init__(self, config):
        # ... existing init ...
        self.validator = TaskValidator()
    
    def run_once(self, student_signal):
        try:
            signal = {**self.scheduler.next_signal(), **student_signal}
            task = self.teacher.generate_task(signal)
            
            # NEW: Validate task
            errors = self.validator.validate_task(task)
            if errors:
                logger.warning(f"Invalid task generated: {errors}")
                return None
            
            # ... rest of method ...
```

#### Day 3-4: Retry Logic

**Create:** `agent0/resilience/retry.py`

```python
import time
import logging
from typing import Callable, TypeVar, Optional
from functools import wraps

T = TypeVar('T')
logger = logging.getLogger(__name__)

def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Decorator for retrying functions with exponential backoff"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt+1}/{max_attempts}): {e}"
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts"
                        )
            
            raise last_exception
        return wrapper
    return decorator
```

**Apply to Ollama client:**
```python
# ollama_client.py
from agent0.resilience.retry import retry_with_backoff
import requests

class OllamaModel(BaseModel):
    @retry_with_backoff(
        max_attempts=3,
        initial_delay=1.0,
        exceptions=(requests.RequestException,)
    )
    def generate(self, prompt: str, **kwargs) -> str:
        # ... existing code ...
```

#### Day 5-7: Comprehensive Testing

**Expand test suite:**

```python
# tests/test_error_handling.py
def test_coordinator_handles_teacher_failure():
    """Coordinator gracefully handles teacher failures"""
    # Mock teacher that raises exception
    pass

def test_coordinator_handles_student_failure():
    """Coordinator gracefully handles student failures"""
    pass

def test_coordinator_handles_verifier_failure():
    """Coordinator gracefully handles verifier failures"""
    pass

def test_retry_logic_ollama():
    """Ollama client retries on network failure"""
    pass

def test_validation_rejects_bad_tasks():
    """Task validator catches invalid tasks"""
    pass
```

**Target: 30% test coverage**

---

### Week 3: Sandbox Hardening

#### Option A: Docker Sandboxing (Recommended)

**Create:** `agent0/tools/docker_runner.py`

```python
import docker
from typing import Dict
import tempfile
from pathlib import Path

class DockerPythonRunner:
    """Execute Python in isolated Docker container"""
    
    def __init__(self):
        self.client = docker.from_env()
        self.image = "python:3.11-slim"
    
    def run_python(
        self,
        code: str,
        timeout: int = 15,
        memory_limit: str = "512m"
    ) -> Dict[str, str]:
        """Run Python code in container"""
        try:
            # Create temp file with code
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False
            ) as f:
                f.write(code)
                code_path = Path(f.name)
            
            # Run in container
            output = self.client.containers.run(
                self.image,
                f"python /code/{code_path.name}",
                volumes={
                    str(code_path.parent): {
                        'bind': '/code',
                        'mode': 'ro'
                    }
                },
                mem_limit=memory_limit,
                network_disabled=True,
                remove=True,
                timeout=timeout
            )
            
            return {
                "status": "ok",
                "stdout": output.decode('utf-8'),
                "stderr": ""
            }
            
        except docker.errors.ContainerError as e:
            return {
                "status": "error",
                "stdout": "",
                "stderr": str(e)
            }
        except Exception as e:
            return {
                "status": "error",
                "stdout": "",
                "stderr": f"Docker error: {e}"
            }
        finally:
            code_path.unlink(missing_ok=True)
```

**Update config:**
```yaml
tooling:
  enable_python: true
  python_runner: "docker"  # or "subprocess" for unsafe
  enable_shell: false
  docker:
    image: "python:3.11-slim"
    memory_limit: "512m"
    network_disabled: true
```

#### Option B: Document Windows Limitations

**Update README:**
```markdown
## Windows Users: Sandboxing Limitations

Agent0's sandbox **does not work** on Windows due to missing `resource` module.

### Options:

1. **WSL2 + Docker** (Recommended)
   - Install WSL2
   - Install Docker Desktop
   - Run Agent0 in WSL2

2. **Accept Limitations**
   - No CPU/memory limits
   - No filesystem isolation
   - Run only trusted code

3. **Virtual Machine**
   - Run in Linux VM
   - Full isolation

**DO NOT run untrusted code on Windows without isolation!**
```

**Deliverable:** Safe execution or documented risks

---

## PHASE 2: Core Improvements (Weeks 4-6)

### Week 4: Enhanced Task Generation

**Goal:** Multi-domain task generation

**Create domain-specific generators:**

```python
# agents/task_generators/
# - math_generator.py (linear, quadratic, calculus)
# - logic_generator.py (proofs, puzzles, reasoning)
# - code_generator.py (algorithms, debugging, refactoring)
# - long_generator.py (multi-step, planning)
```

**Example - math_generator.py:**
```python
from typing import Dict
import random

class MathTaskGenerator:
    def generate_linear(self, difficulty: float) -> Dict:
        """Generate linear equation ax + b = c"""
        max_coef = int(difficulty * 10) + 1
        a = random.randint(1, max_coef)
        b = random.randint(-20, 20)
        x = random.randint(-10, 10)
        c = a * x + b
        
        return {
            "prompt": f"Solve for x: {a}x + {b} = {c}",
            "answer": x,
            "difficulty": difficulty
        }
    
    def generate_quadratic(self, difficulty: float) -> Dict:
        """Generate quadratic equation"""
        # Ensure integer solutions
        r1, r2 = random.randint(-5, 5), random.randint(-5, 5)
        # (x - r1)(x - r2) = x^2 - (r1+r2)x + r1*r2
        b = -(r1 + r2)
        c = r1 * r2
        
        return {
            "prompt": f"Solve: x^2 + {b}x + {c} = 0",
            "answer": [r1, r2],
            "difficulty": difficulty
        }
```

---

### Week 5: Reward System Enhancement

**Implement sophisticated reward calculation:**

```python
# rewards/advanced_calculator.py
class AdvancedRewardCalculator(RewardCalculator):
    def compute_detailed(self, trajectory, metadata):
        """Compute rewards with breakdown"""
        
        # 1. Task-dependent correctness weight
        correctness_weight = self._get_correctness_weight(trajectory.task.domain)
        
        # 2. Calibrated uncertainty
        calibrated_uncertainty = self._calibrate_uncertainty(
            trajectory.task.domain,
            metadata.get("uncertainty", 0.5)
        )
        
        # 3. Tool efficiency (not just usage)
        tool_efficiency = self._compute_tool_efficiency(
            trajectory.tool_calls,
            trajectory.task.domain
        )
        
        # 4. Progressive difficulty bonus
        difficulty_bonus = self._difficulty_bonus(
            trajectory.task.difficulty,
            trajectory.success
        )
        
        # 5. Temporal decay for novelty
        novelty_score = self._novelty_with_decay(
            trajectory.task,
            metadata.get("similarity", 0.0)
        )
        
        return {
            "correctness": ...,
            "uncertainty": ...,
            "tool_efficiency": ...,
            "difficulty_bonus": ...,
            "novelty": ...,
            "total": ...
        }
```

---

### Week 6: Router Production Readiness

**Implement proper cloud integration:**

```python
# router/cloud_providers.py
from typing import Protocol

class CloudProvider(Protocol):
    def complete(self, prompt: str, **kwargs) -> str: ...

class AnthropicProvider:
    def __init__(self, api_key: str):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def complete(self, prompt: str, max_tokens: int = 1000) -> str:
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

class OpenAIProvider:
    def __init__(self, api_key: str):
        import openai
        self.client = openai.OpenAI(api_key=api_key)
    
    def complete(self, prompt: str, max_tokens: int = 1000) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
```

**Enhanced router with cost tracking:**

```python
# router/production_router.py
class ProductionRouter:
    def __init__(self, config: Dict):
        self.providers = self._init_providers(config)
        self.cost_tracker = CostTracker()
        self.cache = PersistentCache(config["cache_path"])
    
    def route_with_cost(self, task: str, confidence: float):
        """Route considering cost and confidence"""
        
        # Check cache first
        cached = self.cache.get(task)
        if cached:
            return cached, 0.0  # No cost
        
        # Estimate costs
        local_cost = 0.0  # Free
        cloud_cost = self._estimate_cloud_cost(task)
        
        # Decision logic
        if confidence > 0.8:
            result = self._run_local(task)
            cost = local_cost
        elif cloud_cost < self.config["max_cost_per_task"]:
            result = self._run_cloud(task)
            cost = cloud_cost
        else:
            result = self._run_local(task)  # Fallback to local
            cost = local_cost
        
        # Cache and track
        self.cache.set(task, result)
        self.cost_tracker.log(task, cost)
        
        return result, cost
```

---

## PHASE 3: Benchmarking & Training (Weeks 7-10)

### Week 7-8: Benchmark Integration

**Integrate standard datasets:**

```python
# scripts/download_benchmarks.py
from datasets import load_dataset

def download_all_benchmarks():
    """Download and cache all benchmark datasets"""
    
    datasets = {
        "gsm8k": load_dataset("gsm8k", "main"),
        "math": load_dataset("hendrycks/math"),
        "arc": load_dataset("ai2_arc", "ARC-Challenge"),
        "hellaswag": load_dataset("hellaswag"),
        "human_eval": load_dataset("openai_humaneval"),
    }
    
    # Convert to Agent0 format
    for name, dataset in datasets.items():
        convert_to_agent0_format(name, dataset)
```

**Run comprehensive evaluation:**

```bash
# Evaluate on all benchmarks
python -m agent0.scripts.eval_suite \
  --config agent0/configs/3070ti.yaml \
  --benchmarks gsm8k,math,arc \
  --samples 100 \
  --output ./results/baseline.json
```

---

### Week 9-10: Training Optimization

**Enhanced PEFT training:**

```python
# training/optimized_trainer.py
class OptimizedPEFTTrainer:
    def train_with_validation(
        self,
        train_data: Path,
        val_data: Path,
        config: PeftConfig
    ):
        """Training with validation and early stopping"""
        
        # Load and split data
        train_dataset = self.load_trajectories(train_data)
        val_dataset = self.load_trajectories(val_data)
        
        # Configure training
        training_args = TrainingArguments(
            output_dir=config.output_dir,
            num_train_epochs=config.num_epochs,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=8,
            learning_rate=2e-4,
            warmup_steps=100,
            logging_steps=10,
            eval_strategy="steps",
            eval_steps=50,
            save_steps=200,
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            fp16=True,  # Mixed precision
            gradient_checkpointing=True,  # Memory efficiency
        )
        
        # Early stopping
        early_stopping = EarlyStoppingCallback(
            early_stopping_patience=3,
            early_stopping_threshold=0.01
        )
        
        # Train
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            callbacks=[early_stopping],
            compute_metrics=self._compute_metrics
        )
        
        trainer.train()
        return trainer
```

---

## Timeline Summary

### Weeks 1-3: Critical Fixes & Stabilization
- Week 1: Bug fixes, security docs, basic tests
- Week 2: Error handling, validation, retry logic
- Week 3: Sandbox hardening (Docker or docs)

### Weeks 4-6: Core Improvements
- Week 4: Multi-domain task generation
- Week 5: Advanced reward system
- Week 6: Production router

### Weeks 7-10: Benchmarking & Training
- Week 7-8: Benchmark integration and baseline
- Week 9-10: Optimized training pipeline

### Weeks 11-16: Original Phases 3-6
- Continue with original plan from Phase 3 onward

---

## Success Metrics (Revised)

### Week 1 (Emergency Fixes)
- ✓ All smoke tests pass
- ✓ No crashes on basic usage
- ✓ Security documented
- ✓ Test coverage >10%

### Week 3 (Stabilization)
- ✓ Test coverage >30%
- ✓ Error handling comprehensive
- ✓ Safe execution (Docker or docs)

### Week 6 (Core Improvements)
- ✓ Multi-domain tasks working
- ✓ Reward system validated
- ✓ Router integrates cloud APIs
- ✓ Test coverage >50%

### Week 10 (Training Ready)
- ✓ Benchmarks integrated
- ✓ Training shows improvement
- ✓ System stable for 100+ iterations
- ✓ Ready for extended experiments

---

## Risk Mitigation

### Technical Risks

**Risk:** Can't fix Windows sandbox  
**Mitigation:** Document limitations, recommend WSL2+Docker

**Risk:** Training doesn't improve performance  
**Mitigation:** Start with known-working hyperparameters from literature

**Risk:** Cloud APIs too expensive  
**Mitigation:** Aggressive caching, cost limits in config

### Project Risks

**Risk:** Scope creep delays critical fixes  
**Mitigation:** Strict phase gating, prioritize P0/P1 only

**Risk:** Upstream code release conflicts  
**Mitigation:** Modular design allows swapping components

---

## Next Immediate Actions

### Right Now (Today)

1. ✅ **Review complete** - Read this document
2. **Apply emergency patches** - Fix imports and regex
3. **Run smoke test** - Verify it works
4. **Document limitations** - Create SECURITY.md

### This Week

5. Add error handling to coordinator
6. Create basic test suite
7. Set up proper logging
8. Run comprehensive tests

### Next Week

9. Implement validation system
10. Add retry logic
11. Expand test coverage to 30%

**Start with Day 1 tasks and work systematically through the phases. Don't skip ahead!**

---

## Conclusion

The codebase is a **functional prototype with critical gaps**. With systematic fixes over 3-4 weeks, it can become a **stable foundation** for research and development.

**Key Changes from Original Plan:**
- Added Phase 0 (emergency fixes)
- Extended timeline by 4 weeks
- Prioritized security and testing
- More realistic milestones

**The good news:** The architecture is solid. Once critical bugs are fixed and tests are added, the path to production is clear.

**Priority:** Fix the bugs, add tests, then enhance. Don't build on a broken foundation!
