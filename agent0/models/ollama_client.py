from __future__ import annotations

from typing import List, Optional

from agent0.models.base import BaseModel


class OllamaModel(BaseModel):
    """HTTP client for Ollama server."""

    def __init__(self, model: str, host: str = "http://127.0.0.1:11434") -> None:
        import requests  # type: ignore

        self.model = model
        self.host = host.rstrip("/")
        self.session = requests.Session()

    def generate(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "top_p": top_p, "num_predict": max_tokens},
        }
        if stop:
            payload["stop"] = stop
        resp = self.session.post(f"{self.host}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        # Ollama streams line-by-line JSON; when using /generate without stream, we get the final object.
        data = resp.json()
        return data.get("response", "") or data.get("text", "")

    def generate_with_logprobs(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        max_tokens: int = 64,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> tuple[str, Optional[float]]:
        # Ollama does not expose logprobs; fall back to plain generate.
        return self.generate(prompt, stop=stop, max_tokens=max_tokens, temperature=temperature, top_p=top_p), None
