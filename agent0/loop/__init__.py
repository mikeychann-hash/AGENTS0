"""Core Agent0 evolution loop for a single round."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

from agent0.config import RunConfig, load_config
from agent0.curriculum import CurriculumAgent
from agent0.evaluator import Evaluator
from agent0.executor import ExecutorAgent
from agent0.llm_client import LocalLLMClient
from agent0.tasks import TaskAttempt


def run_round(run_config: RunConfig) -> List[TaskAttempt]:
    llm = LocalLLMClient(run_config.llm)
    curriculum = CurriculumAgent(llm)
    executor = ExecutorAgent(llm)
    evaluator = Evaluator()

    tasks = curriculum.generate_tasks(run_config, run_config.num_tasks)
    attempts: List[TaskAttempt] = []

    for task in tasks:
        result = executor.solve_task(task)
        evaluation = evaluator.evaluate(task, result)
        attempts.append(TaskAttempt(task=task, result=result, evaluation=evaluation))

    _save_attempts(run_config, attempts)
    return attempts


def _save_attempts(run_config: RunConfig, attempts: List[TaskAttempt]) -> None:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(run_config.logs_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{run_config.run_name}_{ts}.json"

    serializable = [attempt.model_dump() for attempt in attempts]
    out_file.write_text(json.dumps(serializable, indent=2), encoding="utf-8")


__all__ = ["run_round", "load_config"]
