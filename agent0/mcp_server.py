#!/usr/bin/env python3
"""
Agent0 MCP Server - Model Context Protocol server for Agent0.

Exposes Agent0 capabilities as tools that can be used by:
- Claude Desktop
- Claude CLI
- Any MCP-compatible AI assistant

Tools exposed:
- agent0_solve: Solve math/logic/code problems
- agent0_status: Check system status
- agent0_benchmark: Run benchmark evaluation
- agent0_chat: Multi-turn conversation

Usage:
    # Run as MCP server (stdio transport)
    python -m agent0.mcp_server

    # Or with explicit transport
    python -m agent0.mcp_server --transport stdio
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# MCP protocol implementation
# Using the official MCP SDK pattern

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class MCPServer:
    """
    MCP Server for Agent0.

    Implements the Model Context Protocol to expose Agent0 tools
    to external AI assistants like Claude Desktop/CLI.
    """

    def __init__(self, config_path: str = "agent0/configs/3070ti.yaml"):
        self.config_path = Path(config_path)
        self.config = None
        self.student = None
        self.initialized = False

        # Tool definitions
        self.tools = {
            "agent0_solve": {
                "name": "agent0_solve",
                "description": "Solve a math, logic, or code problem using Agent0's tool-augmented reasoning. Returns the solution with step-by-step reasoning.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "problem": {
                            "type": "string",
                            "description": "The problem to solve (e.g., 'Solve for x: 2x + 5 = 15')"
                        },
                        "domain": {
                            "type": "string",
                            "enum": ["math", "logic", "code"],
                            "default": "math",
                            "description": "Problem domain"
                        }
                    },
                    "required": ["problem"]
                }
            },
            "agent0_status": {
                "name": "agent0_status",
                "description": "Check Agent0 system status including Ollama connection, available models, and configuration.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "agent0_run": {
                "name": "agent0_run",
                "description": "Run Agent0 co-evolution training loop for a specified number of steps.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "integer",
                            "default": 5,
                            "description": "Number of co-evolution iterations to run"
                        },
                        "domains": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["math", "logic", "code"]},
                            "default": ["math"],
                            "description": "Domains to train on"
                        }
                    },
                    "required": []
                }
            },
            "agent0_benchmark": {
                "name": "agent0_benchmark",
                "description": "Run benchmark evaluation on MATH or GSM8K datasets.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "benchmark": {
                            "type": "string",
                            "enum": ["math", "gsm8k"],
                            "default": "math",
                            "description": "Benchmark type"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "description": "Maximum number of samples to evaluate"
                        }
                    },
                    "required": []
                }
            },
        }

    def _ensure_initialized(self) -> bool:
        """Ensure Agent0 components are initialized."""
        if self.initialized:
            return True

        try:
            import yaml
            if self.config_path.exists():
                with self.config_path.open('r') as f:
                    self.config = yaml.safe_load(f)
            else:
                self.config = self._default_config()

            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration if no config file exists."""
        return {
            "models": {
                "teacher": {"model": "qwen2.5:3b", "host": "http://127.0.0.1:11434"},
                "student": {"model": "qwen2.5:7b", "host": "http://127.0.0.1:11434"}
            },
            "tooling": {"enable_python": True, "enable_math": True},
            "logging": {"base_dir": "./runs"}
        }

    def _check_ollama(self) -> tuple[bool, List[str]]:
        """Check Ollama connection."""
        try:
            import requests
            host = self.config.get("models", {}).get("teacher", {}).get("host", "http://127.0.0.1:11434")
            response = requests.get(f"{host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = [m.get('name', 'unknown') for m in response.json().get('models', [])]
                return True, models
            return False, []
        except Exception:
            return False, []

    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a tool call and return the result."""
        self._ensure_initialized()

        if name == "agent0_solve":
            return await self._solve(arguments)
        elif name == "agent0_status":
            return await self._status(arguments)
        elif name == "agent0_run":
            return await self._run(arguments)
        elif name == "agent0_benchmark":
            return await self._benchmark(arguments)
        else:
            return {"error": f"Unknown tool: {name}"}

    async def _solve(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Solve a problem using Agent0."""
        problem = args.get("problem", "")
        domain = args.get("domain", "math")

        if not problem:
            return {"error": "No problem provided"}

        try:
            from agent0.agents.student import StudentAgent
            from agent0.tasks.schema import TaskSpec

            if self.student is None:
                self.student = StudentAgent(
                    self.config["models"]["student"],
                    tool_config=self.config.get("tooling", {})
                )

            task = TaskSpec(
                task_id="mcp-task",
                domain=domain,
                prompt=problem,
                constraints=[],
                verifier=None,
            )

            traj = self.student.solve(task)

            return {
                "result": traj.result,
                "success": traj.success,
                "domain": domain,
                "tools_used": [t.get("tool", "unknown") for t in traj.tool_calls],
                "reasoning": traj.messages[-1]["content"] if traj.messages else ""
            }
        except Exception as e:
            return {"error": str(e)}

    async def _status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get system status."""
        connected, models = self._check_ollama()

        return {
            "ollama_connected": connected,
            "available_models": models,
            "config_path": str(self.config_path),
            "teacher_model": self.config.get("models", {}).get("teacher", {}).get("model", "unknown"),
            "student_model": self.config.get("models", {}).get("student", {}).get("model", "unknown"),
        }

    async def _run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run co-evolution loop."""
        steps = args.get("steps", 5)
        domains = args.get("domains", ["math"])

        try:
            from agent0.loop.coordinator import Coordinator

            config = self.config.copy()
            config.setdefault("curriculum", {})["domains"] = domains

            coord = Coordinator(config)

            results = []
            successes = 0

            for i in range(steps):
                traj = coord.run_once({"next_task_id": f"mcp-task-{i}"})
                if traj:
                    results.append({
                        "step": i + 1,
                        "domain": traj.task.domain,
                        "success": traj.success,
                        "reward": traj.reward.get("total", 0.0)
                    })
                    if traj.success:
                        successes += 1

            return {
                "steps_completed": len(results),
                "successes": successes,
                "success_rate": successes / len(results) if results else 0,
                "details": results
            }
        except Exception as e:
            return {"error": str(e)}

    async def _benchmark(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run benchmark evaluation."""
        benchmark = args.get("benchmark", "math")
        limit = args.get("limit", 10)

        try:
            from agent0.benchmarks import BenchmarkLoader, BenchmarkEvaluator
            from agent0.agents.student import StudentAgent
            from agent0.tasks.schema import TaskSpec

            loader = BenchmarkLoader(Path("./data/benchmarks"))

            if benchmark == "math":
                count = loader.load_math(limit=limit)
            else:
                count = loader.load_gsm8k(limit=limit)

            if count == 0:
                return {"error": "No benchmark data found. Check ./data/benchmarks/"}

            student = StudentAgent(
                self.config["models"]["student"],
                tool_config=self.config.get("tooling", {})
            )

            def solver(problem: str) -> str:
                task = TaskSpec(task_id="bench", domain="math", prompt=problem, constraints=[], verifier=None)
                return student.solve(task).result

            evaluator = BenchmarkEvaluator()
            correct = 0

            for sample in loader.samples:
                result = evaluator.evaluate_sample(sample, solver)
                if result.correct:
                    correct += 1

            return {
                "benchmark": benchmark,
                "total": count,
                "correct": correct,
                "accuracy": correct / count if count > 0 else 0
            }
        except Exception as e:
            return {"error": str(e)}

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools."""
        return list(self.tools.values())


class MCPProtocolHandler:
    """
    Handle MCP JSON-RPC protocol over stdio.

    Implements the core MCP message flow:
    1. initialize -> capabilities exchange
    2. tools/list -> return available tools
    3. tools/call -> execute tool and return result
    """

    def __init__(self, server: MCPServer):
        self.server = server
        self.initialized = False

    async def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle an incoming JSON-RPC message."""
        method = message.get("method", "")
        params = message.get("params", {})
        msg_id = message.get("id")

        try:
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "initialized":
                # Notification, no response needed
                self.initialized = True
                return None
            elif method == "tools/list":
                result = await self._handle_tools_list(params)
            elif method == "tools/call":
                result = await self._handle_tools_call(params)
            elif method == "shutdown":
                result = {}
            else:
                result = {"error": {"code": -32601, "message": f"Method not found: {method}"}}

            if msg_id is not None:
                return {"jsonrpc": "2.0", "id": msg_id, "result": result}
            return None

        except Exception as e:
            logger.error(f"Error handling {method}: {e}")
            if msg_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": str(e)}
                }
            return None

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": False}
            },
            "serverInfo": {
                "name": "agent0",
                "version": "0.2.0"
            }
        }

    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        return {"tools": self.server.get_tools()}

    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        name = params.get("name", "")
        arguments = params.get("arguments", {})

        result = await self.server.handle_tool_call(name, arguments)

        # Format as MCP content
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }
            ]
        }


async def run_stdio_server():
    """Run MCP server over stdio transport."""
    server = MCPServer()
    handler = MCPProtocolHandler(server)

    logger.info("Agent0 MCP server starting on stdio...")

    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, asyncio.get_event_loop())

    buffer = ""

    while True:
        try:
            # Read line (JSON-RPC messages are newline-delimited)
            line = await reader.readline()
            if not line:
                break

            line = line.decode('utf-8').strip()
            if not line:
                continue

            # Parse JSON-RPC message
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON: {line}")
                continue

            # Handle message
            response = await handler.handle_message(message)

            # Send response if needed
            if response:
                response_str = json.dumps(response) + "\n"
                writer.write(response_str.encode('utf-8'))
                await writer.drain()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in server loop: {e}")
            continue

    logger.info("Agent0 MCP server shutting down")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Agent0 MCP Server")
    parser.add_argument("--transport", choices=["stdio"], default="stdio",
                       help="Transport type (currently only stdio supported)")
    parser.add_argument("--config", type=str, default="agent0/configs/3070ti.yaml",
                       help="Path to config file")

    args = parser.parse_args()

    if args.transport == "stdio":
        asyncio.run(run_stdio_server())
    else:
        print(f"Unknown transport: {args.transport}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
