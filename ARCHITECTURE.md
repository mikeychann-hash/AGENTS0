# Agent0 Technical Architecture

## System Overview

Agent0 is a self-evolving agent training framework implementing dual-agent co-evolution with tool-integrated reasoning. The system consists of two primary agents (teacher and student) that improve each other through iterative task generation, execution, and learning.

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent0 Framework                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────┐           ┌────────────┐                    │
│  │  Teacher   │  Tasks    │  Student   │                    │
│  │  Agent     │──────────>│  Agent     │                    │
│  │ (3b model) │           │ (7b model) │                    │
│  └────────────┘           └─────┬──────┘                    │
│        ▲                         │                           │
│        │                         │ Tool Calls                │
│        │                         ▼                           │
│        │                  ┌─────────────┐                   │
│        │                  │   Tool      │                   │
│        │                  │  Executor   │                   │
│        │                  └──────┬──────┘                   │
│        │                         │                           │
│        │    Rewards        ┌─────▼─────┐                    │
│        └───────────────────│ Verifier  │                    │
│                            │ & Rewards │                    │
│                            └───────────┘                    │
│                                  │                           │
│                                  ▼                           │
│                          ┌──────────────┐                   │
│                          │ Trajectories │                   │
│                          │   (JSONL)    │                   │
│                          └──────┬───────┘                   │
│                                  │                           │
│                                  ▼                           │
│                          ┌──────────────┐                   │
│                          │    PEFT      │                   │
│                          │  Training    │                   │
│                          └──────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Agent System (`agent0/agents/`)

#### Teacher Agent (`teacher.py`)
**Purpose:** Generate challenging but solvable tasks at the capability frontier

**Key Responsibilities:**
- Task generation using domain-specific prompts
- Novelty tracking via embeddings
- Uncertainty-seeking task selection
- Curriculum difficulty management

**Inputs:**
- Student performance history
- Domain specification (math/logic/code)
- Novelty constraints (FAISS similarity)

**Outputs:**
- Task specification (description, domain, expected difficulty)
- Metadata (generation timestamp, novelty score)

**Model:** `qwen2.5:3b` (small, fast generation)

#### Student Agent (`student.py`)
**Purpose:** Execute tasks using tool-integrated reasoning

**Key Responsibilities:**
- Task interpretation
- Tool plan generation (ReAct format)
- Tool execution coordination
- Answer synthesis

**Inputs:**
- Task from teacher
- Available tools (python, shell, math, test)
- Execution constraints (timeout, memory)

**Outputs:**
- Solution attempt
- Tool usage logs
- Reasoning trace
- Confidence estimate

**Model:** `qwen2.5:7b` (larger, better reasoning)

#### Supporting Modules

**`prompts.py`, `prompts_code.py`, `prompts_logic.py`, `prompts_long.py`**
- Domain-specific prompt templates
- Few-shot examples
- ReAct formatting guides

**`react_parser.py`**
- Parse LLM output into action sequences
- Extract tool calls from reasoning text
- Handle malformed outputs gracefully

**`uncertainty.py`**
- Estimate solution confidence
- Extract logprobs from model outputs
- Self-critique prompting
- Calibration utilities

---

### 2. Tool System (`agent0/tools/`)

#### Tool Runner Architecture

```
┌──────────────────────────────────────────┐
│         Plan Executor                     │
│  - Parses tool plans from LLM            │
│  - Routes to appropriate runner          │
│  - Handles sequential execution          │
└──────────────┬───────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌─────────────┐  ┌─────────────┐
│   Python    │  │    Shell    │
│   Runner    │  │   Runner    │
└─────────────┘  └─────────────┘
       ▼               ▼
┌─────────────┐  ┌─────────────┐
│    Math     │  │    Test     │
│   Engine    │  │   Runner    │
└─────────────┘  └─────────────┘
       │               │
       └───────┬───────┘
               ▼
        ┌──────────────┐
        │   Sandbox    │
        │  - Workdir   │
        │  - Allowlist │
        │  - Limits    │
        └──────────────┘
```

#### Python Runner (`python_runner.py`)
- Execute Python code in sandboxed environment
- Capture stdout/stderr
- Enforce time and memory limits
- Module allowlist (sympy, math, etc.)

#### Shell Runner (`shell_runner.py`)
- Execute shell commands safely
- Command allowlist (ls, cat, grep, etc.)
- Directory restrictions
- Output capture

