from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

from agent0.tasks.schema import Trajectory


@dataclass
class RewardWeights:
    weight_uncertainty: float = 0.5
    weight_tool_use: float = 0.3
    weight_novelty: float = 0.2
    target_success_rate: float = 0.5
    repetition_similarity_threshold: float = 0.9


class RewardCalculator:
    """Computes reward components for a trajectory."""

    def __init__(self, weights: RewardWeights) -> None:
        self.weights = weights
        self.recent_task_signatures: List[str] = []
        self.recent_embeddings: List[List[float]] = []

    def _uncertainty_reward(self, success_prob: float) -> float:
        # Peak reward near the target_success_rate; penalize over/under confidence.
        return -abs(success_prob - self.weights.target_success_rate)

    def _tool_use_reward(self, tool_calls: List[dict]) -> float:
        if not tool_calls:
            return -0.2
        meaningful = [t for t in tool_calls if t.get("status") == "ok"]
        return min(len(meaningful) * 0.1, 1.0)

    def _novelty_penalty(self, signature: str) -> float:
        if signature in self.recent_task_signatures:
            return -1.0
        self.recent_task_signatures.append(signature)
        # Keep a short window to avoid unbounded growth.
        self.recent_task_signatures = self.recent_task_signatures[-100:]
        return 0.0

    def compute(
        self,
        trajectory: Trajectory,
        success_prob: float,
        novelty_sig: str,
        similarity: Optional[float] = None,
    ) -> Dict[str, float]:
        r_unc = self._uncertainty_reward(success_prob)
        r_tool = self._tool_use_reward(trajectory.tool_calls)
        r_nov = self._novelty_penalty(novelty_sig)
        if similarity is not None and similarity > self.weights.repetition_similarity_threshold:
            r_nov -= 0.5
        r_correct = 1.0 if trajectory.success else -0.5

        total = (
            self.weights.weight_uncertainty * r_unc
            + self.weights.weight_tool_use * r_tool
            + self.weights.weight_novelty * r_nov
            + 0.3 * r_correct
        )

        return {
            "uncertainty": r_unc,
            "tool_use": r_tool,
            "novelty": r_nov,
            "correctness": r_correct,
            "total": total,
        }
