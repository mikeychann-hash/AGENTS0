from __future__ import annotations

from typing import Any, Dict, Optional


class CloudRouter:
    """Router with simple cache, thresholds, and optional confidence fusion."""

    def __init__(self, local_threshold: float = 0.5, escalate_threshold: float = 0.3):
        self.local_threshold = local_threshold
        self.escalate_threshold = escalate_threshold
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_path: Optional[str] = None

    def decide(self, local_conf: float) -> str:
        """
        Returns:
            "local"   -> handle locally
            "cloud"   -> defer to cloud LLM
            "hybrid"  -> combine results (placeholder)
        """
        if local_conf >= self.local_threshold:
            return "local"
        if local_conf <= self.escalate_threshold:
            return "cloud"
        return "hybrid"

    def fuse_confidence(self, uncertainty: float, reward_total: float) -> float:
        """Combine uncertainty estimate and reward into a crude confidence score."""
        # uncertainty is centered around ~0.5 target; reward_total typically negative/positive small.
        return max(0.0, min(1.0, uncertainty + 0.5 + 0.1 * reward_total))

    def cache_key(self, task: str) -> str:
        return str(hash(task))

    def load_cache(self, path: str) -> None:
        self.cache_path = path
        p = Path(path)
        if p.exists():
            self.cache = json.loads(p.read_text(encoding="utf-8"))

    def save_cache(self) -> None:
        if not self.cache_path:
            return
        p = Path(self.cache_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.cache), encoding="utf-8")

    def get_cache(self, task: str) -> Optional[Dict[str, Any]]:
        return self.cache.get(self.cache_key(task))

    def set_cache(self, task: str, value: Dict[str, Any]) -> None:
        self.cache[self.cache_key(task)] = value
        self.save_cache()
