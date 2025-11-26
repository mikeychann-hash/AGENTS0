from __future__ import annotations

from typing import List, Optional

from agent0.models.base import BaseModel


class VLLMModel(BaseModel):
    """Wrapper for a vLLM HTTP server."""

    def __init__(self, endpoint: str) -> None:
        import requests  # type: ignore

        self.endpoint = endpoint
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
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        if stop:
            payload["stop"] = stop
        resp = self.session.post(self.endpoint, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["text"] if "text" in data else data["choices"][0]["text"]
