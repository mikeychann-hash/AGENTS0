from __future__ import annotations

from typing import Any, Dict


class LocalRouter:
    """Routes tasks between local Agent0 and cloud LLMs based on confidence."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.enable = config.get("router", {}).get("enable", False)
        self.cloud_threshold = config.get("router", {}).get("cloud_confidence_threshold", 0.7)
        self.local_threshold = config.get("router", {}).get("local_confidence_threshold", 0.4)

    def should_use_local(self, confidence: float) -> bool:
        if not self.enable:
            return False
        return confidence >= self.local_threshold

    def should_escalate_cloud(self, confidence: float) -> bool:
        return confidence < self.cloud_threshold

    def route(self, confidence: float) -> str:
        if self.should_use_local(confidence):
            return "local"
        if self.should_escalate_cloud(confidence):
            return "cloud"
        return "local"
