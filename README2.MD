Agent0 Framework — Technical Brief & Current Implementation Status

Strengths (research/design)
- Clear teacher (curriculum) vs student (executor) separation with co-evolution.
- Zero-data self-curriculum; uncertainty + tool-use rewards encourage frontier tasks.
- Tool-aware training loop, not just inference-time tools.
- Promising reported gains (+18% math, +24% general reasoning on Qwen3-8B-Base).

Local Implementation (this workspace)
- Agents: teacher/student wired to Ollama models (`qwen2.5:3b` teacher, `qwen2.5:7b` student).
- Loop: co-evolution coordinator, reward calculator (uncertainty/tool-use/novelty), verifier, logging to JSONL.
- Tools: sandboxed python/shell/math/test runners with allowlists/workdir/time/mem limits; ReAct prompting for math/logic/code/long; plan execution from LLM tool plans.
- Router: cacheable router with confidence thresholds; manual proxy script to route tasks; cloud CLI hook optional; smoke/loop scripts log routing decisions.
- Training: PEFT (LoRA/QLoRA) trainer over trajectories using transformers/peft/datasets; configurable target (teacher/student).
- Config: 3070 Ti-friendly defaults in `agent0/configs/3070ti.yaml`; Ollama host set; embedding similarity + FAISS optional.
- Benchmarks/metrics: sample math benchmark + runner; metrics aggregator; curriculum scheduler rotates domains and adjusts difficulty; long-horizon prompt added.
- Benchmark suite runner for GSM8K/ARC (downloads via Hugging Face datasets); logic/code samples included.

Upstream status (aiming-lab/Agent0)
- Repo still code-less: README, LICENSE, figs only; “Code: Coming soon.” No published training/inference scripts.

Limitations / risks
- Benchmarks incomplete; router integration to cloud CLIs is basic; confidence fusion is simple.
- Prompts/verifiers for long-horizon coding/logic still to enrich.
- Uncertainty is heuristic/logprob proxy; a stronger logits-based calibrator would be better.
- Sandbox is best-effort on Windows; no hard isolation (containers/VM).
- PEFT pipeline requires transformers/peft/accelerate and sufficient VRAM; assumes HF checkpoints compatible.

Practical implications / uses
- Local agentic booster for math/logic/code tasks to save cloud tokens; route/handoff based on confidence.
- Self-play curriculum + tool use helps teach tool-handling for mid-size local models.
- Extensible to codebases (generate/solve issues/tests) or other domains by adding verifiers and prompts.
