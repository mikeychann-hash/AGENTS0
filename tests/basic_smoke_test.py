import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent0.config import load_config
from agent0.loop import run_round


def test_basic_smoke_round(monkeypatch):
    cfg = load_config("runs/default_config.yaml")
    cfg.num_tasks = 1

    # Use a CLI stub to return deterministic code and avoid backend dependency.
    cfg.llm.backend_type = "cli"
    cfg.llm.cli_command = (
        "python -c \"import json,sys; prompt=sys.stdin.read(); "
        "print(json.dumps({'response':'print(123)'}))\""
    )

    attempts = run_round(cfg)
    assert len(attempts) == 1
    attempt = attempts[0]
    assert attempt.task.task_id
    assert hasattr(attempt, "result")
    assert isinstance(attempt.result.solution, str)
