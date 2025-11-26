1. Repo status (practical reality check)

Local fork (this workspace) – LOCAL MODE, NO SANDBOX
- Teacher/student agents, co-evolution loop, rewards (uncertainty/tool/novelty + correctness), verifier, logging.
- Models wired via Ollama: teacher `qwen2.5:3b`, student `qwen2.5:7b` (see `agent0/configs/3070ti.yaml`).
- Tools: python runner gated by code review (shell/tests disabled in config), math engine; sandbox is an explicit no-op with warnings; input validator blocks bad tasks.
- Scripts: smoke/loop runners, monitoring (`scripts/monitor_local_execution.py`), logging with local-mode warnings; trajectories log to JSONL.

Upstream GitHub (aiming-lab/Agent0)
- Files: README.md, LICENSE, figs/, .DS_Store. No official code yet; README says “Code: Coming soon.” Community awaiting training/inference code.

2. High-level idea
Agent0 is a self-evolving agent training framework:
- Starts from a base LLM and clones into two roles:
  - Curriculum Agent: invents tasks at the capability frontier.
  - Executor Agent: solves tasks with tools (code interpreter, calculator, search, etc.).
- Co-evolution loop: each agent’s progress pushes the other; tool use is part of the reward.

3. Core architecture (conceptual)
- Curriculum Agent: uses executor performance signals to generate tasks that are hard but solvable and encourage tool use.
- Executor Agent: solves tasks with tool-integrated reasoning; trained from correctness and tool-usage signals.
- Iterative loop: tasks -> solutions -> rewards -> updates; monotonic improvements shown in paper (Qwen3-4B/8B).

4. Tool-integrated reasoning
- Tools are central: executor has math/python (shell disabled by default in local config); curriculum reward factors tool usage.

5. Results (from paper/AIModels summaries)
- Base: Qwen3-8B-Base. After co-evolution: +18% math (MATH, GSM8K), +24% general reasoning (ARC, HellaSwag).
- Gains measured at best checkpoints; improvements across iterations.

6. Strengths / contributions
- Zero human-curated data; curriculum generator vs executor separation; tool-aware training; strong fit for mid-sized LLMs.

7. Limitations / open questions
Upstream:
- No official code; prompts, reward shaping, RL specifics, task formats, tool APIs are unpublished.
- Domain focus: math/general reasoning; unclear for long-horizon coding or complex environments.
- Verification: open-ended tasks need robust automated verifiers.
- Safety: curriculum can drift without constraints.

Local fork status/risks:
- Local-only, no isolation: code runs directly; sandbox is a no-op; shell/tests disabled in config.
- Benchmarks minimal; need full suites (MATH/GSM8K/ARC/Code) and reports.
- Router integration to cloud CLIs is basic; needs production wiring and better confidence fusion.
- Prompts/verifiers for long-horizon coding/logic can be expanded; curriculum scheduler is simple.
- PEFT pipeline needs transformers/peft deps and VRAM budget.
- Uncertainty is heuristic (self-critique); logits-based calibration would be stronger.
- Router to cloud CLIs is stub-level; caching is in-memory only.
