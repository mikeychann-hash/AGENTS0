from __future__ import annotations

import logging
from typing import List, Optional

from agent0.models.base import BaseModel

logger = logging.getLogger(__name__)


class OllamaConnectionError(Exception):
    """Raised when Ollama server is not available."""
    pass


class OllamaModel(BaseModel):
    """HTTP client for Ollama server."""

    def __init__(self, model: str, host: str = "http://127.0.0.1:11434") -> None:
        import requests  # type: ignore

        self.model = model
        self.host = host.rstrip("/")
        self.session = requests.Session()
        self._connected = False

    def check_connection(self) -> bool:
        """Check if Ollama server is available and model exists."""
        try:
            response = self.session.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                # Check if our model (or base name) is available
                if any(self.model in name or name in self.model for name in model_names):
                    self._connected = True
                    logger.info(f"Ollama connected: model '{self.model}' available")
                    return True
                else:
                    logger.warning(f"Ollama connected but model '{self.model}' not found. Available: {model_names}")
                    return False
            return False
        except Exception as e:
            logger.error(f"Ollama connection check failed: {e}")
            self._connected = False
            return False

    @property
    def is_connected(self) -> bool:
        """Return connection status."""
        return self._connected

    def generate(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        import requests

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "top_p": top_p, "num_predict": max_tokens},
        }
        if stop:
            payload["stop"] = stop

        try:
            resp = self.session.post(f"{self.host}/api/generate", json=payload, timeout=120)
            resp.raise_for_status()
            self._connected = True
            # Ollama streams line-by-line JSON; when using /generate without stream, we get the final object.
            data = resp.json()
            return data.get("response", "") or data.get("text", "")
        except requests.exceptions.ConnectionError as e:
            self._connected = False
            logger.error(f"Ollama connection error: {e}")
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self.host}. Is Ollama running?") from e
        except requests.exceptions.Timeout as e:
            logger.error(f"Ollama request timed out: {e}")
            raise OllamaConnectionError(f"Ollama request timed out after 120s") from e
        except requests.exceptions.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e}")
            if "model" in str(e).lower():
                raise OllamaConnectionError(f"Model '{self.model}' not found. Run: ollama pull {self.model}") from e
            raise

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
