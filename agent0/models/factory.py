from __future__ import annotations

from agent0.models.base import BaseModel
from agent0.models.llama_cpp_client import LlamaCppModel
from agent0.models.vllm_client import VLLMModel
from agent0.models.ollama_client import OllamaModel


class DummyModel(BaseModel):
    """Fallback model that echoes prompts; useful when no backend is configured."""

    def generate(self, prompt: str, stop=None, max_tokens: int = 256, temperature: float = 0.7, top_p: float = 0.9) -> str:  # type: ignore[override]
        return f"[dummy completion] {prompt[:64]}"


def create_model(config: dict) -> BaseModel:
    backend = config.get("backend", "dummy")
    if backend == "llama_cpp":
        return LlamaCppModel(
            model_path=config.get("model_path", ""),
            n_ctx=config.get("context_length", 4096),
            n_threads=config.get("num_threads", 4),
        )
    if backend == "vllm":
        return VLLMModel(endpoint=config.get("endpoint", "http://localhost:8000/generate"))
    if backend == "ollama":
        return OllamaModel(model=config.get("model", ""), host=config.get("host", "http://127.0.0.1:11434"))
    return DummyModel()
