# Agent0 Project Plan

## Executive Summary

Agent0 is a self-evolving agent training framework implementing a teacher-student co-evolution system. The teacher (curriculum agent) generates frontier tasks while the student (executor agent) solves them using tools. Both agents learn from each other in an iterative loop, with the goal of improving reasoning and tool-use capabilities without human-curated data.

**Current Status:** Foundational scaffold implemented, models wired, basic loop functional  
**Target:** Production-ready system with robust benchmarking, cloud integration, and PEFT training

---

## Architecture Overview

### Core Components (Implemented)

1. **Dual Agent System**
   - Teacher Agent: `qwen2.5:3b` (small/fast curriculum generator)
   - Student Agent: `qwen2.5:7b` (larger executor with tool capabilities)
   - Both run via Ollama locally

2. **Co-Evolution Loop**
   - Task generation by teacher
   - Task execution by student with tools
   - Verification and reward calculation
   - Trajectory logging to JSONL
   - Iterative improvement cycle

3. **Tool Integration**
   - Python runner (sandboxed execution)
   - Shell runner (with allowlists)
   - Math engine (sympy-based)
   - Test runner
   - Plan executor for LLM tool suggestions
   - Safety: workdir isolation, time/memory limits

4. **Reward System**
   - Uncertainty-based rewards (self-critique + logprob proxies)
   - Tool-usage rewards
   - Novelty rewards (embedding similarity + FAISS)

5. **Router System**
   - Local-first with cloud fallback
   - Confidence thresholding
   - In-memory caching
   - Token-saving optimization

6. **Training Pipeline**
   - PEFT (LoRA/QLoRA) trainer
   - Trajectory-based learning
   - Configurable for teacher or student updates

---

## Phase 1: Foundation Solidification (CURRENT)

### Objectives
- Validate existing implementation
- Fix critical gaps
- Establish baseline metrics

### Tasks

#### 1.1 Environment Setup & Validation
- [ ] Verify all dependencies install correctly
- [ ] Test Ollama connectivity with both models
- [ ] Run smoke test suite
- [ ] Validate sandboxing on Windows
- [ ] Check CUDA/GPU availability for PEFT

#### 1.2 Core Loop Testing
- [ ] Run 5-step co-evolution loop
- [ ] Validate trajectory logging format
- [ ] Verify reward calculations
- [ ] Test tool execution across all domains (math/logic/code)
- [ ] Check ReAct parser with various outputs

#### 1.3 Initial Benchmarking
- [ ] Run eval_math.py on sample problems
- [ ] Document baseline performance metrics
- [ ] Test verifier accuracy across domains
- [ ] Identify weak points in current prompts

#### 1.4 Documentation
- [ ] Create ARCHITECTURE.md documenting all components
- [ ] Document config options in 3070ti.yaml
- [ ] Add inline code documentation
- [ ] Create troubleshooting guide

**Deliverables:**
- Working baseline system
- Performance metrics dashboard
- Complete documentation set
- List of prioritized improvements

**Timeline:** 1-2 weeks

---

## Phase 2: Enhanced Tool Integration

### Objectives
- Expand tool capabilities
- Improve sandboxing and safety
- Add long-horizon task support

### Tasks

#### 2.1 Tool Expansion
- [ ] Add web search tool integration
- [ ] Implement file operations toolkit (read/write/edit)
- [ ] Add code analysis tools (linting, testing frameworks)
- [ ] Create database query tool (SQLite)
- [ ] Add API calling capabilities

#### 2.2 Sandbox Hardening
- [ ] Evaluate Docker/container isolation options
- [ ] Implement resource monitoring dashboard
- [ ] Add rollback/snapshot capabilities
- [ ] Create allowlist management system
- [ ] Add execution timeout with graceful handling

#### 2.3 Long-Horizon Tasks
- [ ] Expand prompts_long.py with multi-step reasoning
- [ ] Create task decomposition system
- [ ] Add intermediate state tracking
- [ ] Implement multi-turn task execution
- [ ] Build verification for complex workflows