#### Math Engine (`math_engine.py`)
- Symbolic computation via SymPy
- Expression parsing
- Equation solving
- Simplification and evaluation

#### Test Runner (`test_runner.py`)
- Execute test cases
- Report pass/fail status
- Capture test output
- Support multiple test frameworks

#### Plan Executor (`plan_executor.py`)
- Orchestrates multi-tool sequences
- Parses LLM tool plans (JSON/ReAct)
- Sequential execution with state
- Error handling and rollback

#### Sandbox (`sandbox.py`)
- Workdir isolation
- Resource limits (CPU, memory, time)
- Allowlist enforcement
- Safe file operations

#### Tooling Config (`tooling_config.py`)
- Tool availability flags
- Timeout configurations
- Memory limits
- Command allowlists

---

### 3. Loop System (`agent0/loop/`)

#### Coordinator (`coordinator.py`)
**Purpose:** Orchestrate the co-evolution loop

**Flow:**
```
1. Teacher generates task
2. Student attempts task with tools
3. Verifier checks correctness
4. Rewards calculated
5. Trajectory logged
6. Repeat or trigger training
```

**Key Features:**
- Iteration management
- State persistence
- Early stopping conditions
- Error recovery

#### Curriculum Scheduler (`curriculum_scheduler.py`)
**Purpose:** Manage task difficulty and domain rotation

**Strategies:**
- Progressive difficulty increase
- Domain diversity enforcement
- Adaptive sampling based on performance
- Novelty injection

**Inputs:**
- Historical performance per domain
- Current iteration count
- Desired diversity metrics

**Outputs:**
- Next domain to sample
- Difficulty level
- Novelty threshold

---

### 4. Reward System (`agent0/rewards/`)

#### Calculator (`calculator.py`)
**Purpose:** Compute multi-faceted rewards for trajectories

**Reward Components:**

1. **Uncertainty Reward**
   - High uncertainty tasks are valuable for learning
   - Based on self-critique + logprob entropy
   - Encourages frontier exploration

2. **Tool Usage Reward**
   - Incentivize using tools appropriately
   - Higher reward for complex tool sequences
   - Penalty for unnecessary tool calls

3. **Novelty Reward**
   - Reward new task types
   - Embedding similarity via sentence-transformers
   - FAISS for efficient similarity search

4. **Correctness Reward**
   - Binary correct/incorrect from verifier
   - Partial credit for partially correct solutions
   - Domain-specific scoring

**Formula:**
```
R_total = w1 * R_uncertainty + w2 * R_tool_use + w3 * R_novelty + w4 * R_correct
```

**Weights:** Configurable in `configs/3070ti.yaml`

---

### 5. Model System (`agent0/models/`)

#### Factory (`factory.py`)
**Purpose:** Abstract model instantiation

**Supported Backends:**
- Ollama (primary)
- llama-cpp-python
- vLLM
- Future: HuggingFace, OpenAI, Anthropic

#### Ollama Client (`ollama_client.py`)
**Features:**
- HTTP API communication
- Streaming support
- Temperature/top_p control
- Logprob extraction
- Model management (pull, list)

#### Base Interface (`base.py`)
**Defines:**
- `generate(prompt, **kwargs)` - single generation
- `stream(prompt, **kwargs)` - streaming generation
- `embed(text)` - embedding generation
- `get_logprobs()` - probability access

---

### 6. Training System (`agent0/training/`)

#### PEFT Trainer (`peft_trainer.py`)
**Purpose:** Fine-tune models on trajectories using LoRA/QLoRA

**Process:**
1. Load trajectories from JSONL
2. Format as instruction tuning pairs
3. Configure LoRA adapters
4. Train with gradient accumulation
5. Save adapter weights

**Configuration:**
```yaml
peft:
  method: lora  # or qlora
  rank: 8
  alpha: 16
  target_modules: [q_proj, v_proj]
  dropout: 0.05
  
training:
  batch_size: 1
  gradient_accumulation: 8
  learning_rate: 1e-4
  epochs: 3
  warmup_steps: 100
```

**Optimizations:**
- Gradient checkpointing
- Mixed precision (bf16)
- CPU offloading for optimizer
- Flash attention (if available)

**Hardware Requirements:**
- Minimum: 8GB VRAM (3070 Ti with QLoRA)
- Recommended: 24GB VRAM (3090 with LoRA)
- Ideal: 40GB+ VRAM (A100 for full fine-tuning)

