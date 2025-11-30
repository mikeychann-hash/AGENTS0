"""Basic configuration models and loader for Agent0 local runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field


class LLMConfig(BaseModel):
    """Model configuration for an LLM backend."""

    backend_type: str
    model_name: str
    base_url: Optional[str] = None
    cli_command: Optional[str] = None
    api_key_env: Optional[str] = None


class RunConfig(BaseModel):
    """Top-level run configuration."""

    model_config = ConfigDict(populate_by_name=True)

    run_name: str = "default"
    num_tasks: int = 1
    max_attempts: int = Field(1, alias="max_attempts_per_task")
    llm: LLMConfig
    logs_dir: str = "runs/logs"


def _is_run_config_like(data: Any) -> bool:
    """Check if the parsed YAML data matches the RunConfig schema."""
    if not isinstance(data, dict):
        return False
    return "llm" in data


def load_config(path: str | Path) -> Union[RunConfig, Dict[str, Any]]:
    """Load a YAML configuration file, returning either a RunConfig or the raw dict."""
    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if _is_run_config_like(data):
        return RunConfig.model_validate(data)
    return data