#### 2.4 Prompt Engineering
- [ ] Refine math domain prompts
- [ ] Enhance logic reasoning templates
- [ ] Improve code generation prompts
- [ ] Add domain-specific few-shot examples
- [ ] Create prompt versioning system

**Deliverables:**
- Extended tool library (10+ tools)
- Hardened sandbox environment
- Multi-step task execution framework
- Improved prompt library

**Timeline:** 2-3 weeks

---

## Phase 3: Robust Benchmarking & Evaluation

### Objectives
- Implement comprehensive benchmark suites
- Create automated evaluation pipeline
- Track improvement over iterations

### Tasks

#### 3.1 Benchmark Implementation
- [ ] Integrate GSM8K dataset (math reasoning)
- [ ] Add MATH benchmark (advanced math)
- [ ] Implement ARC dataset (general reasoning)
- [ ] Add HellaSwag (common sense)
- [ ] Create HumanEval integration (code)
- [ ] Add MBPP (code generation)

#### 3.2 Evaluation Pipeline
- [ ] Automate benchmark runs after training
- [ ] Create metric aggregation system
- [ ] Build comparison reports (iteration-over-iteration)
- [ ] Add statistical significance testing
- [ ] Create visualization dashboard

#### 3.3 Domain-Specific Evals
- [ ] Create custom math problem sets
- [ ] Build logic puzzle test suite
- [ ] Add coding challenge problems
- [ ] Implement real-world task scenarios
- [ ] Create adversarial test cases

#### 3.4 Metrics & Analytics
- [ ] Track tool usage patterns
- [ ] Monitor uncertainty calibration
- [ ] Measure curriculum diversity
- [ ] Analyze failure modes
- [ ] Create learning curves visualization

**Deliverables:**
- 6+ integrated benchmark suites
- Automated evaluation pipeline
- Interactive metrics dashboard
- Detailed performance reports

**Timeline:** 2-3 weeks

---

## Phase 4: Production Router & Cloud Integration

### Objectives
- Build production-grade routing system
- Integrate with cloud API providers
- Optimize token usage and costs

### Tasks

#### 4.1 Router Enhancement
- [ ] Implement confidence fusion algorithms
- [ ] Add multi-model routing (Claude, GPT-4, etc.)
- [ ] Build persistent caching layer (Redis/SQLite)
- [ ] Create routing strategy selector
- [ ] Add cost estimation and budgeting

#### 4.2 Cloud Integration
- [ ] Integrate Anthropic Claude API
- [ ] Add OpenAI GPT-4 support
- [ ] Implement streaming responses
- [ ] Add rate limiting and retry logic
- [ ] Create fallback chains

#### 4.3 Optimization
- [ ] Implement prompt compression
- [ ] Add response caching strategies
- [ ] Build cost-aware routing
- [ ] Create token usage analytics
- [ ] Optimize batch processing

#### 4.4 Monitoring
- [ ] Add request/response logging
- [ ] Track routing decisions
- [ ] Monitor latency and errors
- [ ] Create alerting system
- [ ] Build usage analytics dashboard

**Deliverables:**
- Production router service
- Multi-cloud integration
- Cost optimization framework
- Monitoring and analytics suite

**Timeline:** 2-3 weeks

---

## Phase 5: Advanced Training & Fine-Tuning

### Objectives
- Optimize PEFT training pipeline
- Implement curriculum learning strategies
- Achieve measurable performance gains

### Tasks

#### 5.1 PEFT Pipeline Optimization
- [ ] Optimize LoRA rank and alpha hyperparameters
- [ ] Test QLoRA for memory efficiency
- [ ] Implement gradient accumulation
- [ ] Add mixed precision training
- [ ] Create checkpoint management system

