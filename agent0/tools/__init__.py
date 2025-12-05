"""
Agent0 Tools Module.

Provides tool integrations for agents:
- FileSystem: Sandboxed file operations
- Shell: Safe command execution
- HTTPClient: HTTP requests with rate limiting
- MathEngine: Symbolic computation
- PythonRunner: Safe Python execution

Usage:
    from agent0.tools import FileSystem, Shell, HTTPClient

    # Filesystem operations
    fs = FileSystem(base_dir="/workspace")
    fs.write("test.txt", "Hello")
    content = fs.read("test.txt")

    # Shell commands
    shell = Shell(workdir="/workspace")
    result = shell.run("ls -la")

    # HTTP requests
    client = HTTPClient(base_url="https://api.example.com")
    response = client.get("/users")
"""
from agent0.tools.file_ops import (
    FileSystem,
    FileInfo,
    safe_read,
    safe_write,
)
from agent0.tools.shell_runner import (
    Shell,
    CommandResult,
    BackgroundProcess,
    run_shell,
    get_shell,
    exec_python,
    exec_script,
    check_command_exists,
)
from agent0.tools.http_client import (
    HTTPClient,
    HTTPResponse,
    RateLimiter,
    http_get,
    http_post,
    fetch_json,
    fetch_text,
)

__all__ = [
    # Filesystem
    "FileSystem",
    "FileInfo",
    "safe_read",
    "safe_write",
    # Shell
    "Shell",
    "CommandResult",
    "BackgroundProcess",
    "run_shell",
    "get_shell",
    "exec_python",
    "exec_script",
    "check_command_exists",
    # HTTP
    "HTTPClient",
    "HTTPResponse",
    "RateLimiter",
    "http_get",
    "http_post",
    "fetch_json",
    "fetch_text",
]
