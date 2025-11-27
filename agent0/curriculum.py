"""Curriculum generator that produces small Python coding tasks."""

from __future__ import annotations

import json
from typing import List

from agent0.config import RunConfig
from agent0.llm_client import LocalLLMClient
from agent0.tasks import Task, new_task_id


SYSTEM_PROMPT = "You are a curriculum generator producing small, testable Python tasks."


def _fallback_tasks(num_tasks: int) -> List[Task]:
    seeds = [
        "Write a function that returns the factorial of n.",
        "Write a function that checks if a string is a palindrome.",
        "Write a function that computes the nth Fibonacci number iteratively.",
        "Write a function that finds the maximum element in a list.",
        "Write a function that counts word frequencies in a sentence.",
    ]
    tasks: List[Task] = []
    for i in range(num_tasks):
        desc = seeds[i % len(seeds)]
        tasks.append(Task(task_id=new_task_id(), description=desc, domain="code", difficulty=0.5))
    return tasks


class CurriculumAgent:
    def __init__(self, llm: LocalLLMClient):
        self.llm = llm

    def generate_tasks(self, run_config: RunConfig, num_tasks: int) -> List[Task]:
        user_prompt = (
            f"Generate {num_tasks} small Python coding tasks for run '{run_config.run_name}'. "
            "Return ONLY a JSON array of objects with 'description' fields."
        )

        try:
            raw = self.llm.completion(SYSTEM_PROMPT, user_prompt)
            data = json.loads(raw)
            if not isinstance(data, list):
                raise ValueError("LLM did not return a list")
            tasks: List[Task] = []
            for item in data:
                desc = ""
                if isinstance(item, dict):
                    desc = item.get("description") or item.get("task") or ""
                elif isinstance(item, str):
                    desc = item
                if desc:
                    tasks.append(Task(task_id=new_task_id(), description=desc, domain="code", difficulty=0.5))
            if tasks:
                return tasks[:num_tasks]
        except Exception:
            pass

        # Fallback if parsing fails or no tasks produced
        return _fallback_tasks(num_tasks)
