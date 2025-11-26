import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional


def run_pytest(test_code: str, timeout: int = 15) -> Dict[str, str]:
    """Run a pytest snippet in isolation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_generated.py"
        test_file.write_text(test_code, encoding="utf-8")
        try:
            result = subprocess.run(
                ["pytest", str(test_file)],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return {"status": "ok", "stdout": result.stdout, "stderr": result.stderr}
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "stdout": "", "stderr": "pytest timed out"}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "stdout": "", "stderr": str(exc)}

