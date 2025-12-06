# Agent0 (Local) - Overview

## What This Is
Agent0 is a lightweight, local-first framework for generating coding tasks, solving them with an executor LLM, and evaluating results. It runs without sandboxing: code executes directly on your machine.

## Install
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run a Round
```bash
python scripts/run_local_round.py
```
Config defaults to `runs/default_config.yaml`. Override with `--config`.

## Logs
Outputs are saved to `runs/logs/` as JSON files named `<run_name>_<timestamp>.json`.

## Architecture
- Curriculum: generates tasks via `CurriculumAgent` (LLM-backed or fallback).
- Executor: solves tasks via `ExecutorAgent`, producing code.
- Evaluator: runs code for `domain="code"` tasks and scores pass/fail.
- Loop: wires curriculum → executor → evaluator, persists attempts.

## Future Enhancements
- Integrate full `claude_tools.py`.
- MCP server and tool routing.
- Multi-agent roles and coordination.
- Minecraft/Node integration.
