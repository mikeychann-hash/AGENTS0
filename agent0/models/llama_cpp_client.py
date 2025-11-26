from __future__ import annotations

from typing import List, Optional

from agent0.models.base import BaseModel


class LlamaCppModel(BaseModel):
    """Lightweight wrapper for llama.cpp Python bindings."""

    def __init__(self, model_path: str, n_ctx: int = 4096, n_threads: int = 4) -> None:
        try:
            from llama_cpp import Llama  # type: ignore
        except ImportError as exc:  # noqa: BLE001
            raise RuntimeError("llama-cpp-python is not installed") from exc

        self.client = Llama(model_path=model_path, n_ctx=n_ctx, n_threads=n_threads, verbose=False)

    def generate(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        output = self.client(
            prompt,
            max_tokens=max_tokens,
            stop=stop,
            temperature=temperature,
            top_p=top_p,
        )
        return output["choices"][0]["text"]

    def generate_with_logprobs(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        max_tokens: int = 64,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> tuple[str, Optional[float]]:
        output = self.client(
            prompt,
            max_tokens=max_tokens,
            stop=stop,
            temperature=temperature,
            top_p=top_p,
            logprobs=5,
            logits_all=False,
        )
        text = output["choices"][0]["text"]
        avg_lp = None
        try:
            lps = output["choices"][0]["logprobs"]["token_logprobs"]
            if lps:
                avg_lp = sum(lp for lp in lps if lp is not None) / len(lps)
        except Exception:
            avg_lp = None
        return text, avg_lp
