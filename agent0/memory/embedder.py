from __future__ import annotations

from typing import List


class BaseEmbedder:
    def embed(self, text: str) -> List[float]:
        raise NotImplementedError


class SentenceTransformerEmbedder(BaseEmbedder):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # noqa: BLE001
            raise RuntimeError("sentence-transformers not installed") from exc
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> List[float]:
        vec = self.model.encode(text)
        return vec.tolist()


class DummyEmbedder(BaseEmbedder):
    """Fallback embedder; use only if transformer is unavailable."""

    def embed(self, text: str) -> List[float]:
        return [float((hash(text) % 1000) / 1000.0)]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def create_embedder(prefer_transformer: bool = True, model_name: str = "all-MiniLM-L6-v2") -> BaseEmbedder:
    if prefer_transformer:
        try:
            return SentenceTransformerEmbedder(model_name=model_name)
        except Exception:
            return DummyEmbedder()
    return DummyEmbedder()