---

### 7. Task System (`agent0/tasks/`)

#### Schema (`schema.py`)
**Purpose:** Define task data structures

```python
@dataclass
class Task:
    id: str
    domain: str  # math, logic, code, long
    description: str
    difficulty: float  # 0.0-1.0
    created_at: float
    metadata: Dict[str, Any]

@dataclass
class Solution:
    task_id: str
    answer: str
    reasoning: str
    tool_calls: List[ToolCall]
    confidence: float
    execution_time: float

@dataclass
class Trajectory:
    task: Task
    solution: Solution
    verification: VerificationResult
    rewards: Dict[str, float]
    timestamp: float
```

#### Verifier (`verifier.py`)
**Purpose:** Automated solution verification

**Verification Strategies:**

1. **Math Domain**
   - Symbolic equality check
   - Numerical tolerance comparison
   - Step-by-step validation

2. **Logic Domain**
   - Formal proof checking
   - Truth table validation
   - Satisfiability testing

3. **Code Domain**
   - Test case execution
   - Output comparison
   - Static analysis checks

4. **Long-Horizon Domain**
   - Milestone checking
   - Partial progress scoring
   - Multi-stage validation

**Outputs:**
- Binary correct/incorrect
- Confidence score
- Error explanations
- Partial credit breakdown

---

### 8. Router System (`agent0/router/`)

#### Local Router (`local_router.py`)
**Purpose:** Decide when to use local vs cloud models

**Decision Logic:**
```
if task in cache:
    return cached_result
elif confidence > threshold:
    return local_model(task)
else:
    return cloud_model(task)
```

**Features:**
- Confidence-based routing
- Cost estimation
- Latency prediction
- Fallback chains

#### Cloud Bridge (`cloud_bridge.py`)
**Purpose:** Interface with cloud APIs

**Supported Providers:**
- Anthropic (Claude)
- OpenAI (GPT-4)
- Google (Gemini)
- Cohere

**Features:**
- Rate limiting
- Retry logic
- Streaming responses
- Cost tracking

#### CLI Bridge (`cli_bridge.py`)
**Purpose:** Route tasks via command-line tools

**Use Cases:**
- Call existing scripts
- Integrate with local tools
- Batch processing
- Legacy system integration

---

### 9. Memory System (`agent0/memory/`)

#### Embedder (`embedder.py`)
**Purpose:** Generate semantic embeddings for novelty detection

**Model:** `sentence-transformers/all-MiniLM-L6-v2`

**Features:**
- Fast embedding generation
- Batch processing
- Caching
- Similarity search

#### FAISS Store (`faiss_store.py`)
**Purpose:** Efficient similarity search for novelty

**Operations:**
- Add embeddings
- K-nearest neighbors search
- Similarity thresholding
- Index persistence

**Index Type:** FAISS Flat (exact search, small scale)

---

### 10. Configuration System (`agent0/configs/`)

#### 3070ti.yaml
**Purpose:** GPU-optimized configuration

```yaml
models:
  teacher:
    backend: ollama
    name: qwen2.5:3b
    temperature: 0.8
  
  student:
    backend: ollama
    name: qwen2.5:7b
    temperature: 0.6

tools:
  timeout_seconds: 30
  memory_limit_mb: 512
  workdir: ./sandbox

rewards:
  weights:
    uncertainty: 0.3
    tool_use: 0.3
    novelty: 0.2
    correctness: 0.2

training:
  peft_method: qlora
  batch_size: 1
  gradient_accumulation: 8

router:
  confidence_threshold: 0.7
  cache_size: 1000
```

---

## Data Flow

### Training Loop Data Flow

```
1. Teacher.generate_task()
   └─> Task object (domain, description, difficulty)

2. Student.solve_task(task)
   ├─> ReAct reasoning with tool calls
   ├─> Tool execution via sandbox
   └─> Solution object (answer, reasoning, tools used)

3. Verifier.verify(task, solution)
   └─> VerificationResult (correct, confidence, explanation)

4. RewardCalculator.compute(task, solution, verification)
   ├─> Uncertainty score (from logprobs)
   ├─> Tool usage score (from tool calls)
   ├─> Novelty score (from embeddings)
   └─> Total reward

5. Logger.log_trajectory(task, solution, verification, rewards)
   └─> JSONL file: runs/trajectories.jsonl

6. (After N iterations) PEFTTrainer.train(trajectories)
   ├─> Load JSONL
   ├─> Format as instruction pairs
   ├─> Fine-tune with LoRA
   └─> Save checkpoint
```

