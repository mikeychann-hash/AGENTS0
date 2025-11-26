# Local Development Mode

## SECURITY WARNING

Agent0 is running in **LOCAL DEVELOPMENT MODE**:

- No sandboxing
- No resource limits
- No filesystem isolation
- No network restrictions
- No process isolation

## What This Means

Code execution happens directly on your machine:

- Python code can import any installed module
- Python code can read/write any file you can access
- Python code can make network requests
- Python code can spawn processes
- There are no safety guardrails

## Safe Usage

Only run Agent0 with trusted tasks that you author yourself.

Recommended use cases:
- Personal research and experimentation
- Learning about agent systems
- Prototyping and development
- Testing with known-safe tasks

Do **not** use this configuration for:
- Production deployments
- Processing untrusted input
- Running on shared systems
- Handling sensitive data

## Monitoring Generated Code

Review what the system creates:

```bash
# Check sandbox directory regularly
dir sandbox

# Review generated Python files
type sandbox\*.py

# Check recent trajectories for tool calls
type runs\trajectories.jsonl | findstr "tool_calls"
```

## Recommendations for Higher Isolation

If you need stronger isolation:
1. Run in a dedicated VM
2. Use WSL2 + Docker for sandboxing
3. Deploy to cloud environments with proper isolation
4. Add code review workflows for generated tasks

**This configuration is for LOCAL DEVELOPMENT ONLY.**
