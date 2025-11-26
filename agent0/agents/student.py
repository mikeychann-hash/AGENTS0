from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from agent0.models.factory import create_model
from agent0.agents.prompts import STUDENT_REACT_PROMPT
from agent0.agents.prompts_logic import LOGIC_REACT_PROMPT
from agent0.agents.prompts_code import CODE_REACT_PROMPT
from agent0.agents.prompts_long import LONG_REACT_PROMPT
from agent0.agents.react_parser import parse_react
from agent0.tasks.schema import TaskSpec, Trajectory
from agent0.tools import math_engine, python_runner, shell_runner, test_runner
from agent0.tools.metrics import timed
from agent0.tools.plan_executor import execute_plan


class StudentAgent:
    """Attempts tasks using tool-augmented reasoning."""

    def __init__(self, model_config: Dict[str, Any], tool_config: Optional[Dict[str, Any]] = None) -> None:
        self.model_config = model_config
        self.model = create_model(model_config)
        self.tool_config = tool_config or {}
        self.last_llm_tools: List[dict] = []

    def _extract_number(self, text: str) -> Optional[str]:
        match = re.search(r"[-+]?\\d+(?:\\.\\d+)?", text)
        return match.group(0) if match else None

    def _llm_guess(self, task: TaskSpec) -> Optional[str]:
        if task.domain == "logic":
            prompt = LOGIC_REACT_PROMPT.format(problem=task.prompt)
        elif task.domain == "code":
            prompt = CODE_REACT_PROMPT.format(task=task.prompt)
        elif task.domain == "long":
            prompt = LONG_REACT_PROMPT.format(task=task.prompt)
        else:
            prompt = STUDENT_REACT_PROMPT.format(equation=task.prompt)
        raw = self.model.generate(
            prompt,
            max_tokens=128,
            temperature=self.model_config.get("temperature", 0.6),
            top_p=self.model_config.get("top_p", 0.9),
        )
        tool_calls, answer = parse_react(raw)
        if tool_calls:
            # Log parsed tool calls even though we don't execute them yet.
            self.last_llm_tools = tool_calls
        if answer:
            return self._extract_number(answer)
        return self._extract_number(raw or "")

    def solve(self, task: TaskSpec) -> Trajectory:
        """Minimal placeholder solver that demonstrates tool calls."""
        messages: List[Dict[str, Any]] = [{"role": "user", "content": task.prompt}]
        tool_calls = []
        result_text = ""
        metrics: Dict[str, float] = {}
        self.last_llm_tools = []

        # Step 1: ask the model directly.
        with timed("llm_reason", metrics):
            guess = self._llm_guess(task)
        candidate = guess

        # Step 2: symbolic attempt if no candidate.
        if candidate is None and self.last_llm_tools:
            plan_results = execute_plan(
                self.last_llm_tools,
                allowed_shell=self.tool_config.get("allowed_shell"),
                timeout=self.tool_config.get("timeout_seconds", 15),
                workdir=self.tool_config.get("workdir", "./sandbox"),
            )
            tool_calls.extend(plan_results)
            for res in plan_results:
                cand = res["result"].get("result") or res["result"].get("stdout", "")
                num = self._extract_number(str(cand))
                if num:
                    candidate = num
                    break

        if candidate is None:
            math_result = math_engine.solve_expression(task.prompt)
            tool_calls.append({"tool": "math_engine", "status": math_result.get("status"), "result": math_result})
            if math_result.get("status") == "ok":
                candidate = self._extract_number(str(math_result.get("result", "")))

        # Step 3: Python fallback.
        if candidate is None:
            py_code = f"import sympy as sp\nx = sp.symbols('x')\nexpr = sp.Eq({task.prompt.split(':')[-1].strip()})\nsol = sp.solve(expr, x)\nprint(sol[0])"
            with timed("python", metrics):
                py_result = python_runner.run_python(
                    py_code,
                    timeout=self.tool_config.get("timeout_seconds", 15),
                    workdir=self.tool_config.get("workdir", "./sandbox"),
                )
            tool_calls.append({"tool": "python", "status": py_result.get("status"), "result": py_result})
            candidate = self._extract_number(py_result.get("stdout", ""))

        result_text = candidate or ""

        reward_stub = {"total": 0.0}

        return Trajectory(
            task=task,
            messages=messages,
            tool_calls=tool_calls,
            result=result_text,
            success=False,
            reward=reward_stub,
            metrics=metrics,
        )
