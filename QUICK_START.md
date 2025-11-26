# Agent0 Quick Start Roadmap

## Week 1: Foundation & Validation

### Day 1: Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Verify Ollama is running
ollama list

# Pull required models
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b

# Run smoke test
python -m agent0.scripts.smoke_run --config agent0/configs/3070ti.yaml
```

**Expected Outcome:** All systems operational, basic task execution working

### Day 2-3: Baseline Metrics
```bash
# Run basic math evaluation
python -m agent0.scripts.eval_math

# Run 10-step co-evolution loop
python -m agent0.scripts.run_loop --config agent0/configs/3070ti.yaml --steps 10

# Check trajectories
ls runs/trajectories.jsonl
```

**Expected Outcome:** Baseline performance documented, loop stable

### Day 4-5: Critical Gap Analysis
- Review uncertainty calculation in `agents/uncertainty.py`
- Test all tool runners (python, shell, math, test)
- Identify top 3 immediate improvements needed
- Document failure modes

**Expected Outcome:** Prioritized improvement list

### Day 6-7: Quick Wins
- Add better error handling to tool runners
- Enhance logging with structured output
- Improve prompt templates in `agents/prompts.py`
- Add basic metrics tracking

**Expected Outcome:** Measurably improved stability

---

## Week 2: Enhanced Capabilities

### Days 8-10: Tool Enhancement
- Add file operation tools
- Improve sandbox safety checks
- Test long-horizon task prompts
- Add tool usage analytics

### Days 11-12: First Training Iteration
```bash
# Generate training data (100 trajectories)
python -m agent0.scripts.run_loop --config agent0/configs/3070ti.yaml --steps 100

# Train student model with PEFT
python -m agent0.scripts.train_peft_stub \
  --config agent0/configs/3070ti.yaml \
  --data runs/trajectories.jsonl \
  --target student \
  --output ./checkpoints/student-v1

# Evaluate improvement
python -m agent0.scripts.eval_math
```

### Days 13-14: Router Hardening
- Add SQLite caching to router
- Test cloud CLI integration
- Implement confidence thresholding
- Add routing metrics

---

## Week 3-4: Benchmarking & Iteration

### Days 15-18: Benchmark Integration
```bash
# Install additional datasets
pip install datasets

# Run GSM8K evaluation
python -m agent0.scripts.eval_suite --dataset gsm8k --samples 100

# Run ARC evaluation
python -m agent0.scripts.eval_suite --dataset arc --samples 100

# Generate report
python -m agent0.scripts.report_metrics
```

### Days 19-21: Training Optimization
- Experiment with LoRA hyperparameters
- Test different reward weightings
- Run curriculum scheduler analysis
- Document optimal settings

### Days 22-28: Documentation & Polish
- Write ARCHITECTURE.md
- Create API documentation
- Add inline code comments
- Write troubleshooting guide
- Create tutorial notebooks

---

## Critical Files to Understand First

### Core Loop
1. `agent0/loop/coordinator.py` - Main co-evolution orchestrator
2. `agent0/agents/teacher.py` - Task generation
3. `agent0/agents/student.py` - Task execution with tools
4. `agent0/rewards/calculator.py` - Reward computation

### Tool System
5. `agent0/tools/plan_executor.py` - Tool orchestration
6. `agent0/tools/python_runner.py` - Code execution
7. `agent0/tools/sandbox.py` - Safety controls
8. `agent0/tools/tooling_config.py` - Tool configuration

### Training
9. `agent0/training/peft_trainer.py` - PEFT training logic
10. `agent0/tasks/verifier.py` - Task verification

### Configuration
11. `agent0/configs/3070ti.yaml` - Main config file

---

## Quick Debugging Checklist

### Ollama Issues
```bash
# Check Ollama service
curl http://localhost:11434/api/tags

