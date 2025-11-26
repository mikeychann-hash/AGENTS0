from __future__ import annotations

from typing import List, Optional


class FaissIndex:
    """Simple FAISS wrapper if available; falls back to in-memory list."""

    def __init__(self, dim: int):
        try:
            import faiss  # type: ignore
        except ImportError as exc:  # noqa: BLE001
            raise RuntimeError("faiss-cpu not installed") from exc
        self.faiss = faiss
        self.index = faiss.IndexFlatL2(dim)
        self.vectors: List[List[float]] = []

    def add(self, vec: List[float]) -> None:
        import numpy as np  # type: ignore

        self.index.add(np.array([vec], dtype="float32"))
        self.vectors.append(vec)

    def max_similarity(self, vec: List[float]) -> float:
        import numpy as np  # type: ignore

        if self.index.ntotal == 0:
            return 0.0
        D, _ = self.index.search(np.array([vec], dtype="float32"), 1)
        if D.size == 0:
            return 0.0
        # Convert L2 distance to cosine approximation when vectors are normalized.
        dist = float(D[0][0])
        return max(0.0, 1.0 - dist)