### Router Request Flow

```
1. User submits task
   └─> Router.route(task)

2. Check cache
   ├─> Hit: return cached result
   └─> Miss: continue

3. Estimate local confidence
   └─> LocalRouter.predict_confidence(task)

4. Decision
   ├─> High confidence: use local model
   └─> Low confidence: use cloud model

5. Execute and cache result
   └─> Cache.set(task_hash, result)

6. Return to user
```

---

## File Structure

```
agent0/
├── agents/              # Agent implementations
│   ├── teacher.py       # Task generation agent
│   ├── student.py       # Task execution agent
│   ├── prompts*.py      # Domain-specific prompts
│   ├── react_parser.py  # ReAct parsing
│   └── uncertainty.py   # Confidence estimation
│
├── configs/             # Configuration files
│   └── 3070ti.yaml      # GPU-optimized config
│
├── logging/             # Logging utilities
│   └── setup.py         # Logger configuration
│
├── loop/                # Co-evolution loop
│   ├── coordinator.py   # Main loop orchestrator
│   └── curriculum_scheduler.py  # Difficulty management
│
├── memory/              # Novelty detection
│   ├── embedder.py      # Embedding generation
│   └── faiss_store.py   # Similarity search
│
├── models/              # Model backends
│   ├── base.py          # Abstract interface
│   ├── factory.py       # Model instantiation
│   ├── ollama_client.py # Ollama integration
│   ├── llama_cpp_client.py  # llama.cpp integration
│   └── vllm_client.py   # vLLM integration
│
├── rewards/             # Reward computation
│   └── calculator.py    # Multi-faceted rewards
│
├── router/              # Task routing
│   ├── local_router.py  # Local vs cloud decisions
│   ├── cloud_bridge.py  # Cloud API integration
│   └── cli_bridge.py    # CLI tool integration
│
├── scripts/             # Runnable scripts
│   ├── smoke_run.py     # Basic functionality test
│   ├── run_loop.py      # Co-evolution loop
│   ├── eval_math.py     # Math benchmark
│   ├── eval_suite.py    # Full benchmark suite
│   ├── router_proxy.py  # Router testing
│   ├── train_peft_stub.py  # PEFT training
│   └── report_metrics.py   # Metrics reporting
│
├── tasks/               # Task definitions
│   ├── schema.py        # Data structures
│   └── verifier.py      # Solution verification
│
├── tools/               # Tool execution
│   ├── python_runner.py # Python sandbox
│   ├── shell_runner.py  # Shell sandbox
│   ├── math_engine.py   # Symbolic math
│   ├── test_runner.py   # Test execution
│   ├── plan_executor.py # Tool orchestration
│   ├── sandbox.py       # Safety layer
│   └── tooling_config.py # Tool settings
│
└── training/            # Model training
    └── peft_trainer.py  # LoRA/QLoRA training

runs/                    # Generated artifacts
├── trajectories.jsonl   # Training data
├── checkpoints/         # Model checkpoints
└── logs/               # Execution logs

benchmarks/             # Benchmark data
└── (dataset files)
```

---

## Key Design Decisions

### Why Teacher-Student Split?
- **Specialization:** Teacher focuses on task generation, student on execution
- **Efficiency:** Smaller teacher model (3b) is faster for generation
- **Co-evolution:** Each agent's progress drives the other forward

### Why Tool Integration?
- **Capability:** LLMs alone struggle with precise computation
- **Training Signal:** Tool usage provides clear reward signals
- **Realism:** Real-world agents need external tool access

### Why PEFT (LoRA/QLoRA)?
- **Efficiency:** Full fine-tuning is expensive (VRAM, time, cost)
- **Flexibility:** Adapters can be swapped/combined
- **Storage:** 10-100MB vs multi-GB full checkpoints

### Why Local-First Routing?
- **Cost:** Cloud API calls are expensive at scale
- **Latency:** Local inference is faster for simple tasks
- **Privacy:** Sensitive tasks stay on-device

### Why JSONL Trajectories?
- **Streamability:** Process line-by-line without loading full file
- **Appendability:** Add new trajectories without rewriting
- **Debuggability:** Human-readable format

---