#### 5.2 Curriculum Evolution
- [ ] Implement difficulty grading system
- [ ] Add adaptive curriculum scheduler
- [ ] Create domain rotation strategies
- [ ] Build novelty detection improvements
- [ ] Add curriculum analysis tools

#### 5.3 Reward Shaping
- [ ] Refine uncertainty estimation (logits-based)
- [ ] Enhance tool-usage rewards
- [ ] Add multi-objective reward balancing
- [ ] Implement reward normalization
- [ ] Create reward debugging tools

#### 5.4 Training Experiments
- [ ] Run baseline training (teacher only)
- [ ] Test student-only training
- [ ] Experiment with co-evolution schedules
- [ ] Try different model size combinations
- [ ] Document optimal hyperparameters

#### 5.5 Model Management
- [ ] Create model versioning system
- [ ] Implement A/B testing framework
- [ ] Add model comparison tools
- [ ] Build rollback capabilities
- [ ] Create model card documentation

**Deliverables:**
- Optimized training pipeline
- Adaptive curriculum system
- Trained model checkpoints
- Training experiment reports
- Model management system

**Timeline:** 3-4 weeks

---

## Phase 6: Extension & Productization

### Objectives
- Add specialized capabilities
- Create deployment options
- Build user interfaces

### Tasks

#### 6.1 Specialized Domains
- [ ] Add code refactoring capabilities
- [ ] Implement bug detection/fixing
- [ ] Create test generation system
- [ ] Add documentation generation
- [ ] Build code review assistant

#### 6.2 Deployment Options
- [ ] Create Docker containers
- [ ] Build REST API service
- [ ] Add CLI interface improvements
- [ ] Implement batch processing mode
- [ ] Create deployment documentation

#### 6.3 User Interfaces
- [ ] Build web dashboard (monitoring)
- [ ] Create task submission UI
- [ ] Add trajectory visualization
- [ ] Build configuration management UI
- [ ] Create admin panel

#### 6.4 Integration Examples
- [ ] VSCode extension prototype
- [ ] Jupyter notebook integration
- [ ] GitHub Actions workflow
- [ ] Discord/Slack bot
- [ ] API client libraries (Python/JS)

**Deliverables:**
- Specialized domain modules
- Multi-format deployment packages
- Web dashboard
- Integration examples
- User documentation

**Timeline:** 3-4 weeks

---

## Technical Debt & Known Issues

### High Priority
1. **Uncertainty Estimation:** Currently heuristic-based; needs logits-based calibration
2. **Sandbox Isolation:** Best-effort on Windows; needs container/VM isolation
3. **Router Integration:** Stub-level cloud CLI integration; needs production wiring
4. **Confidence Fusion:** Simple threshold-based; needs sophisticated multi-model fusion

### Medium Priority
5. **Benchmark Coverage:** Limited test suites; needs full GSM8K/MATH/ARC/Code integration
6. **Long-Horizon Prompts:** Basic templates; needs richer multi-step reasoning
7. **Curriculum Scheduler:** Simple difficulty adjustment; needs adaptive grading
8. **Caching:** In-memory only; needs persistent layer

### Low Priority
9. **Logging:** Basic JSONL; needs structured logging with search
10. **Config Management:** Single YAML; needs environment-specific configs
11. **Error Handling:** Basic try-catch; needs comprehensive error taxonomy
12. **Testing:** Minimal pytest; needs full unit/integration test coverage

---

## Success Metrics

### Performance Targets
- **Math Reasoning (GSM8K):** +15% improvement over baseline
- **General Reasoning (ARC):** +20% improvement over baseline
- **Code Generation (HumanEval):** +10% improvement over baseline
- **Tool Usage Rate:** >80% of tasks use at least one tool
- **Uncertainty Calibration:** <0.1 expected calibration error

### System Metrics
- **Latency:** <5s for simple tasks, <30s for complex tasks
- **Token Savings:** >50% reduction via local-first routing
- **Sandbox Safety:** 0 escapes, 100% resource enforcement
- **Training Stability:** <5% checkpoint performance variance

