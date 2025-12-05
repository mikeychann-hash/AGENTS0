#!/usr/bin/env python3
"""
Agent0 Shell Runner Tool.

Provides safe shell command execution for agents:
- Command execution with timeouts
- Environment variable handling
- Working directory support
- Output capture and streaming
- Background execution
- Command allowlisting

Usage:
    from agent0.tools.shell_runner import Shell, run_shell

    # Simple execution
    result = run_shell("ls -la")

    # Advanced usage
    shell = Shell(workdir="/workspace")
    result = shell.run("python script.py", timeout=60)
    result = shell.run_background("python server.py")
"""
from __future__ import annotations

import logging
import os
import shlex
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from agent0.tools.sandbox import limit_resources

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of a shell command execution."""
    status: str  # "ok", "error", "timeout", "blocked", "killed"
    stdout: str
    stderr: str
    exit_code: Optional[int]
    command: str
    duration_ms: float
    pid: Optional[int] = None

    @property
    def success(self) -> bool:
        return self.status == "ok" and self.exit_code == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "command": self.command,
            "duration_ms": self.duration_ms,
            "success": self.success,
        }


@dataclass
class BackgroundProcess:
    """A background process handle."""
    pid: int
    command: str
    process: subprocess.Popen
    started_at: float
    output_buffer: List[str] = field(default_factory=list)
    error_buffer: List[str] = field(default_factory=list)
    _reader_thread: Optional[threading.Thread] = None

    def is_running(self) -> bool:
        return self.process.poll() is None

    def get_output(self, clear: bool = False) -> str:
        output = "\n".join(self.output_buffer)
        if clear:
            self.output_buffer.clear()
        return output

    def get_errors(self, clear: bool = False) -> str:
        errors = "\n".join(self.error_buffer)
        if clear:
            self.error_buffer.clear()
        return errors

    def kill(self) -> bool:
        try:
            self.process.terminate()
            time.sleep(0.1)
            if self.is_running():
                self.process.kill()
            return True
        except Exception:
            return False


class Shell:
    """
    Safe shell command executor.

    Features:
    - Command allowlisting
    - Timeout handling
    - Environment variables
    - Background execution
    - Output streaming
    """

    # Common safe commands
    DEFAULT_ALLOWED = [
        # File operations
        "ls", "cat", "head", "tail", "wc", "find", "grep", "awk", "sed",
        "cp", "mv", "rm", "mkdir", "rmdir", "touch", "chmod",
        # Python
        "python", "python3", "pip", "pip3", "pytest", "black", "ruff",
        # Node
        "node", "npm", "npx", "yarn",
        # Git
        "git",
        # System info
        "echo", "pwd", "whoami", "date", "env", "which", "uname",
        # Networking (limited)
        "curl", "wget", "ping",
        # Compression
        "tar", "gzip", "gunzip", "zip", "unzip",
        # Process
        "ps", "top", "htop", "kill",
    ]

    def __init__(
        self,
        workdir: Union[str, Path] = ".",
        timeout: int = 30,
        allowed_commands: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        use_sandbox: bool = True,
    ):
        self.workdir = Path(workdir).resolve()
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.allowed_commands = allowed_commands or self.DEFAULT_ALLOWED
        self.env = {**os.environ, **(env or {})}
        self.use_sandbox = use_sandbox
        self._background_processes: Dict[int, BackgroundProcess] = {}

    def _check_command(self, command: str) -> Optional[str]:
        """Check if command is allowed. Returns error message if blocked."""
        if not self.allowed_commands:
            return None  # All commands allowed

        # Parse command to get the binary name
        try:
            parts = shlex.split(command)
            if not parts:
                return "Empty command"
            binary = parts[0].split("/")[-1]  # Handle full paths
        except ValueError:
            # Fall back to simple split
            binary = command.strip().split()[0].split("/")[-1]

        if binary not in self.allowed_commands:
            return f"Command '{binary}' not in allowlist"
        return None

    def run(
        self,
        command: str,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        workdir: Optional[Union[str, Path]] = None,
        shell: bool = True,
        capture_output: bool = True,
    ) -> CommandResult:
        """
        Execute a shell command.

        Args:
            command: The command to execute
            timeout: Override default timeout (seconds)
            env: Additional environment variables
            workdir: Override working directory
            shell: Use shell execution (default True)
            capture_output: Capture stdout/stderr

        Returns:
            CommandResult with execution details
        """
        start_time = time.time()

        # Check allowlist
        error = self._check_command(command)
        if error:
            return CommandResult(
                status="blocked",
                stdout="",
                stderr=error,
                exit_code=None,
                command=command,
                duration_ms=0,
            )

        # Prepare execution
        exec_timeout = timeout or self.timeout
        exec_env = {**self.env, **(env or {})}
        exec_workdir = Path(workdir).resolve() if workdir else self.workdir
        exec_workdir.mkdir(parents=True, exist_ok=True)

        try:
            if self.use_sandbox:
                with limit_resources():
                    result = subprocess.run(
                        command,
                        shell=shell,
                        capture_output=capture_output,
                        text=True,
                        timeout=exec_timeout,
                        cwd=exec_workdir,
                        env=exec_env,
                    )
            else:
                result = subprocess.run(
                    command,
                    shell=shell,
                    capture_output=capture_output,
                    text=True,
                    timeout=exec_timeout,
                    cwd=exec_workdir,
                    env=exec_env,
                )

            duration_ms = (time.time() - start_time) * 1000
            return CommandResult(
                status="ok",
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                exit_code=result.returncode,
                command=command,
                duration_ms=duration_ms,
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.time() - start_time) * 1000
            return CommandResult(
                status="timeout",
                stdout="",
                stderr=f"Command timed out after {exec_timeout}s",
                exit_code=None,
                command=command,
                duration_ms=duration_ms,
            )

        except FileNotFoundError as e:
            duration_ms = (time.time() - start_time) * 1000
            return CommandResult(
                status="error",
                stdout="",
                stderr=f"Command not found: {e}",
                exit_code=None,
                command=command,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return CommandResult(
                status="error",
                stdout="",
                stderr=str(e),
                exit_code=None,
                command=command,
                duration_ms=duration_ms,
            )

    def run_background(
        self,
        command: str,
        env: Optional[Dict[str, str]] = None,
        workdir: Optional[Union[str, Path]] = None,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Start a command in the background.

        Args:
            command: The command to execute
            env: Additional environment variables
            workdir: Override working directory
            on_output: Callback for output lines

        Returns:
            Dict with process info and pid
        """
        # Check allowlist
        error = self._check_command(command)
        if error:
            return {"status": "blocked", "error": error}

        exec_env = {**self.env, **(env or {})}
        exec_workdir = Path(workdir).resolve() if workdir else self.workdir

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=exec_workdir,
                env=exec_env,
            )

            bg_process = BackgroundProcess(
                pid=process.pid,
                command=command,
                process=process,
                started_at=time.time(),
            )

            # Start output reader thread
            def read_output():
                for line in iter(process.stdout.readline, ""):
                    bg_process.output_buffer.append(line.rstrip())
                    if on_output:
                        on_output(line.rstrip())
                for line in iter(process.stderr.readline, ""):
                    bg_process.error_buffer.append(line.rstrip())

            thread = threading.Thread(target=read_output, daemon=True)
            thread.start()
            bg_process._reader_thread = thread

            self._background_processes[process.pid] = bg_process

            return {
                "status": "ok",
                "pid": process.pid,
                "command": command,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def check_process(self, pid: int) -> Dict[str, Any]:
        """Check status of a background process."""
        if pid not in self._background_processes:
            return {"status": "error", "error": "Process not found"}

        bg_process = self._background_processes[pid]
        running = bg_process.is_running()
        exit_code = bg_process.process.returncode if not running else None

        return {
            "status": "ok",
            "pid": pid,
            "command": bg_process.command,
            "running": running,
            "exit_code": exit_code,
            "runtime_seconds": time.time() - bg_process.started_at,
            "stdout_lines": len(bg_process.output_buffer),
            "stderr_lines": len(bg_process.error_buffer),
        }

    def get_output(self, pid: int, clear: bool = False) -> Dict[str, Any]:
        """Get output from a background process."""
        if pid not in self._background_processes:
            return {"status": "error", "error": "Process not found"}

        bg_process = self._background_processes[pid]
        return {
            "status": "ok",
            "stdout": bg_process.get_output(clear),
            "stderr": bg_process.get_errors(clear),
        }

    def kill_process(self, pid: int) -> Dict[str, Any]:
        """Kill a background process."""
        if pid not in self._background_processes:
            return {"status": "error", "error": "Process not found"}

        bg_process = self._background_processes[pid]
        if bg_process.kill():
            return {"status": "ok", "killed": pid}
        return {"status": "error", "error": "Failed to kill process"}

    def list_processes(self) -> Dict[str, Any]:
        """List all background processes."""
        processes = []
        for pid, bg_process in self._background_processes.items():
            processes.append({
                "pid": pid,
                "command": bg_process.command,
                "running": bg_process.is_running(),
                "runtime_seconds": time.time() - bg_process.started_at,
            })
        return {"status": "ok", "processes": processes}

    def cleanup(self) -> None:
        """Kill all background processes."""
        for bg_process in self._background_processes.values():
            bg_process.kill()
        self._background_processes.clear()

    # Convenience methods

    def python(self, script: str, timeout: Optional[int] = None) -> CommandResult:
        """Run a Python script/command."""
        return self.run(f'python3 -c "{script}"', timeout=timeout)

    def pip_install(self, package: str) -> CommandResult:
        """Install a Python package."""
        return self.run(f"pip install {package}", timeout=120)

    def git(self, args: str) -> CommandResult:
        """Run a git command."""
        return self.run(f"git {args}")

    def which(self, command: str) -> Optional[str]:
        """Find command location."""
        result = self.run(f"which {command}", timeout=5)
        if result.success:
            return result.stdout.strip()
        return None


# Global default shell
_default_shell: Optional[Shell] = None


def get_shell(workdir: str = ".") -> Shell:
    """Get or create the default shell instance."""
    global _default_shell
    if _default_shell is None:
        _default_shell = Shell(workdir=workdir)
    return _default_shell


# Simple function interface (legacy compatible)
def run_shell(
    command: str,
    allowed_binaries: Optional[List[str]] = None,
    timeout: int = 15,
    workdir: str = ".",
) -> Dict[str, str]:
    """
    Run shell commands with an allowlist check.

    Legacy-compatible interface.
    """
    shell = Shell(
        workdir=workdir,
        timeout=timeout,
        allowed_commands=allowed_binaries,
    )
    result = shell.run(command)
    return {
        "status": result.status,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


# Additional utility functions

def exec_python(code: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute Python code and return result."""
    shell = get_shell()
    # Escape the code for shell
    escaped = code.replace("'", "'\"'\"'")
    result = shell.run(f"python3 -c '{escaped}'", timeout=timeout)
    return result.to_dict()


def exec_script(
    script_path: str,
    args: Optional[List[str]] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Execute a script file."""
    shell = get_shell()
    args_str = " ".join(args or [])
    result = shell.run(f"python3 {script_path} {args_str}", timeout=timeout)
    return result.to_dict()


def check_command_exists(command: str) -> bool:
    """Check if a command exists on the system."""
    shell = get_shell()
    return shell.which(command) is not None
