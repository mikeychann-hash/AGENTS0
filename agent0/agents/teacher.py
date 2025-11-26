from __future__ import annotations

import json
from typing import Any, Dict

from agent0.models.factory import create_model
from agent0.agents.prompts import TEACHER_PROMPT
from agent0.tasks.schema import TaskSpec, VerifierSpec


class TeacherAgent:
    """Generates tasks targeting the student's learning frontier."""

    def __init__(self, model_config: Dict[str, Any]) -> None:
        self.model_config = model_config
        self.model = create_model(model_config)

    def _parse_params(self, raw: str) -> Dict[str, int]:
        try:
            data = json.loads(raw.strip().splitlines()[-1])
            a, b, c = int(data["a"]), int(data["b"]), int(data["c"])
            if a == 0:
                raise ValueError("a must be non-zero")
            return {"a": a, "b": b, "c": c}
        except Exception:
            return {}

    def generate_task(self, student_signal: Dict[str, Any]) -> TaskSpec:
        """Produce a new task using student performance signals."""
        if "prompt_override" in student_signal:
            task_id = student_signal.get("next_task_id", "task-0001")
            domain = student_signal.get("domain_override", "logic")
            prompt = str(student_signal["prompt_override"])
            verifier = None
            return TaskSpec(
                task_id=task_id,
                domain=domain,
                prompt=prompt,
                constraints=["show reasoning", "use tools if needed"],
                verifier=verifier,
                seed=student_signal.get("seed"),
            )

        task_id = student_signal.get("next_task_id", "task-0001")
        raw = self.model.generate(TEACHER_PROMPT, max_tokens=64, temperature=self.model_config.get("temperature", 0.7))
        params = self._parse_params(raw)

        a = params.get("a", int(student_signal.get("a", 2)))
        b = params.get("b", int(student_signal.get("b", 3)))
        c = params.get("c", int(student_signal.get("c", 11)))
        prompt = f"Solve for x: {a}x + {b} = {c}."
        answer = (c - b) / a
        verifier = VerifierSpec(kind="expected_number", spec={"answer": str(answer)})
        return TaskSpec(
            task_id=task_id,
            domain="math",
            prompt=prompt,
            constraints=["show reasoning", "use tools if needed"],
            verifier=verifier,
            seed=student_signal.get("seed"),
        )
