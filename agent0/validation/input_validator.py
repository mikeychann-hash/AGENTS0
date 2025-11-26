from typing import List

from agent0.tasks.schema import TaskSpec


class InputValidator:
    """Validate tasks before execution in local mode."""

    MAX_PROMPT_LENGTH = 1000
    ALLOWED_DOMAINS = {"math", "logic", "code", "long"}

    def validate_task(self, task: TaskSpec) -> List[str]:
        errors: List[str] = []

        if not task.task_id:
            errors.append("Missing task_id")
        if task.domain not in self.ALLOWED_DOMAINS:
            errors.append(f"Invalid domain: {task.domain}")
        if not task.prompt:
            errors.append("Empty prompt")
        if len(task.prompt) > self.MAX_PROMPT_LENGTH:
            errors.append(f"Prompt too long: {len(task.prompt)} > {self.MAX_PROMPT_LENGTH}")

        suspicious_terms = ("exec(", "eval(", "__import__", "subprocess", "rm -rf", "format C:")
        lower_prompt = task.prompt.lower()
        for term in suspicious_terms:
            if term in lower_prompt:
                errors.append(f"Suspicious content in prompt: {term}")

        return errors
