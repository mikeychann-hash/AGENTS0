import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from agent0.tools.sandbox import limit_resources


def run_shell(command: str, allowed_binaries: Optional[List[str]] = None, timeout: int = 15, workdir: str = ".") -> Dict[str, str]:
    """Run shell commands with an allowlist check."""
    if allowed_binaries:
        head = command.strip().split(" ", 1)[0]
        if head not in allowed_binaries:
            return {"status": "blocked", "stdout": "", "stderr": f"Command '{head}' not allowed"}

    cwd = Path(workdir).resolve()
    cwd.mkdir(parents=True, exist_ok=True)
    try:
        with limit_resources():
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=True,
                timeout=timeout,
                check=False,
                cwd=cwd,
            )
        return {"status": "ok", "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "stdout": "", "stderr": "shell timed out"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "stdout": "", "stderr": str(exc)}
