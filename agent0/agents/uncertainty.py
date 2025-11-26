from __future__ import annotations

import re
from typing import Any, Dict

from agent0.models.factory import create_model


class UncertaintyEstimator:
    """Estimates success probability via agreement-based sampling and self-critique prompt."""

    def __init__(self, model_config: Dict[str, Any]) -> None:
        self.model = create_model(model_config)
        self.model_config = model_config
        self.samples = model_config.get("uncertainty_samples", 3)

    def _build_prompt(self, task_text: str, answer: str) -> str:
        return (
            "You are an evaluator. Given a problem and a proposed answer, estimate the probability"
            " the answer is correct. Respond with a number between 0 and 1.\n"
            f"Problem: {task_text}\n"
            f"Proposed answer: {answer}\n"
            "Probability:"
        )

    def _extract_prob(self, text: str) -> float:
        match = re.search(r"0(?:\.\d+)?|1(?:\.0+)?", text)
        if not match:
            return 0.5
        try:
            val = float(match.group(0))
            return max(0.0, min(1.0, val))
        except Exception:
            return 0.5

    def estimate(self, task_text: str, answer: str) -> float:
        # If backend supports logprobs, use them as confidence proxy.
        try:
            text, avg_lp = self.model.generate_with_logprobs(
                f"{task_text}\nAnswer: {answer}",
                max_tokens=1,
                temperature=0.0,
                top_p=1.0,
            )
            if avg_lp is not None:
                # Convert average logprob to pseudo-confidence in [0,1].
                import math

                conf = math.exp(avg_lp)
                return max(0.0, min(1.0, conf))
        except Exception:
            pass

        # Fallback: agreement-based sampling via self-critique prompt.
        probs = []
        for _ in range(max(1, self.samples)):
            prompt = self._build_prompt(task_text, answer)
            raw = self.model.generate(
                prompt,
                max_tokens=16,
                temperature=self.model_config.get("temperature", 0.6),
                top_p=self.model_config.get("top_p", 0.9),
            )
            probs.append(self._extract_prob(raw or ""))
        return sum(probs) / len(probs)