## Performance Characteristics

### Latency (Single Task)
- Teacher generation: 2-5s
- Student solution: 5-15s (simple), 20-60s (complex)
- Verification: 0.1-2s
- Total loop iteration: 10-70s

### Throughput
- Tasks per hour: 50-300 (depending on complexity)
- Training data generation: 100 trajectories in 1-2 hours

### Resource Usage
- Ollama idle: ~500MB RAM
- Teacher inference: +2GB RAM, ~30% GPU
- Student inference: +4GB RAM, ~60% GPU
- PEFT training: +6GB VRAM, 100% GPU

### Storage
- Trajectory per task: ~1-5KB
- 1000 trajectories: ~1-5MB
- LoRA checkpoint: ~50-500MB
- Full dataset cache: ~5GB

---

## Security Considerations

### Sandbox Isolation
- Workdir restrictions prevent filesystem access
- Command allowlists prevent dangerous operations
- Time limits prevent infinite loops
- Memory limits prevent resource exhaustion

### Current Limitations (Windows)
- Process isolation is weaker than containers
- File system restrictions are advisory
- Privilege escalation possible with exploits

### Recommended Hardening
- Use WSL2 + Docker for true isolation
- Run in dedicated VM for untrusted code
- Implement audit logging for all tool calls
- Add rate limiting for resource-intensive operations

---

## Monitoring & Observability

### Metrics to Track
- Task generation rate
- Solution success rate
- Tool usage patterns
- Training loss/reward curves
- Router decision accuracy
- Latency percentiles
- Cost per task

### Logging Levels
- DEBUG: All tool calls, model interactions
- INFO: Task completions, training steps
- WARN: Verification failures, timeout events
- ERROR: Crashes, API failures

### Alerts
- High failure rate (>50%)
- Resource exhaustion (OOM, timeout)
- Model degradation (reward decrease)
- Cost threshold exceeded

---

## Extension Points

### Adding New Tools
1. Create runner in `tools/`
2. Add to `tooling_config.py`
3. Update `plan_executor.py` router
4. Add to prompts as available tool
5. Test in sandbox environment

### Adding New Domains
1. Create prompt template in `agents/prompts_*.py`
2. Add verifier logic in `tasks/verifier.py`
3. Update `CurriculumScheduler` domain list
4. Add benchmark in `scripts/eval_*.py`

### Adding New Model Backends
1. Implement `base.py` interface
2. Add client in `models/*_client.py`
3. Update `factory.py` to recognize backend
4. Test generation and embeddings
5. Update configs to use new backend

### Adding New Reward Components
1. Add calculation method in `rewards/calculator.py`
2. Update config schema for weight
3. Test on sample trajectories
4. Balance weights with existing components

---

## Troubleshooting

### Common Issues

**"Connection refused" (Ollama)**
- Ensure Ollama is running: `ollama serve`
- Check port 11434 is accessible
- Verify models are pulled: `ollama list`

**"CUDA out of memory"**
- Use QLoRA instead of LoRA
- Reduce batch size to 1
- Enable gradient checkpointing
- Close other GPU applications

**"Tool execution timeout"**
- Increase timeout in config
- Check task is actually solvable
- Review tool implementation for bugs
- Test tool independently

**"No trajectories generated"**
- Check teacher model is generating tasks
- Verify student can connect to tools
- Review verifier isn't rejecting all solutions
- Check JSONL file permissions

---

## Future Enhancements

### Short-Term (1-3 months)
- Container-based sandboxing (Docker)
- Logits-based uncertainty calibration
- Persistent router caching (Redis/SQLite)
- Full benchmark suite integration
- Advanced curriculum scheduling

### Medium-Term (3-6 months)
- Multi-model ensembles
- Distributed training across GPUs
- Web-based monitoring dashboard
- RESTful API service
- VSCode extension

### Long-Term (6+ months)
- Multi-agent collaboration
- Continuous learning from deployment
- Automated hyperparameter tuning
- Custom domain DSLs
- Enterprise deployment patterns

---

## Conclusion

Agent0's architecture balances research flexibility with engineering pragmatism. The modular design allows incremental improvements while the clear interfaces enable testing and extension. The key innovation is the co-evolution loop, where teacher and student agents mutually improve through tool-integrated reasoning and self-generated curriculum.

The current implementation provides a solid foundation for both research experiments and practical applications, with clear paths for scaling to production deployments.
