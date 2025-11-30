import logging
import subprocess
import tempfile
import os
import signal
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
    tmp_path = None
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix=".py", dir=base_dir, delete=False, encoding='utf-8') as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        with limit_resources():
            # Use creationflags to prevent window creation on Windows
            creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            
            result = subprocess.run(
                ["python", tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                creationflags=creationflags,
                cwd=str(base_dir)
            )
        
        # Clean up temporary file immediately after execution
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except OSError as cleanup_error:
            logger.warning(f"Failed to cleanup temporary file {tmp_path}: {cleanup_error}")
            
        return {"status": "ok", "stdout": result.stdout, "stderr": result.stderr}
        
    except subprocess.TimeoutExpired:
        # Kill the process and its children if timeout occurs
        try:
            if 'result' in locals() and result.pid:
                os.kill(result.pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass  # Process already terminated
        
        return {"status": "timeout", "stdout": "", "stderr": "python timed out"}
        
    except (subprocess.SubprocessError, OSError, FileNotFoundError) as exec_error:
        logger.error("Python execution error: %s", exec_error)
        return {"status": "error", "stdout": "", "stderr": f"Execution error: {exec_error}"}
        
    except Exception as unexpected_error:
        logger.error("Unexpected error during Python execution: %s", unexpected_error)
        return {"status": "error", "stdout": "", "stderr": f"Unexpected error: {unexpected_error}"}
        
    finally:
        # Ensure cleanup happens even if an error occurs
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError as final_cleanup_error:
                logger.warning(f"Failed to cleanup temporary file in finally block: {final_cleanup_error}")
