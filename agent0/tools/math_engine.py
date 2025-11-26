import sympy as sp
from typing import Dict, Optional


def solve_expression(expression: str) -> Dict[str, str]:
    """Attempt to simplify/evaluate a math expression safely."""
    try:
        sym_expr = sp.sympify(expression)
        simplified = sp.simplify(sym_expr)
        return {"status": "ok", "result": str(simplified)}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "result": "", "stderr": str(exc)}


def numerical_eval(expression: str, subs: Optional[dict] = None) -> Dict[str, str]:
    try:
        sym_expr = sp.sympify(expression)
        evaluated = sym_expr.evalf(subs=subs)
        return {"status": "ok", "result": str(evaluated)}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "result": "", "stderr": str(exc)}

