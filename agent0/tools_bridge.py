"""Foundational tool bridge for Agent0 (Python, shell, files)."""

from __future__ import annotations

import contextlib
import io
import subprocess
from pathlib import Path
from typing import Optional


def run_python_snippet(code: str) -> str:
    """
    Execute a small Python snippet in a restricted environment.

    Captures stdout/stderr and returns combined output. Exceptions are included in the output.
    This is a simple sandbox and should be tightened before running untrusted code.
    """
    stdout = io.StringIO()
    stderr = io.StringIO()
    safe_builtins = {
        "print": print,
        "len": len,
        "range": range,
        "min": min,
        "max": max,
        "sum": sum,
    }
    local_env = {}
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exec(code, {"__builtins__": safe_builtins}, local_env)
    except Exception as exc:  # noqa: BLE001
        stderr.write(f"Exception: {exc}\n")
    out = stdout.getvalue()
    err = stderr.getvalue()
    return (out + err).strip()


def run_shell_command(cmd: str, timeout: int = 60) -> tuple[str, int]:
    """
    Run a shell command with a timeout.

    Returns (combined stdout+stderr, returncode).
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Error: command timed out", 124
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}", 1
    combined = (result.stdout or "") + (result.stderr or "")
    return combined, result.returncode


def read_text_file(path: str, max_bytes: int = 100_000) -> str:
    """Read a text file up to max_bytes."""
    p = Path(path)
    data = p.read_bytes()[:max_bytes]
    return data.decode(errors="ignore")


def write_text_file(path: str, content: str) -> None:
    """Write text content to a file, creating parent dirs as needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


# TODO: integrate full claude_tools.py adapter once available.
# TODO: add Node.js / Minecraft API tool shims.
# TODO: add MCP tool routing for multi-backend tool orchestration.
