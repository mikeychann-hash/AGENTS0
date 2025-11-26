from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class SchedulerState:
    success_rate: float = 0.5
    step: int = 0
    a: int = 2
    b: int = 3
    c: int = 11
    domain: str = "math"
    domains: List[str] = None


class CurriculumScheduler:
    """Adjusts task parameters based on recent performance."""

    def __init__(self, target_success: float = 0.5) -> None:
        self.target = target_success
        self.state = SchedulerState(domains=["math", "logic", "code"])

    def update(self, success: bool) -> None:
        # Simple moving rate update.
        self.state.step += 1
        self.state.success_rate = (self.state.success_rate * 0.9) + (0.1 if success else 0.0)
        # Adjust difficulty: if too easy, increase coefficients; if too hard, decrease.
        if self.state.success_rate > self.target + 0.05:
            self.state.a = min(self.state.a + 1, 9)
            self.state.b = min(self.state.b + 1, 20)
            self.state.c = min(self.state.c + 1, 20)
        elif self.state.success_rate < self.target - 0.05:
            self.state.a = max(self.state.a - 1, 1)
            self.state.b = max(self.state.b - 1, -20)
            self.state.c = max(self.state.c - 1, -20)
        # Rotate domain every few steps for variety.
        if self.state.step % 5 == 0 and self.state.domains:
            idx = self.state.domains.index(self.state.domain) if self.state.domain in self.state.domains else 0
            self.state.domain = self.state.domains[(idx + 1) % len(self.state.domains)]

    def next_signal(self) -> Dict[str, object]:
        return {
            "a": self.state.a,
            "b": self.state.b,
            "c": self.state.c,
            "domain_override": self.state.domain,
        }
