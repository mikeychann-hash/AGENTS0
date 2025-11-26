from __future__ import annotations

from typing import List, Optional


class BaseModel:
    """Minimal interface for text generation."""

    def generate(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        raise NotImplementedError

    def generate_with_logprobs(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> tuple[str, Optional[float]]:
        """Optional: return text and average token logprob if backend supports it."""
        raise NotImplementedError
