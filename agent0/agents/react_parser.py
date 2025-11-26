from __future__ import annotations

import re
from typing import List, Tuple


def parse_react(output: str) -> Tuple[List[dict], str]:
    """Parse a simple ReAct-style transcript into tool_calls and final answer."""
    tool_calls: List[dict] = []
    answer = ""
    lines = output.splitlines()
    current_tool = None
    for line in lines:
        if line.lower().startswith("tool:"):
            current_tool = line.split(":", 1)[1].strip()
        elif line.lower().startswith("toolinput:") and current_tool:
            inp = line.split(":", 1)[1].strip()
            tool_calls.append({"tool": current_tool, "input": inp})
        elif line.lower().startswith("answer:"):
            answer = line.split(":", 1)[1].strip()
    return tool_calls, answer
