from __future__ import annotations

from typing import Dict

from agent0.tasks.schema import TaskSpec, VerifierSpec
import re

from agent0.tools import python_runner, test_runner


def verify(task: TaskSpec, candidate: str) -> Dict[str, str]:
    """Evaluate a candidate answer against the task's verifier spec."""
    if task.verifier is None:
        return {"status": "unknown", "detail": "no verifier"}

    kind = task.verifier.kind
    spec = task.verifier.spec

    if kind == "expected_number":
        expected_raw = spec.get("answer")
        expected_str = str(expected_raw)
        cand_str = str(candidate).strip()
        ok = False
        
        try:
            # Handle both integer and floating point comparisons
            expected_num = float(expected_raw)
            candidate_num = float(cand_str)
            
            # Use relative tolerance for floating point comparison
            if abs(expected_num) < 1e-10:  # Very small expected value
                ok = abs(candidate_num) < 1e-10
            else:
                relative_error = abs(candidate_num - expected_num) / abs(expected_num)
                ok = relative_error < 1e-6 or abs(candidate_num - expected_num) < 1e-10
                
        except (ValueError, TypeError, OverflowError):
            # Fall back to string comparison if numeric conversion fails
            ok = expected_str.strip().lower() == cand_str.lower()
        
        return {"status": "pass" if ok else "fail", "detail": f"expected {expected_str}, got {candidate}"}

    if kind == "python_assert":
        code = spec.get("code", "")
        # Append candidate if requested
        code_with_candidate = code.replace("{{candidate}}", str(candidate))
        result = python_runner.run_python(code_with_candidate)
        ok = result.get("status") == "ok" and not result.get("stderr")
        return {"status": "pass" if ok else "fail", "detail": result.get("stderr", result)}

    if kind == "unit_test":
        test_code = spec.get("test_code", "")
        result = test_runner.run_pytest(test_code)
        ok = result.get("status") == "ok" and "failed" not in result.get("stdout", "")
        return {"status": "pass" if ok else "fail", "detail": result.get("stdout", result)}

    if kind == "contains":
        substring = spec.get("text", "")
        ok = substring in str(candidate)
        return {"status": "pass" if ok else "fail", "detail": f"expected substring '{substring}'"}

    if kind == "regex":
        pattern = spec.get("pattern", "")
        ok = re.search(pattern, str(candidate)) is not None
        return {"status": "pass" if ok else "fail", "detail": f"regex match for '{pattern}'"}

    if kind == "python_predicate":
        code = spec.get("code", "")
        code_with_candidate = code.replace("{{candidate}}", str(candidate))
        result = python_runner.run_python(code_with_candidate)
        ok = result.get("status") == "ok" and not result.get("stderr")
        return {"status": "pass" if ok else "fail", "detail": result.get("stderr", result)}

    return {"status": "unknown", "detail": f"unsupported verifier kind: {kind}"}