# Test model generation
ollama run qwen2.5:3b "2+2="
```

### Tool Execution Issues
- Check sandbox permissions in Windows
- Verify workdir exists and is writable
- Review allowlists in tooling_config.py
- Check time/memory limits aren't too restrictive

### Training Issues
- Verify CUDA available: `python -c "import torch; print(torch.cuda.is_available())"`
- Check VRAM usage: `nvidia-smi`
- Reduce batch size if OOM
- Enable gradient checkpointing

### Router Issues
- Clear cache: delete cache files
- Check confidence thresholds in config
- Verify cloud API keys if using
- Test local-only mode first

---

## Common Issues & Solutions

### Issue: "Model not found"
**Solution:** Run `ollama pull qwen2.5:3b` and `ollama pull qwen2.5:7b`

### Issue: "CUDA out of memory"
**Solutions:**
- Use QLoRA instead of LoRA
- Reduce batch size to 1
- Enable gradient checkpointing
- Use smaller models (3b only)

### Issue: "Tool execution timeout"
**Solutions:**
- Increase timeout in tooling_config.py
- Check if task is actually solvable
- Review tool allowlists
- Test tool independently

### Issue: "No trajectories generated"
**Solutions:**
- Check Ollama connection
- Review task generation prompts
- Verify verifier isn't rejecting all tasks
- Check logging setup

### Issue: "Router always uses cloud"
**Solutions:**
- Lower confidence threshold
- Check cache is working
- Verify local models loaded
- Review routing logic

---

## Performance Optimization Tips

### For 3070 Ti (8GB VRAM)
1. Use QLoRA for training (4-bit quantization)
2. Set batch size = 1
3. Enable gradient checkpointing
4. Use CPU offloading for optimizer states
5. Consider training teacher only (3b model)

### For Token Savings
1. Cache aggressively (router)
2. Use local models for >80% of tasks
3. Batch cloud requests
4. Compress prompts when possible
5. Monitor token usage per task type

### For Speed
1. Keep Ollama warm (always running)
2. Use faster models for teacher
3. Parallel tool execution where safe
4. Optimize prompt lengths
5. Cache embeddings for novelty detection

---

## Testing Commands Quick Reference

```bash
# Smoke test (basic functionality)
python -m agent0.scripts.smoke_run --config agent0/configs/3070ti.yaml

# Short loop (10 iterations)
python -m agent0.scripts.run_loop --config agent0/configs/3070ti.yaml --steps 10

# Math evaluation
python -m agent0.scripts.eval_math

# Benchmark suite
python -m agent0.scripts.eval_suite --dataset gsm8k --samples 50

# Router test
python -m agent0.scripts.router_proxy --config agent0/configs/3070ti.yaml --task "solve x^2 + 5x + 6 = 0" --domain math

# Training test (small run)
python -m agent0.scripts.train_peft_stub --config agent0/configs/3070ti.yaml --data runs/trajectories.jsonl --target student --output ./test-checkpoint

# Metrics report
python -m agent0.scripts.report_metrics
```

---

## Success Indicators by Week

### Week 1 Success
✅ All tests pass  
✅ 10-step loop completes without errors  
✅ Trajectories logged correctly  
✅ Tools execute successfully  
✅ Baseline metrics documented  

### Week 2 Success
✅ First training run completes  
✅ Router caching works  
✅ Tool library expanded  
✅ Some measurable improvement  
✅ Stability improved  

### Week 3-4 Success
✅ GSM8K/ARC benchmarks integrated  
✅ Training shows consistent gains  
✅ Documentation complete  
✅ System ready for extended experiments  
✅ Clear path to production identified  

---

## Next Steps After Week 4

Choose focus area based on goals:

**Research Focus:**
- Experiment with co-evolution dynamics
- Try different reward formulations
- Test novel curriculum strategies
- Publish findings

**Production Focus:**
- Containerize with Docker
- Build REST API
- Create monitoring dashboard
- Deploy to cloud

**Domain Specialization:**
- Focus on code generation
- Optimize for math reasoning
- Build logic puzzle solver
- Create custom domain tools

---

## Getting Help

1. **Check logs:** `runs/*.log` and trajectory files
2. **Review config:** `agent0/configs/3070ti.yaml`
3. **Test components:** Run individual scripts
4. **Monitor resources:** GPU usage, memory, disk
5. **Simplify:** Start with teacher-only or student-only mode

Good luck! Start with Day 1 and work through systematically. The foundation is solid - now it's about validation, enhancement, and optimization.
