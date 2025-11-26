from __future__ import annotations

import subprocess
from typing import Optional, Dict


def call_cloud_cli(command: str, task: str, timeout: int = 120) -> Dict[str, str]:
    """
    Call a cloud CLI command by piping the task as stdin.
    Example command: "openai api chat.completions.create -m gpt-4o-mini"
    """
    try:
        proc = subprocess.run(
            command,
            input=task,
            text=True,
            capture_output=True,
            shell=True,
            timeout=timeout,
            check=False,
        )
        return {"status": "ok", "stdout": proc.stdout, "stderr": proc.stderr}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "stdout": "", "stderr": "cloud CLI timed out"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "stdout": "", "stderr": str(exc)}