### Quality Metrics
- **Curriculum Diversity:** >100 unique task patterns per 1000 iterations
- **Verification Accuracy:** >95% correct accept/reject decisions
- **Model Improvement:** Monotonic gains across training iterations
- **Cost Efficiency:** <$0.10 per training iteration (cloud costs)

---

## Resource Requirements

### Compute
- **Development:** 1x RTX 3070 Ti (8GB VRAM) - sufficient for inference
- **Training:** 1x RTX 3090 (24GB VRAM) or cloud GPU - needed for PEFT
- **Production:** CPU-based routing + GPU inference cluster

### Storage
- **Trajectories:** ~1GB per 10K iterations
- **Model Checkpoints:** ~500MB per checkpoint (LoRA)
- **Benchmarks:** ~5GB for full dataset collection
- **Logs/Cache:** ~100MB per day

### API Costs (Estimated)
- **Development:** $50-100/month (cloud routing tests)
- **Production:** $200-500/month (depending on volume)

---

## Risk Assessment

### Technical Risks
1. **VRAM Limitations:** 3070 Ti may struggle with larger models/batches
   - *Mitigation:* Use QLoRA, gradient checkpointing, smaller batch sizes
2. **Windows Sandboxing:** Harder to isolate than Linux containers
   - *Mitigation:* Use WSL2 with Docker, or cloud Linux instances
3. **Model Quality:** Qwen 2.5 may not reach target performance
   - *Mitigation:* Test alternative models (Mistral, Llama 3), ensemble approaches

### Research Risks
4. **Co-Evolution Instability:** Agents may diverge or collapse
   - *Mitigation:* Add stability constraints, curriculum guardrails
5. **Reward Hacking:** Agents may exploit reward signals
   - *Mitigation:* Multi-faceted rewards, adversarial testing
6. **Verification Brittleness:** Hard to verify open-ended tasks
   - *Mitigation:* Conservative verification, human-in-the-loop validation

### Project Risks
7. **Upstream Code Release:** Official Agent0 code may differ significantly
   - *Mitigation:* Modular design allows easy integration of official components
8. **Scope Creep:** Many interesting directions could delay core goals
   - *Mitigation:* Strict phase gating, MVP focus

---

## Next Immediate Actions

1. **Run Complete Validation** (Day 1)
   - Execute smoke_run.py and verify all systems work
   - Run run_loop.py with 5 steps and check trajectories
   - Test all tool runners independently

2. **Baseline Benchmarking** (Days 2-3)
   - Run eval_math.py and document results
   - Test a few GSM8K problems manually
   - Record current capabilities and failure modes

3. **Priority Gap Fixes** (Days 4-7)
   - Improve uncertainty estimation (add logprob extraction)
   - Enhance router caching (add SQLite persistence)
   - Expand prompts_long.py with better examples

4. **First Training Run** (Week 2)
   - Generate 100 trajectories via loop
   - Run train_peft_stub.py on student model
   - Evaluate improvement on test set

5. **Documentation Sprint** (Week 2-3)
   - Write ARCHITECTURE.md
   - Document all config options
   - Create setup and troubleshooting guides

---

## Conclusion

Agent0 has a solid foundation with all core components implemented. The path to production involves:
1. Validating and hardening the existing system
2. Expanding tool and benchmark capabilities
3. Optimizing the training pipeline for measurable gains
4. Building production-grade routing and monitoring
5. Creating deployment artifacts and user interfaces

The modular architecture allows incremental progress, with each phase delivering tangible value. The key challenge is balancing research exploration (co-evolution dynamics, reward shaping) with engineering rigor (testing, monitoring, deployment).

**Recommended Start:** Phase 1 tasks to establish a solid baseline, then prioritize based on your specific use case (research vs. production, local vs. cloud focus, domain specialization).
