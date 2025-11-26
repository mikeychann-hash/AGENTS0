Agent0 Local Implementation Plan & Status (Option B: Small Teacher + Larger Student)

Goal
Build a full Agent0-style system locally: dual-agent co-evolution, full tool integration, reward shaping, curriculum evolution, and a token-saving router to cloud CLIs.

Current architecture (implemented) – LOCAL MODE, NO SANDBOX
- Models: Ollama teacher `qwen2.5:3b` (small/fast) and student `qwen2.5:7b` (larger) configured in `agent0/configs/3070ti.yaml`.
- Agents: teacher/student classes with domain-specific prompts (math/logic/code), ReAct parsing, tool-plan execution, and prompt/domain overrides for manual routing.
- Loop: coordinator runs tasks, validates inputs, solves, verifies, logs trajectories to JSONL, computes rewards (uncertainty/self-critique, tool-use, novelty, correctness).
- Tools: python runner gated by code review; math engine enabled; shell/tests disabled in config; sandbox is an explicit no-op with warnings; plan executor wiring present.
- Router: stub with cache and thresholds; proxy script to decide local vs cloud for a given task and cache results.
- Training: PEFT (LoRA/QLoRA) trainer over trajectories using transformers/peft/datasets; selectable target (teacher or student).
- Configs/scripts: smoke_run, run_loop, eval_math, router_proxy, train_peft_stub, monitor_local_execution; trajectories stored under `runs/`.

Token-saving integration
- Local router can decide when to answer locally vs escalate to cloud; caching prevents repeated cloud calls. Proxy script demonstrates the flow; needs wiring to your cloud CLI entrypoints for full integration.

Pending / to improve
- Richer long-horizon prompts/verifiers and more advanced curriculum scheduling.
- Full benchmark suites (GSM8K/ARC/Code) and reporting dashboards (runner added; datasets download required).
- Production-grade router integration with specific cloud CLIs and better confidence fusion.

How to run
1) Install deps: `pip install -r requirements.txt` (includes transformers/peft/accelerate for PEFT; heavy).
2) Ensure Ollama is running with `qwen2.5:3b` and `qwen2.5:7b` pulled.
3) Smoke test: `python -m agent0.scripts.smoke_run --config agent0/configs/3070ti.yaml`
4) Loop: `python -m agent0.scripts.run_loop --config agent0/configs/3070ti.yaml --steps 5`
5) Router proxy: `python -m agent0.scripts.router_proxy --config agent0/configs/3070ti.yaml --task "prove De Morgan's law" --domain logic`
6) PEFT: `python -m agent0.scripts.train_peft_stub --config agent0/configs/3070ti.yaml --data runs/trajectories.jsonl --target student --output ./peft-checkpoints`

Behaviors required (covered)
- Teacher: generates tasks (math by default; can be overridden), tracks novelty, rewards tool-demanding uncertainty.
- Student: uses math/python tools (shell disabled by default), executes LLM-suggested plans, returns reasoning/answer, logs tool calls/metrics; code review gates python execution.

Behaviors pending
- Automated task difficulty grading and richer curriculum scheduling.
- Robust long-horizon verifiers and multi-stage tasks.
- Strong isolation and production router integration to cloud CLIs.
