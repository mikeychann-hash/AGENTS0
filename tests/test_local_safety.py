import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent0.safety.code_reviewer import LocalCodeReviewer
from agent0.validation.input_validator import InputValidator
from agent0.tasks.schema import TaskSpec
from agent0.tools import python_runner


def test_code_reviewer_blocks_dangerous():
    reviewer = LocalCodeReviewer()
    dangerous = "import os\nos.system('rm -rf /')"
    result = reviewer.review_python_code(dangerous)
    assert not result["safe"]
    assert result["issues"]


def test_code_reviewer_allows_safe():
    reviewer = LocalCodeReviewer()
    safe = "import math\nprint(math.sqrt(16))"
    result = reviewer.review_python_code(safe)
    assert result["safe"]
    assert not result["issues"]


def test_input_validator_catches_bad_task():
    validator = InputValidator()
    bad_task = TaskSpec(task_id="", domain="invalid", prompt="")
    errors = validator.validate_task(bad_task)
    assert errors


def test_python_runner_blocks_review(tmp_path):
    dangerous = "import os\nos.system('rm -rf /')"
    result = python_runner.run_python(dangerous, timeout=5, workdir=str(tmp_path))
    assert result["status"] == "blocked"
