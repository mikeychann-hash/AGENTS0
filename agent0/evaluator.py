"""Evaluator that checks executor outputs and assigns rewards."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from agent0 import tools_bridge
from agent0.tasks import Evaluation, Task, TaskResult


class Evaluator:
    def __init__(self, tools=tools_bridge):
        self.tools = tools

    def evaluate(self, task: Task, result: TaskResult) -> Evaluation:
        if task.domain == "code":
            return self._eval_code(task, result)
        # Default fallback: unknown domain gets neutral score.
        return Evaluation(task_id=task.task_id, score=0.0, passed=False, feedback="Unsupported domain")

    def _eval_code(self, task: Task, result: TaskResult) -> Evaluation:
        # Write solution to a temp file
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
            tmp.write(result.solution)
            tmp_path = Path(tmp.name)

        try:
            output, rc = self.tools.run_shell_command(f"python {tmp_path}")
            passed = rc == 0
            score = 1.0 if passed else -1.0
            feedback = output
        except Exception as exc:  # noqa: BLE001
            passed = False
            score = -1.0
            feedback = f"Execution failed: {exc}"
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

        return Evaluation(task_id=task.task_id, score=score, passed=passed, feedback=feedback)
