import ast
import re
import builtins
from typing import Dict, List, Set


class LocalCodeReviewer:
    """Enhanced code reviewer for local execution safety with comprehensive checks."""

    # Expanded dangerous imports for better security
    DANGEROUS_IMPORTS: Set[str] = {
        "os", "subprocess", "sys", "shutil", "multiprocessing", "threading",
        "socket", "urllib", "http", "ftplib", "smtplib", "sqlite3", "pickle",
        "ctypes", "mmap", "signal", "gc", "importlib", "pkgutil", "site"
    }
    
    # Dangerous builtin functions
    DANGEROUS_BUILTINS: Set[str] = {
        "eval", "exec", "compile", "__import__", "open", "input", "raw_input"
    }
    
    # Dangerous patterns for file operations and system commands
    DANGEROUS_PATTERNS: List[str] = [
        r"rm\s+-rf?",  # rm -rf variations
        r"del\s+[A-Za-z0-9]",  # del command
        r"format\s+[A-Z]:",  # format drive
        r"\.\.[/\\]",  # Directory traversal
        r"registry",  # Windows registry
        r"\bopen\s*\(",  # File operations
        r"\bwrite\s*\(",  # File write operations
        r"\bread\s*\(",  # File read operations
        r"\bdelete\s*\(",  # File deletion
        r"\bremove\s*\(",  # File removal
        r"\bsystem\s*\(",  # System command execution
        r"\bpopen\s*\(",  # Process execution
        r"\bspawn\s*\(",  # Process spawning
        r"\bfork\s*\(",  # Process forking
        r"\bkill\s*\(",  # Process termination
        r"\bexit\s*\(",  # Program termination
        r"\bquit\s*\(",  # Program termination
    ]
    
    # Safe builtin functions that are allowed
    SAFE_BUILTINS: Set[str] = {
        "abs", "all", "any", "bin", "bool", "bytearray", "bytes", "chr", 
        "complex", "dict", "divmod", "enumerate", "filter", "float", "format",
        "frozenset", "hasattr", "hash", "hex", "int", "isinstance", "issubclass",
        "iter", "len", "list", "map", "max", "memoryview", "min", "next", "object",
        "oct", "ord", "pow", "print", "range", "repr", "reversed", "round", "set",
        "slice", "sorted", "str", "sum", "tuple", "type", "vars", "zip", "help"
    }

    def review_python_code(self, code: str) -> Dict[str, object]:
        """Enhanced code review with comprehensive safety checks."""
        issues: List[str] = []
        warnings: List[str] = []

        # Basic validation
        if not code or not isinstance(code, str):
            return {"safe": False, "issues": ["Invalid code input"], "warnings": warnings, "code": code}

        # Check code length to prevent DoS
        if len(code) > 10000:  # 10KB limit
            issues.append("Code too long (max 10KB)")
            return {"safe": False, "issues": issues, "warnings": warnings, "code": code}

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return {"safe": False, "issues": [f"Syntax error: {exc}"], "warnings": warnings, "code": code}
        except Exception as exc:
            return {"safe": False, "issues": [f"Parse error: {exc}"], "warnings": warnings, "code": code}

        # AST-based security analysis
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_module = alias.name.split(".")[0]
                    if root_module in self.DANGEROUS_IMPORTS:
                        issues.append(f"Dangerous import: {alias.name}")
                    
            # Check from imports
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    root_module = node.module.split(".")[0]
                    if root_module in self.DANGEROUS_IMPORTS:
                        issues.append(f"Dangerous import from: {node.module}")
                        
            # Check function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in self.DANGEROUS_BUILTINS:
                        issues.append(f"Dangerous builtin: {func_name}")
                    elif func_name not in self.SAFE_BUILTINS and hasattr(builtins, func_name):
                        warnings.append(f"Potentially unsafe builtin: {func_name}")
                        
                # Check for getattr/hasattr with dangerous attributes
                if isinstance(node.func, ast.Name) and node.func.id in ["getattr", "hasattr"]:
                    if len(node.args) >= 2 and isinstance(node.args[1], ast.Str):
                        attr_name = node.args[1].s
                        if attr_name.startswith("_") or "__" in attr_name:
                            issues.append(f"Dangerous attribute access: {attr_name}")

            # Check for dangerous operations
            if isinstance(node, ast.Delete):
                warnings.append("Delete operations detected")
                
            # Check for exec/eval strings (Python 3.x compatibility)
            if hasattr(node, 'func') and isinstance(node.func, ast.Name):
                if node.func.id in ['exec', 'eval']:
                    issues.append("Direct exec/eval usage detected")

        # Pattern-based detection
        code_normalized = code.lower()
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code_normalized, re.IGNORECASE):
                issues.append(f"Suspicious pattern detected: {pattern}")

        # Additional heuristics
        if re.search(r'__\w+__', code):
            warnings.append("Magic methods detected")
            
        # Check for dynamic code generation
        if any(keyword in code_normalized for keyword in ["compile", "code", "bytecode"]):
            warnings.append("Dynamic code generation detected")

        # Check for network operations
        if any(keyword in code_normalized for keyword in ["socket", "http", "url", "request"]):
            warnings.append("Network operations detected")

        return {
            "safe": len(issues) == 0, 
            "issues": issues, 
            "warnings": warnings, 
            "code": code,
            "score": max(0, 100 - len(issues) * 20 - len(warnings) * 5)  # Security score
        }
