"""
Agent0 Evolution Loop:
Generate → Solve → Evaluate → Log
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

from agent0.config import RunConfig
from agent0.llm_client import LocalLLMClient
from agent0.curriculum import CurriculumAgent
from agent0.executor import ExecutorAgent
from agent0.evaluator import Evaluator
from agent0.tasks import TaskAttempt


def run_round(run_config: RunConfig) -> List[TaskAttempt]:
    """
    Run a single Agent0 evolution round.

    Steps:
    1. Initialize LLM + agent components
    2. CurriculumAgent generates tasks
    3. ExecutorAgent solves tasks
    4. Evaluator scores results
    5. Save logs
    6. Return List[TaskAttempt]
    """
    # 1. Initialize LLM + agents
    llm = LocalLLMClient(run_config.llm)
    curriculum = CurriculumAgent(llm)
    executor = ExecutorAgent(llm)
    evaluator = Evaluator()

    attempts: List[TaskAttempt] = []

    # 2. Generate tasks
    tasks = curriculum.generate_tasks(run_config, run_config.num_tasks)

    # 3. Process each task
    for task in tasks:
        result = executor.solve_task(task)
        evaluation = evaluator.evaluate(task, result)
        attempts.append(TaskAttempt(task=task, result=result, evaluation=evaluation))

    # 4. Save logs
    log_path = _save_round_log(run_config, attempts)

    print(f"[Agent0] Completed round: {run_config.run_name}")
    print(f"[Agent0] Tasks solved: {len(attempts)}")
    print(f"[Agent0] Log saved to: {log_path}")

    return attempts


def _save_round_log(run_config: RunConfig, attempts: List[TaskAttempt]) -> Path:
    """
    Save task attempts to a timestamped JSON file inside runs/logs/.
    """
    logs_dir = Path(run_config.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{run_config.run_name}_{timestamp}.json"
    log_path = logs_dir / filename

    # Convert Pydantic TaskAttempt → dict for JSON serialization
    data = [a.model_dump() for a in attempts]

    log_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return log_path
