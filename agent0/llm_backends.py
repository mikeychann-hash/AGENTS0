#!/usr/bin/env python3
"""
External LLM Backend Integration for Agent0.

Allows Agent0 to use various LLM providers as backends:
- Claude CLI (claude)
- OpenAI CLI (openai)
- Gemini CLI (gemini)
- Ollama (ollama)
- Any custom CLI command

This enables Agent0 to leverage multiple AI models for:
- Fallback when primary model fails
- Ensemble reasoning
- Model comparison
- Cost optimization

Usage:
    from agent0.llm_backends import LLMBackend, ClaudeCLI, OpenAICLI

    # Use Claude CLI
    claude = ClaudeCLI()
    response = claude.generate("Solve: 2x + 5 = 15")

    # Use OpenAI CLI
    openai = OpenAICLI(model="gpt-4o")
    response = openai.generate("What is the capital of France?")

    # Use any CLI
    custom = CustomCLI(command="my-llm-cli --model local")
    response = custom.generate("Hello!")
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from an LLM backend."""
    content: str
    model: str
    backend: str
    latency_ms: float
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LLMBackend(ABC):
    """Abstract base class for LLM backends."""

    def __init__(self, timeout: int = 120):
        self.timeout = timeout
        self.name = "base"

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is available."""
        pass

    def _run_command(self, command: List[str], input_text: str = None) -> tuple[str, str, int]:
        """Run a CLI command and return stdout, stderr, returncode."""
        try:
            result = subprocess.run(
                command,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", -1
        except Exception as e:
            return "", str(e), -1


class ClaudeCLI(LLMBackend):
    """
    Claude CLI backend using the official Claude CLI.

    Requires: npm install -g @anthropic-ai/claude-cli
    Or: pip install claude-cli
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        timeout: int = 120,
        max_tokens: int = 1024,
    ):
        super().__init__(timeout)
        self.name = "claude-cli"
        self.model = model
        self.max_tokens = max_tokens
        self._cli_path = self._find_cli()

    def _find_cli(self) -> Optional[str]:
        """Find the Claude CLI executable."""
        # Try common names
        for name in ["claude", "claude-cli"]:
            path = shutil.which(name)
            if path:
                return path
        return None

    def is_available(self) -> bool:
        """Check if Claude CLI is available."""
        if not self._cli_path:
            return False

        try:
            result = subprocess.run(
                [self._cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate using Claude CLI."""
        if not self._cli_path:
            return LLMResponse(
                content="",
                model=self.model,
                backend=self.name,
                latency_ms=0,
                success=False,
                error="Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-cli"
            )

        start = time.time()

        # Build command
        command = [
            self._cli_path,
            "--model", self.model,
            "--max-tokens", str(kwargs.get("max_tokens", self.max_tokens)),
            "--print",  # Print response only
            prompt
        ]

        stdout, stderr, returncode = self._run_command(command)
        latency = (time.time() - start) * 1000

        if returncode == 0:
            return LLMResponse(
                content=stdout.strip(),
                model=self.model,
                backend=self.name,
                latency_ms=latency,
                success=True
            )
        else:
            return LLMResponse(
                content="",
                model=self.model,
                backend=self.name,
                latency_ms=latency,
                success=False,
                error=stderr or f"Command failed with code {returncode}"
            )


class OpenAICLI(LLMBackend):
    """
    OpenAI CLI backend.

    Requires: pip install openai
    And: OPENAI_API_KEY environment variable
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        timeout: int = 120,
        max_tokens: int = 1024,
    ):
        super().__init__(timeout)
        self.name = "openai-cli"
        self.model = model
        self.max_tokens = max_tokens

    def is_available(self) -> bool:
        """Check if OpenAI CLI is available."""
        if not os.environ.get("OPENAI_API_KEY"):
            return False

        try:
            import openai
            return True
        except ImportError:
            return False

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate using OpenAI API."""
        if not os.environ.get("OPENAI_API_KEY"):
            return LLMResponse(
                content="",
                model=self.model,
                backend=self.name,
                latency_ms=0,
                success=False,
                error="OPENAI_API_KEY not set"
            )

        try:
            import openai
        except ImportError:
            return LLMResponse(
                content="",
                model=self.model,
                backend=self.name,
                latency_ms=0,
                success=False,
                error="openai package not installed. Run: pip install openai"
            )

        start = time.time()

        try:
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
            )
            content = response.choices[0].message.content
            latency = (time.time() - start) * 1000

            return LLMResponse(
                content=content,
                model=self.model,
                backend=self.name,
                latency_ms=latency,
                success=True,
                metadata={"usage": dict(response.usage) if response.usage else {}}
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return LLMResponse(
                content="",
                model=self.model,
                backend=self.name,
                latency_ms=latency,
                success=False,
                error=str(e)
            )


class GeminiCLI(LLMBackend):
    """
    Google Gemini CLI backend.

    Requires: pip install google-generativeai
    And: GOOGLE_API_KEY environment variable
    """

    def __init__(
        self,
        model: str = "gemini-1.5-flash",
        timeout: int = 120,
        max_tokens: int = 1024,
    ):
        super().__init__(timeout)
        self.name = "gemini-cli"
        self.model = model
        self.max_tokens = max_tokens

    def is_available(self) -> bool:
        """Check if Gemini is available."""
        if not os.environ.get("GOOGLE_API_KEY"):
            return False

        try:
            import google.generativeai
            return True
        except ImportError:
            return False

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate using Gemini API."""
        if not os.environ.get("GOOGLE_API_KEY"):
            return LLMResponse(
                content="",
                model=self.model,
                backend=self.name,
                latency_ms=0,
                success=False,
                error="GOOGLE_API_KEY not set"
            )

        try:
            import google.generativeai as genai
        except ImportError:
            return LLMResponse(
                content="",
                model=self.model,
                backend=self.name,
                latency_ms=0,
                success=False,
                error="google-generativeai not installed. Run: pip install google-generativeai"
            )

        start = time.time()

        try:
            genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            content = response.text
            latency = (time.time() - start) * 1000

            return LLMResponse(
                content=content,
                model=self.model,
                backend=self.name,
                latency_ms=latency,
                success=True
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return LLMResponse(
                content="",
                model=self.model,
                backend=self.name,
                latency_ms=latency,
                success=False,
                error=str(e)
            )


class OllamaCLI(LLMBackend):
    """
    Ollama CLI backend using the ollama command.

    Requires: ollama installed and running
    """

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        host: str = "http://127.0.0.1:11434",
        timeout: int = 120,
    ):
        super().__init__(timeout)
        self.name = "ollama"
        self.model = model
        self.host = host

    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            import requests
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate using Ollama API."""
        try:
            import requests
        except ImportError:
            return LLMResponse(
                content="",
                model=self.model,
                backend=self.name,
                latency_ms=0,
                success=False,
                error="requests not installed"
            )

        start = time.time()

        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                content = data.get("response", "")
                latency = (time.time() - start) * 1000

                return LLMResponse(
                    content=content,
                    model=self.model,
                    backend=self.name,
                    latency_ms=latency,
                    success=True,
                    metadata={
                        "eval_count": data.get("eval_count", 0),
                        "eval_duration": data.get("eval_duration", 0),
                    }
                )
            else:
                latency = (time.time() - start) * 1000
                return LLMResponse(
                    content="",
                    model=self.model,
                    backend=self.name,
                    latency_ms=latency,
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text}"
                )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return LLMResponse(
                content="",
                model=self.model,
                backend=self.name,
                latency_ms=latency,
                success=False,
                error=str(e)
            )


class CustomCLI(LLMBackend):
    """
    Custom CLI backend for any command-line LLM tool.

    Usage:
        # Simple command (prompt as argument)
        custom = CustomCLI(command="my-llm")  # Runs: my-llm "prompt"

        # Command with stdin input
        custom = CustomCLI(command="my-llm --stdin", use_stdin=True)

        # With custom flags
        custom = CustomCLI(command="llm chat -m model-name")
    """

    def __init__(
        self,
        command: str,
        use_stdin: bool = False,
        timeout: int = 120,
    ):
        super().__init__(timeout)
        self.name = "custom-cli"
        self.command = command
        self.use_stdin = use_stdin

    def is_available(self) -> bool:
        """Check if the command exists."""
        cmd = self.command.split()[0]
        return shutil.which(cmd) is not None

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate using custom CLI."""
        start = time.time()

        try:
            if self.use_stdin:
                # Pass prompt via stdin
                command = self.command.split()
                result = subprocess.run(
                    command,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
            else:
                # Pass prompt as argument
                command = f'{self.command} "{prompt}"'
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )

            latency = (time.time() - start) * 1000

            if result.returncode == 0:
                return LLMResponse(
                    content=result.stdout.strip(),
                    model="custom",
                    backend=self.name,
                    latency_ms=latency,
                    success=True
                )
            else:
                return LLMResponse(
                    content="",
                    model="custom",
                    backend=self.name,
                    latency_ms=latency,
                    success=False,
                    error=result.stderr or f"Exit code: {result.returncode}"
                )
        except subprocess.TimeoutExpired:
            latency = (time.time() - start) * 1000
            return LLMResponse(
                content="",
                model="custom",
                backend=self.name,
                latency_ms=latency,
                success=False,
                error="Command timed out"
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return LLMResponse(
                content="",
                model="custom",
                backend=self.name,
                latency_ms=latency,
                success=False,
                error=str(e)
            )


class LLMRouter:
    """
    Route requests to multiple LLM backends with fallback support.

    Features:
    - Primary/fallback routing
    - Load balancing
    - Automatic failover
    - Response caching (optional)
    """

    def __init__(self, backends: List[LLMBackend] = None):
        self.backends = backends or []
        self._cache: Dict[str, LLMResponse] = {}

    def add_backend(self, backend: LLMBackend) -> None:
        """Add a backend to the router."""
        self.backends.append(backend)

    def get_available_backends(self) -> List[LLMBackend]:
        """Get list of available backends."""
        return [b for b in self.backends if b.is_available()]

    def generate(
        self,
        prompt: str,
        use_cache: bool = False,
        fallback: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        Generate using available backends.

        Args:
            prompt: The prompt to send
            use_cache: Cache and reuse responses
            fallback: Try next backend if current fails
            **kwargs: Additional arguments for the backend

        Returns:
            LLMResponse from the first successful backend
        """
        # Check cache
        if use_cache and prompt in self._cache:
            cached = self._cache[prompt]
            cached.metadata["cached"] = True
            return cached

        # Try each backend
        available = self.get_available_backends()
        if not available:
            return LLMResponse(
                content="",
                model="none",
                backend="router",
                latency_ms=0,
                success=False,
                error="No backends available"
            )

        errors = []
        for backend in available:
            response = backend.generate(prompt, **kwargs)

            if response.success:
                if use_cache:
                    self._cache[prompt] = response
                return response
            else:
                errors.append(f"{backend.name}: {response.error}")

                if not fallback:
                    break

        # All backends failed
        return LLMResponse(
            content="",
            model="none",
            backend="router",
            latency_ms=0,
            success=False,
            error="All backends failed: " + "; ".join(errors)
        )

    def generate_ensemble(
        self,
        prompt: str,
        min_responses: int = 2,
        **kwargs
    ) -> List[LLMResponse]:
        """
        Generate from multiple backends and return all responses.

        Useful for ensemble reasoning or model comparison.
        """
        available = self.get_available_backends()[:min_responses]
        responses = []

        for backend in available:
            response = backend.generate(prompt, **kwargs)
            responses.append(response)

        return responses


def create_default_router() -> LLMRouter:
    """Create a router with common backends."""
    router = LLMRouter()

    # Add backends in priority order
    router.add_backend(OllamaCLI())  # Local first
    router.add_backend(ClaudeCLI())
    router.add_backend(OpenAICLI())
    router.add_backend(GeminiCLI())

    return router


def check_available_backends() -> Dict[str, bool]:
    """Check which backends are available."""
    backends = {
        "ollama": OllamaCLI(),
        "claude": ClaudeCLI(),
        "openai": OpenAICLI(),
        "gemini": GeminiCLI(),
    }

    return {name: backend.is_available() for name, backend in backends.items()}
