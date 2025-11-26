from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ToolingConfig:
    enable_python: bool = True
    enable_shell: bool = True
    enable_math: bool = True
    enable_tests: bool = True
    timeout_seconds: int = 15
    workdir: str = "./sandbox"
    allowed_shell: Optional[List[str]] = None
    max_cpu_seconds: int = 5
    max_mem_mb: int = 512
