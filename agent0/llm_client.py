"""Generic local LLM client supporting HTTP and CLI backends."""

from __future__ import annotations

import asyncio
import json
import shlex
from typing import Optional

import httpx

from agent0.config import LLMConfig


class LocalLLMClient:
    """Query a local model via HTTP or CLI using a shared interface."""

    def __init__(self, config: LLMConfig, timeout: float = 60.0) -> None:
        self.config = config
        self.timeout = timeout
        self.backend = (config.backend_type or "").lower()

    async def acompletion(self, system_prompt: str, user_prompt: str) -> str:
        """Asynchronously get a completion from the configured backend."""
        if self.backend == "http":
            return await self._http_completion(system_prompt, user_prompt)
        if self.backend == "cli":
            return await self._cli_completion(system_prompt, user_prompt)
        raise ValueError(f"Unsupported backend_type: {self.config.backend_type!r}")

    def completion(self, system_prompt: str, user_prompt: str) -> str:
        """Synchronous wrapper around acompletion."""
        return asyncio.run(self.acompletion(system_prompt, user_prompt))

    async def _http_completion(self, system_prompt: str, user_prompt: str) -> str:
        if not self.config.base_url:
            raise ValueError("HTTP backend requires base_url in LLMConfig")
        payload = {
            "model": self.config.model_name,
            "system": system_prompt,
            "prompt": user_prompt,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.config.base_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"HTTP request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON response from backend: {exc}") from exc

        for key in ("response", "text", "completion", "content"):
            if isinstance(data, dict) and key in data:
                return str(data[key])
        return str(data)

    async def _cli_completion(self, system_prompt: str, user_prompt: str) -> str:
        if not self.config.cli_command:
            raise ValueError("CLI backend requires cli_command in LLMConfig")

        prompt = f"System:\n{system_prompt}\n\nUser:\n{user_prompt}\n"
        cmd = self.config.cli_command

        # Prefer exec form for portability; fall back to shell if needed.
        try:
            args = shlex.split(cmd)
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(f"CLI command not found: {cmd}") from exc
        except Exception:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(prompt.encode("utf-8")), timeout=self.timeout)
        except asyncio.TimeoutError as exc:
            proc.kill()
            raise RuntimeError("CLI completion timed out") from exc

        if proc.returncode != 0:
            raise RuntimeError(f"CLI command failed (code {proc.returncode}): {stderr.decode('utf-8', 'ignore')}")

        return stdout.decode("utf-8", "ignore").strip()
