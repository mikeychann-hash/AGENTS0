Agent0 Framework — Technical Brief & Current Implementation Status

Strengths (research/design)
- Clear teacher (curriculum) vs student (executor) separation with co-evolution.
- Zero-data self-curriculum; uncertainty + tool-use rewards encourage frontier tasks.
- Tool-aware training loop, not just inference-time tools.
- Promising reported gains (+18% math, +24% general reasoning on Qwen3-8B-Base).

Local Implementation (this workspace) – LOCAL MODE, NO SANDBOX
- Agents: teacher/student wired to Ollama models (`qwen2.5:3b` teacher, `qwen2.5:7b` student).
- Loop: co-evolution coordinator, reward calculator (uncertainty/tool-use/novelty + correctness), verifier, logging to JSONL.
- Tools: python runner gated by code review, math engine enabled; shell/tests disabled in config; sandbox is an explicit no-op with warnings; ReAct prompting for math/logic/code/long; plan execution wiring present.
- Router: cacheable router with confidence thresholds; manual proxy/cloud hook optional; smoke/loop scripts log routing decisions.
- Training: PEFT (LoRA/QLoRA) trainer over trajectories using transformers/peft/datasets; configurable target (teacher/student).
- Config: `agent0/configs/3070ti.yaml` pinned for local use (timeouts bumped, shell/tests off, warning banner); embedding similarity + FAISS optional.
- Benchmarks/metrics: sample math benchmark runner; curriculum scheduler rotates domains; long-horizon prompt added.
- Monitoring/logging: local-mode logger writes warnings to files/console; `scripts/monitor_local_execution.py` reviews sandbox/trajectories.

Upstream status (aiming-lab/Agent0)
- Repo still code-less: README, LICENSE, figs only; “Code: Coming soon.” No published training/inference scripts.

Limitations / risks
- No isolation: runs directly on host; sandbox is a no-op; shell/tests disabled.
- Benchmarks incomplete; router integration to cloud CLIs is basic; confidence fusion is simple.
- Prompts/verifiers for long-horizon coding/logic still to enrich.
- Uncertainty is heuristic/logprob proxy; a stronger logits-based calibrator would be better.
- PEFT pipeline requires transformers/peft/accelerate and sufficient VRAM; assumes HF checkpoints compatible.

Practical implications / uses
- Local agentic booster for math/logic/code tasks to save cloud tokens; route/handoff based on confidence.
- Self-play curriculum + tool use helps teach tool-handling for mid-size local models.
- Extensible to codebases (generate/solve issues/tests) or other domains by adding verifiers and prompts.
