"""Executor agent that solves tasks by generating Python code."""

from __future__ import annotations

from agent0.llm_client import LocalLLMClient
from agent0.tasks import Task, TaskResult


SYSTEM_PROMPT = "You are an expert Python coder. Output ONLY executable Python code."


class ExecutorAgent:
    def __init__(self, llm: LocalLLMClient):
        self.llm = llm

    def solve_task(self, task: Task) -> TaskResult:
        user_prompt = f"Task: {task.description}"
        code = self.llm.completion(SYSTEM_PROMPT, user_prompt)
        return TaskResult(task_id=task.task_id, solution=code, tool_calls=[])
