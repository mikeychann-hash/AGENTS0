import logging
import subprocess
import tempfile
from typing import Dict, Optional

from pathlib import Path

from agent0.safety.code_reviewer import LocalCodeReviewer
from agent0.tools.sandbox import limit_resources

logger = logging.getLogger(__name__)
reviewer = LocalCodeReviewer()


def run_python(code: str, timeout: int = 15, workdir: str = ".") -> Dict[str, str]:
    """Execute Python in a temporary file with a timeout. Returns stdout/stderr."""
    review = reviewer.review_python_code(code)
    if not review["safe"]:
        logger.error("Code review blocked execution: %s", review["issues"])
        return {"status": "blocked", "stdout": "", "stderr": f"Blocked by code review: {review['issues']}"}
    if review["warnings"]:
        logger.warning("Code review warnings: %s", review["warnings"])

    base_dir = Path(workdir).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".py", dir=base_dir, delete=False) as tmp:
        tmp.write(code.encode("utf-8"))
        tmp_path = tmp.name

    try:
        with limit_resources():
            result = subprocess.run(
                ["python", tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        return {"status": "ok", "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "stdout": "", "stderr": "python timed out"}
    except Exception as exc:  # noqa: BLE001
        logger.error("Python execution error: %s", exc)
        return {"status": "error", "stdout": "", "stderr": str(exc)}
