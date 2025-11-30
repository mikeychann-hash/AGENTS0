# Agent0 Framework - AI Agent Development Guide

## Project Overview

Agent0 is a self-evolving agent training framework implementing dual-agent co-evolution with tool-integrated reasoning. The system consists of two primary agents (teacher and student) that improve each other through iterative task generation, execution, and learning.

**Key Innovation**: Zero human-curated data required - agents generate their own training curriculum through co-evolution.

**Current Status**: Local implementation, NO SANDBOXING - code runs directly on host machine. Only use with trusted tasks.

## Technology Stack

- **Language**: Python 3.8+
- **LLM Backend**: Ollama (primary), with support for llama-cpp-python and vLLM
- **Models**: Teacher (qwen2.5:3b), Student (qwen2.5:7b)
- **Training**: PEFT (LoRA/QLoRA) with transformers, datasets, peft, accelerate
- **Dependencies**: PyYAML, HTTPx, Pydantic, python-dotenv, SymPy, pytest, sentence-transformers, FAISS

## Architecture

### Core Components

1. **Agent System** (`agent0/agents/`)
   - **Teacher Agent**: Generates challenging tasks at capability frontier
   - **Student Agent**: Executes tasks using tool-integrated reasoning
   - Domain-specific prompts for math, logic, code, and long-horizon tasks

2. **Tool System** (`agent0/tools/`)
   - Python runner (gated by code review)
   - Math engine (SymPy-based)
   - Shell runner (disabled by default for safety)
   - Test runner (disabled by default)
   - **WARNING**: Sandbox is NO-OP - no isolation provided

3. **Loop System** (`agent0/loop/`)
   - Coordinates co-evolution between teacher and student
   - Curriculum scheduler manages task difficulty and domain rotation
   - Logs trajectories to JSONL for training

4. **Reward System** (`agent0/rewards/`)
   - Multi-faceted rewards: uncertainty, tool usage, novelty, correctness
   - Configurable weights in `configs/3070ti.yaml`

5. **Training System** (`agent0/training/`)
   - PEFT trainer for LoRA/QLoRA fine-tuning
   - Processes trajectory data into instruction tuning pairs

## Quick Start

### Prerequisites
```bash
# Install Ollama and pull models
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage
```bash
# Smoke test
python -m agent0.scripts.smoke_run --config agent0/configs/3070ti.yaml

# Run co-evolution loop (10 steps)
python -m agent0.scripts.run_loop --config agent0/configs/3070ti.yaml --steps 10

# Math evaluation
python -m agent0.scripts.eval_math

# Train with PEFT
python -m agent0.scripts.train_peft_stub \
  --config agent0/configs/3070ti.yaml \
  --data runs/trajectories.jsonl \
  --target student \
  --output ./checkpoints
```

## Code Style Guidelines

### Python Conventions
- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Document all public functions with docstrings
- Keep functions focused and modular

### File Organization
- Each module should have a clear purpose
- Use `__init__.py` to expose public APIs
- Keep configuration separate from implementation
- Log extensively for debugging

### Naming Conventions
- Classes: PascalCase (e.g., `TeacherAgent`)
- Functions/Methods: snake_case (e.g., `generate_task`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_TOKENS`)
- Private methods: prefix with underscore (e.g., `_internal_method`)

## Testing Strategy

### Test Structure
```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for system components
└── benchmarks/     # Performance benchmarks
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_agents.py

# Run with coverage
pytest --cov=agent0
```

### Key Test Areas
- Agent task generation and execution
- Tool execution and safety
- Reward calculation accuracy
- Training pipeline functionality
- Router decision making

## Security Considerations

### Current Limitations (CRITICAL)
- **NO SANDBOXING**: Code runs directly on host machine
- **Windows Environment**: Weaker process isolation than containers
- **Disabled Tools**: Shell and test runners disabled by default
- **Code Review**: Python execution gated by review process

### Safety Measures
- Use only with trusted tasks
- Monitor all tool executions
- Keep backups of important data
- Consider VM/container deployment for untrusted code

### Recommended Deployment
- Use WSL2 + Docker for true isolation
- Run in dedicated VM for production
- Implement audit logging
- Add resource limits and rate limiting

## Development Workflow

### Adding New Features
1. Create feature branch
2. Implement with tests
3. Update documentation
4. Run full test suite
5. Submit for review

### Configuration Management
- Main config: `agent0/configs/3070ti.yaml`
- Environment-specific configs in `configs/` directory
- Use environment variables for sensitive data
- Validate all configuration at startup

### Monitoring and Debugging
- Logs stored in `runs/` directory
- Structured logging with levels (DEBUG, INFO, WARN, ERROR)
- Monitor resource usage (GPU, memory, disk)
- Track key metrics (success rates, tool usage, training progress)

## Performance Optimization

### For 8GB VRAM (3070 Ti)
- Use QLoRA (4-bit quantization) for training
- Set batch size to 1
- Enable gradient checkpointing
- Use CPU offloading for optimizer states

### Token Savings
- Cache aggressively in router
- Use local models for >80% of tasks
- Monitor token usage per task type
- Implement smart prompt compression

### Speed Optimization
- Keep Ollama running (avoid cold starts)
- Cache embeddings for novelty detection
- Parallel tool execution where safe
- Optimize prompt templates

## Common Issues and Solutions

### Ollama Connection Issues
```bash
# Check Ollama service
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve
```

### CUDA Out of Memory
- Switch to QLoRA from LoRA
- Reduce batch size to 1
- Enable gradient checkpointing
- Close other GPU applications

### Tool Execution Timeouts
- Increase timeout in config
- Verify task is solvable
- Check tool implementation
- Test tool independently

## Extension Points

### Adding New Tools
1. Create runner in `tools/` directory
2. Add to `tooling_config.py`
3. Update `plan_executor.py`
4. Add to domain prompts
5. Test in safe environment

### Adding New Domains
1. Create prompt template in `agents/prompts_*.py`
2. Add verifier logic in `tasks/verifier.py`
3. Update curriculum scheduler
4. Add benchmark evaluation

### Adding Model Backends
1. Implement `base.py` interface
2. Add client in `models/`
3. Update `factory.py`
4. Test generation and embeddings
5. Update configuration

## Future Roadmap

### Short-term (1-3 months)
- Container-based sandboxing
- Enhanced curriculum scheduling
- Full benchmark integration
- Production router deployment

### Medium-term (3-6 months)
- Multi-model ensembles
- Distributed training
- Web dashboard
- REST API service

### Long-term (6+ months)
- Multi-agent collaboration
- Continuous learning
- Custom domain DSLs
- Enterprise deployment patterns

## Resources

### Key Files to Understand
1. `agent0/loop/coordinator.py` - Main orchestrator
2. `agent0/agents/teacher.py` - Task generation
3. `agent0/agents/student.py` - Task execution
4. `agent0/rewards/calculator.py` - Reward computation
5. `agent0/configs/3070ti.yaml` - Configuration

### Documentation
- `ARCHITECTURE.md` - Detailed technical architecture
- `QUICK_START.md` - Step-by-step setup guide
- `README*.MD` - Implementation status and plans

### Community
- Upstream repository: aiming-lab/Agent0 (code coming soon)
- Local implementation provides research foundation
- Extensible for both research and production use

---

**Remember**: This is a research framework with active development. Always prioritize safety and validate results before production deployment.