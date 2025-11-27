"""Task, result, and evaluation models for Agent0."""

from __future__ import annotations

from typing import Dict, List

from uuid import uuid4
from pydantic import BaseModel


class Task(BaseModel):
    task_id: str
    description: str
    domain: str = "generic"
    difficulty: float = 0.5
    metadata: Dict = {}


class TaskResult(BaseModel):
    task_id: str
    solution: str
    tool_calls: List[str] = []


class Evaluation(BaseModel):
    task_id: str
    score: float
    passed: bool
    feedback: str


class TaskAttempt(BaseModel):
    task: Task
    result: TaskResult


def new_task_id() -> str:
    """Generate a new task identifier."""
    return str(uuid4())
