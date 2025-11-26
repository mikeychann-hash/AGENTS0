import ast
import re
from typing import Dict, List


class LocalCodeReviewer:
    """Lightweight code reviewer for local execution safety."""

    DANGEROUS_IMPORTS = {"os", "subprocess", "sys", "shutil"}
    DANGEROUS_BUILTINS = {"eval", "exec", "compile", "__import__"}
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf",
        r"del\s+\/",
        r"format\s+[A-Z]:",
        r"\.\./",
        r"registry",
    ]

    def review_python_code(self, code: str) -> Dict[str, object]:
        """Return review result with issues/warnings."""
        issues: List[str] = []
        warnings: List[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return {"safe": False, "issues": [f"Syntax error: {exc}"], "warnings": warnings, "code": code}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in self.DANGEROUS_IMPORTS:
                        issues.append(f"Dangerous import: {alias.name}")
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in self.DANGEROUS_IMPORTS:
                    issues.append(f"Dangerous import from: {node.module}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in self.DANGEROUS_BUILTINS:
                    issues.append(f"Dangerous builtin: {node.func.id}")

        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code, flags=re.IGNORECASE):
                warnings.append(f"Suspicious pattern: {pattern}")

        if "open(" in code:
            warnings.append("File I/O detected")

        return {"safe": len(issues) == 0, "issues": issues, "warnings": warnings, "code": code}
