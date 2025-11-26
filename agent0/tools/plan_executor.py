from __future__ import annotations

from typing import Dict, List, Optional

from agent0.tools import math_engine, python_runner, shell_runner


def execute_plan(
    plan: List[dict],
    allowed_shell: Optional[List[str]] = None,
    timeout: int = 15,
    workdir: str = ".",
    cpu_seconds: int = 5,
    mem_mb: int = 512,
) -> List[dict]:
    """Execute a parsed plan of tool calls."""
    results = []
    for step in plan:
        tool = step.get("tool")
        inp = step.get("input", "")
        if tool == "math_engine":
            res = math_engine.solve_expression(inp)
        elif tool == "python":
            res = python_runner.run_python(inp, timeout=timeout, workdir=workdir)
        elif tool == "shell":
            res = shell_runner.run_shell(inp, allowed_binaries=allowed_shell, timeout=timeout, workdir=workdir)
        else:
            res = {"status": "unknown_tool", "stderr": tool}
        results.append({"tool": tool, "input": inp, "result": res})
    return results
