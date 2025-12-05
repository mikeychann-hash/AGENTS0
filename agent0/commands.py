#!/usr/bin/env python3
"""
Agent0 Slash Command System.

Provides interactive slash commands for the CLI chat interface:
- /help       - Show help
- /ollama     - Manage Ollama connection/models
- /settings   - View/modify settings
- /train      - Start training
- /benchmark  - Run benchmark
- /status     - Show system status
- /models     - List available models
- /clear      - Clear conversation
- /history    - Show conversation history
- /save       - Save conversation/trace
- /load       - Load conversation
- /skills     - List cached skills
- /traces     - View stored traces
- /export     - Export data

Usage:
    from agent0.commands import CommandHandler

    handler = CommandHandler(config)
    result = handler.execute("/help")
    print(result.output)
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    @classmethod
    def disable(cls):
        cls.HEADER = cls.BLUE = cls.CYAN = cls.GREEN = ''
        cls.YELLOW = cls.RED = cls.ENDC = cls.BOLD = cls.DIM = ''


if not sys.stdout.isatty():
    Colors.disable()


@dataclass
class CommandResult:
    """Result of a slash command execution."""
    success: bool
    output: str
    data: Optional[Dict[str, Any]] = None
    action: Optional[str] = None  # Special action: "clear", "quit", "switch_model", etc.


@dataclass
class Command:
    """Slash command definition."""
    name: str
    description: str
    handler: Callable
    usage: str = ""
    aliases: List[str] = field(default_factory=list)
    category: str = "general"


class CommandHandler:
    """
    Slash command handler for Agent0 CLI.

    Manages registration and execution of interactive commands.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        conversation: Optional[Any] = None,
    ):
        self.config = config
        self.conversation = conversation
        self.commands: Dict[str, Command] = {}
        self.aliases: Dict[str, str] = {}
        self.settings: Dict[str, Any] = {
            "model": config.get("models", {}).get("student", {}).get("model", "qwen2.5:3b"),
            "temperature": 0.7,
            "max_tokens": 2048,
            "stream": True,
            "verbose": False,
            "ollama_host": "http://127.0.0.1:11434",
        }
        self._register_builtin_commands()

    def _register_builtin_commands(self):
        """Register all built-in commands."""
        # Help
        self.register(Command(
            name="help",
            description="Show available commands",
            handler=self._cmd_help,
            usage="/help [command]",
            aliases=["h", "?"],
            category="general",
        ))

        # Status
        self.register(Command(
            name="status",
            description="Show system status",
            handler=self._cmd_status,
            aliases=["st"],
            category="system",
        ))

        # Ollama
        self.register(Command(
            name="ollama",
            description="Manage Ollama connection and models",
            handler=self._cmd_ollama,
            usage="/ollama [list|pull|status|host] [args]",
            aliases=["ol"],
            category="models",
        ))

        # Models
        self.register(Command(
            name="models",
            description="List and switch models",
            handler=self._cmd_models,
            usage="/models [model_name]",
            aliases=["model", "m"],
            category="models",
        ))

        # Settings
        self.register(Command(
            name="settings",
            description="View or modify settings",
            handler=self._cmd_settings,
            usage="/settings [key] [value]",
            aliases=["set", "config"],
            category="system",
        ))

        # Clear
        self.register(Command(
            name="clear",
            description="Clear conversation history",
            handler=self._cmd_clear,
            aliases=["cls", "reset"],
            category="chat",
        ))

        # History
        self.register(Command(
            name="history",
            description="Show conversation history",
            handler=self._cmd_history,
            usage="/history [limit]",
            aliases=["hist"],
            category="chat",
        ))

        # Save
        self.register(Command(
            name="save",
            description="Save conversation to file",
            handler=self._cmd_save,
            usage="/save [filename]",
            category="data",
        ))

        # Load
        self.register(Command(
            name="load",
            description="Load conversation from file",
            handler=self._cmd_load,
            usage="/load <filename>",
            category="data",
        ))

        # Export
        self.register(Command(
            name="export",
            description="Export conversation/traces",
            handler=self._cmd_export,
            usage="/export [json|markdown|text] [filename]",
            category="data",
        ))

        # Train
        self.register(Command(
            name="train",
            description="Start training session",
            handler=self._cmd_train,
            usage="/train [--steps N] [--domain DOMAIN]",
            aliases=["tr"],
            category="training",
        ))

        # Benchmark
        self.register(Command(
            name="benchmark",
            description="Run benchmark evaluation",
            handler=self._cmd_benchmark,
            usage="/benchmark [math|gsm8k] [--limit N]",
            aliases=["bench", "eval"],
            category="training",
        ))

        # Skills
        self.register(Command(
            name="skills",
            description="List and manage cached skills",
            handler=self._cmd_skills,
            usage="/skills [list|add|remove|search] [args]",
            category="system",
        ))

        # Traces
        self.register(Command(
            name="traces",
            description="View stored execution traces",
            handler=self._cmd_traces,
            usage="/traces [list|show|search] [args]",
            category="data",
        ))

        # Quit
        self.register(Command(
            name="quit",
            description="Exit the chat",
            handler=self._cmd_quit,
            aliases=["exit", "q", "bye"],
            category="general",
        ))

        # Solve
        self.register(Command(
            name="solve",
            description="Solve a problem directly",
            handler=self._cmd_solve,
            usage="/solve <problem>",
            aliases=["s"],
            category="chat",
        ))

        # Tools
        self.register(Command(
            name="tools",
            description="List available tools",
            handler=self._cmd_tools,
            usage="/tools [tool_name]",
            aliases=["tool"],
            category="system",
        ))

        # Backend
        self.register(Command(
            name="backend",
            description="Manage LLM backends",
            handler=self._cmd_backend,
            usage="/backend [list|switch|test] [args]",
            aliases=["backends", "llm"],
            category="models",
        ))

        # Info
        self.register(Command(
            name="info",
            description="Show Agent0 info",
            handler=self._cmd_info,
            aliases=["about", "version"],
            category="general",
        ))

        # Debug
        self.register(Command(
            name="debug",
            description="Toggle debug mode",
            handler=self._cmd_debug,
            aliases=["dbg"],
            category="system",
        ))

    def register(self, command: Command):
        """Register a command."""
        self.commands[command.name] = command
        for alias in command.aliases:
            self.aliases[alias] = command.name

    def is_command(self, text: str) -> bool:
        """Check if text is a slash command."""
        return text.strip().startswith("/")

    def parse(self, text: str) -> tuple[str, List[str]]:
        """Parse command text into name and arguments."""
        text = text.strip()
        if not text.startswith("/"):
            return "", []

        parts = text[1:].split()
        if not parts:
            return "", []

        cmd_name = parts[0].lower()
        args = parts[1:]

        # Resolve alias
        if cmd_name in self.aliases:
            cmd_name = self.aliases[cmd_name]

        return cmd_name, args

    def execute(self, text: str) -> CommandResult:
        """Execute a slash command."""
        cmd_name, args = self.parse(text)

        if not cmd_name:
            return CommandResult(
                success=False,
                output=f"{Colors.RED}Invalid command{Colors.ENDC}",
            )

        if cmd_name not in self.commands:
            suggestions = self._suggest_command(cmd_name)
            output = f"{Colors.RED}Unknown command: /{cmd_name}{Colors.ENDC}"
            if suggestions:
                output += f"\n{Colors.DIM}Did you mean: {', '.join(suggestions)}?{Colors.ENDC}"
            return CommandResult(success=False, output=output)

        command = self.commands[cmd_name]
        try:
            return command.handler(args)
        except Exception as e:
            return CommandResult(
                success=False,
                output=f"{Colors.RED}Error executing /{cmd_name}: {e}{Colors.ENDC}",
            )

    def _suggest_command(self, name: str) -> List[str]:
        """Suggest similar commands."""
        suggestions = []
        for cmd in self.commands:
            if cmd.startswith(name) or name in cmd:
                suggestions.append(f"/{cmd}")
        return suggestions[:3]

    # ========================================================================
    # Command Handlers
    # ========================================================================

    def _cmd_help(self, args: List[str]) -> CommandResult:
        """Show help."""
        if args:
            # Help for specific command
            cmd_name = args[0].lstrip("/")
            if cmd_name in self.aliases:
                cmd_name = self.aliases[cmd_name]
            if cmd_name in self.commands:
                cmd = self.commands[cmd_name]
                output = f"{Colors.BOLD}/{cmd.name}{Colors.ENDC} - {cmd.description}\n"
                if cmd.usage:
                    output += f"{Colors.DIM}Usage: {cmd.usage}{Colors.ENDC}\n"
                if cmd.aliases:
                    output += f"{Colors.DIM}Aliases: {', '.join('/' + a for a in cmd.aliases)}{Colors.ENDC}"
                return CommandResult(success=True, output=output)
            return CommandResult(
                success=False,
                output=f"{Colors.RED}Unknown command: {cmd_name}{Colors.ENDC}",
            )

        # Group commands by category
        categories: Dict[str, List[Command]] = {}
        for cmd in self.commands.values():
            if cmd.category not in categories:
                categories[cmd.category] = []
            categories[cmd.category].append(cmd)

        output = f"{Colors.BOLD}Available Commands{Colors.ENDC}\n"
        output += f"{Colors.DIM}{'─' * 50}{Colors.ENDC}\n"

        category_order = ["general", "chat", "models", "training", "data", "system"]
        for category in category_order:
            if category in categories:
                output += f"\n{Colors.CYAN}{category.upper()}{Colors.ENDC}\n"
                for cmd in sorted(categories[category], key=lambda c: c.name):
                    aliases = f" ({', '.join('/' + a for a in cmd.aliases)})" if cmd.aliases else ""
                    output += f"  {Colors.GREEN}/{cmd.name}{Colors.ENDC}{Colors.DIM}{aliases}{Colors.ENDC}\n"
                    output += f"    {cmd.description}\n"

        output += f"\n{Colors.DIM}Type /help <command> for detailed help{Colors.ENDC}"
        return CommandResult(success=True, output=output)

    def _cmd_status(self, args: List[str]) -> CommandResult:
        """Show system status."""
        output = f"{Colors.BOLD}System Status{Colors.ENDC}\n"
        output += f"{Colors.DIM}{'─' * 40}{Colors.ENDC}\n"

        # Ollama
        connected, models = self._check_ollama()
        if connected:
            output += f"{Colors.GREEN}●{Colors.ENDC} Ollama: Connected ({len(models)} models)\n"
        else:
            output += f"{Colors.RED}●{Colors.ENDC} Ollama: Disconnected\n"

        # Current model
        output += f"{Colors.CYAN}●{Colors.ENDC} Model: {self.settings['model']}\n"

        # Settings
        output += f"{Colors.CYAN}●{Colors.ENDC} Temperature: {self.settings['temperature']}\n"
        output += f"{Colors.CYAN}●{Colors.ENDC} Max Tokens: {self.settings['max_tokens']}\n"

        # Conversation
        if self.conversation:
            turns = len(getattr(self.conversation, 'history', []))
            output += f"{Colors.CYAN}●{Colors.ENDC} Conversation: {turns} turns\n"

        return CommandResult(success=True, output=output)

    def _cmd_ollama(self, args: List[str]) -> CommandResult:
        """Manage Ollama."""
        if not args:
            args = ["status"]

        subcmd = args[0].lower()

        if subcmd == "status":
            connected, models = self._check_ollama()
            if connected:
                output = f"{Colors.GREEN}Ollama is running{Colors.ENDC}\n"
                output += f"Host: {self.settings['ollama_host']}\n"
                output += f"Models: {len(models)}"
            else:
                output = f"{Colors.RED}Ollama is not running{Colors.ENDC}\n"
                output += f"{Colors.DIM}Start with: ollama serve{Colors.ENDC}"
            return CommandResult(success=True, output=output)

        elif subcmd == "list":
            connected, models = self._check_ollama()
            if not connected:
                return CommandResult(
                    success=False,
                    output=f"{Colors.RED}Ollama not connected{Colors.ENDC}",
                )
            output = f"{Colors.BOLD}Available Models{Colors.ENDC}\n"
            for model in models:
                current = " (current)" if model == self.settings['model'] else ""
                output += f"  • {model}{Colors.GREEN}{current}{Colors.ENDC}\n"
            return CommandResult(success=True, output=output, data={"models": models})

        elif subcmd == "pull":
            if len(args) < 2:
                return CommandResult(
                    success=False,
                    output=f"{Colors.YELLOW}Usage: /ollama pull <model_name>{Colors.ENDC}",
                )
            model = args[1]
            output = f"Pulling model: {model}\n"
            output += f"{Colors.DIM}Run in terminal: ollama pull {model}{Colors.ENDC}"
            return CommandResult(success=True, output=output)

        elif subcmd == "host":
            if len(args) >= 2:
                self.settings['ollama_host'] = args[1]
                return CommandResult(
                    success=True,
                    output=f"Ollama host set to: {args[1]}",
                )
            return CommandResult(
                success=True,
                output=f"Current host: {self.settings['ollama_host']}",
            )

        return CommandResult(
            success=False,
            output=f"{Colors.YELLOW}Usage: /ollama [status|list|pull|host]{Colors.ENDC}",
        )

    def _cmd_models(self, args: List[str]) -> CommandResult:
        """List and switch models."""
        if args:
            # Switch model
            model = args[0]
            old_model = self.settings['model']
            self.settings['model'] = model
            return CommandResult(
                success=True,
                output=f"Model changed: {old_model} → {Colors.GREEN}{model}{Colors.ENDC}",
                action="switch_model",
                data={"model": model},
            )

        # List models
        connected, models = self._check_ollama()
        if not connected:
            return CommandResult(
                success=False,
                output=f"{Colors.RED}Ollama not connected{Colors.ENDC}",
            )

        output = f"{Colors.BOLD}Models{Colors.ENDC}\n"
        current = self.settings['model']
        for model in models:
            if model == current:
                output += f"  {Colors.GREEN}● {model} (active){Colors.ENDC}\n"
            else:
                output += f"  ○ {model}\n"
        output += f"\n{Colors.DIM}Switch with: /models <name>{Colors.ENDC}"
        return CommandResult(success=True, output=output, data={"models": models})

    def _cmd_settings(self, args: List[str]) -> CommandResult:
        """View or modify settings."""
        if not args:
            # Show all settings
            output = f"{Colors.BOLD}Settings{Colors.ENDC}\n"
            output += f"{Colors.DIM}{'─' * 40}{Colors.ENDC}\n"
            for key, value in self.settings.items():
                output += f"  {key}: {Colors.CYAN}{value}{Colors.ENDC}\n"
            output += f"\n{Colors.DIM}Change with: /settings <key> <value>{Colors.ENDC}"
            return CommandResult(success=True, output=output, data={"settings": self.settings})

        key = args[0]
        if len(args) == 1:
            # Show single setting
            if key in self.settings:
                return CommandResult(
                    success=True,
                    output=f"{key}: {Colors.CYAN}{self.settings[key]}{Colors.ENDC}",
                )
            return CommandResult(
                success=False,
                output=f"{Colors.RED}Unknown setting: {key}{Colors.ENDC}",
            )

        # Set value
        value = args[1]

        # Type conversion
        if key in ["temperature"]:
            value = float(value)
        elif key in ["max_tokens"]:
            value = int(value)
        elif key in ["stream", "verbose"]:
            value = value.lower() in ("true", "1", "yes", "on")

        if key not in self.settings:
            return CommandResult(
                success=False,
                output=f"{Colors.RED}Unknown setting: {key}{Colors.ENDC}",
            )

        old_value = self.settings[key]
        self.settings[key] = value
        return CommandResult(
            success=True,
            output=f"{key}: {old_value} → {Colors.GREEN}{value}{Colors.ENDC}",
        )

    def _cmd_clear(self, args: List[str]) -> CommandResult:
        """Clear conversation."""
        return CommandResult(
            success=True,
            output=f"{Colors.DIM}Conversation cleared{Colors.ENDC}",
            action="clear",
        )

    def _cmd_history(self, args: List[str]) -> CommandResult:
        """Show conversation history."""
        if not self.conversation:
            return CommandResult(
                success=True,
                output=f"{Colors.DIM}No conversation history{Colors.ENDC}",
            )

        history = getattr(self.conversation, 'history', [])
        if not history:
            return CommandResult(
                success=True,
                output=f"{Colors.DIM}No conversation history{Colors.ENDC}",
            )

        limit = int(args[0]) if args else 10
        output = f"{Colors.BOLD}History (last {min(limit, len(history))} turns){Colors.ENDC}\n"
        output += f"{Colors.DIM}{'─' * 40}{Colors.ENDC}\n"

        for turn in history[-limit:]:
            role = turn.get("role", "unknown")
            content = turn.get("content", "")[:100]
            if len(turn.get("content", "")) > 100:
                content += "..."

            if role == "user":
                output += f"{Colors.CYAN}You:{Colors.ENDC} {content}\n"
            else:
                output += f"{Colors.GREEN}Agent:{Colors.ENDC} {content}\n"

        return CommandResult(success=True, output=output)

    def _cmd_save(self, args: List[str]) -> CommandResult:
        """Save conversation."""
        filename = args[0] if args else f"conversation_{datetime.now():%Y%m%d_%H%M%S}.json"

        if not self.conversation:
            return CommandResult(
                success=False,
                output=f"{Colors.RED}No conversation to save{Colors.ENDC}",
            )

        history = getattr(self.conversation, 'history', [])
        data = {
            "timestamp": datetime.now().isoformat(),
            "model": self.settings['model'],
            "settings": self.settings,
            "history": history,
        }

        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

        return CommandResult(
            success=True,
            output=f"Saved to: {Colors.GREEN}{path}{Colors.ENDC}",
        )

    def _cmd_load(self, args: List[str]) -> CommandResult:
        """Load conversation."""
        if not args:
            return CommandResult(
                success=False,
                output=f"{Colors.YELLOW}Usage: /load <filename>{Colors.ENDC}",
            )

        path = Path(args[0])
        if not path.exists():
            return CommandResult(
                success=False,
                output=f"{Colors.RED}File not found: {path}{Colors.ENDC}",
            )

        data = json.loads(path.read_text())
        return CommandResult(
            success=True,
            output=f"Loaded conversation from: {path}",
            action="load",
            data=data,
        )

    def _cmd_export(self, args: List[str]) -> CommandResult:
        """Export conversation."""
        format_type = args[0] if args else "json"
        filename = args[1] if len(args) > 1 else f"export_{datetime.now():%Y%m%d_%H%M%S}"

        if not self.conversation:
            return CommandResult(
                success=False,
                output=f"{Colors.RED}No conversation to export{Colors.ENDC}",
            )

        history = getattr(self.conversation, 'history', [])

        if format_type == "json":
            filename = f"{filename}.json"
            content = json.dumps({"history": history}, indent=2)
        elif format_type == "markdown":
            filename = f"{filename}.md"
            content = "# Conversation\n\n"
            for turn in history:
                role = "**You**" if turn.get("role") == "user" else "**Agent**"
                content += f"{role}: {turn.get('content', '')}\n\n"
        else:  # text
            filename = f"{filename}.txt"
            content = ""
            for turn in history:
                role = "You" if turn.get("role") == "user" else "Agent"
                content += f"{role}: {turn.get('content', '')}\n\n"

        Path(filename).write_text(content)
        return CommandResult(
            success=True,
            output=f"Exported to: {Colors.GREEN}{filename}{Colors.ENDC}",
        )

    def _cmd_train(self, args: List[str]) -> CommandResult:
        """Start training."""
        steps = 10
        domain = "math"

        i = 0
        while i < len(args):
            if args[i] == "--steps" and i + 1 < len(args):
                steps = int(args[i + 1])
                i += 2
            elif args[i] == "--domain" and i + 1 < len(args):
                domain = args[i + 1]
                i += 2
            else:
                i += 1

        output = f"{Colors.BOLD}Training Configuration{Colors.ENDC}\n"
        output += f"  Steps: {steps}\n"
        output += f"  Domain: {domain}\n"
        output += f"\n{Colors.DIM}Starting training...{Colors.ENDC}\n"
        output += f"{Colors.YELLOW}Run in terminal: agent0 train --steps {steps}{Colors.ENDC}"

        return CommandResult(
            success=True,
            output=output,
            action="train",
            data={"steps": steps, "domain": domain},
        )

    def _cmd_benchmark(self, args: List[str]) -> CommandResult:
        """Run benchmark."""
        bench_type = args[0] if args else "math"
        limit = 50

        for i, arg in enumerate(args):
            if arg == "--limit" and i + 1 < len(args):
                limit = int(args[i + 1])

        output = f"{Colors.BOLD}Benchmark Configuration{Colors.ENDC}\n"
        output += f"  Type: {bench_type}\n"
        output += f"  Limit: {limit}\n"
        output += f"\n{Colors.YELLOW}Run: agent0 benchmark --type {bench_type} --limit {limit}{Colors.ENDC}"

        return CommandResult(
            success=True,
            output=output,
            action="benchmark",
            data={"type": bench_type, "limit": limit},
        )

    def _cmd_skills(self, args: List[str]) -> CommandResult:
        """Manage skills."""
        subcmd = args[0] if args else "list"

        if subcmd == "list":
            try:
                from agent0.storage import SkillCache
                cache = SkillCache()
                skills = list(cache.skills.values())

                if not skills:
                    return CommandResult(
                        success=True,
                        output=f"{Colors.DIM}No cached skills{Colors.ENDC}",
                    )

                output = f"{Colors.BOLD}Cached Skills{Colors.ENDC}\n"
                for skill in skills[:10]:
                    conf = skill.confidence * 100
                    output += f"  • {skill.name} ({skill.domain}) - {conf:.0f}% confidence\n"
                return CommandResult(success=True, output=output)
            except Exception as e:
                return CommandResult(
                    success=False,
                    output=f"{Colors.RED}Error: {e}{Colors.ENDC}",
                )

        elif subcmd == "search" and len(args) > 1:
            query = " ".join(args[1:])
            try:
                from agent0.storage import SkillCache
                cache = SkillCache()
                matches = cache.find_skill(query)

                if not matches:
                    return CommandResult(
                        success=True,
                        output=f"{Colors.DIM}No matching skills{Colors.ENDC}",
                    )

                output = f"{Colors.BOLD}Matching Skills{Colors.ENDC}\n"
                for skill, score in matches:
                    output += f"  • {skill.name} (score: {score:.2f})\n"
                return CommandResult(success=True, output=output)
            except Exception as e:
                return CommandResult(
                    success=False,
                    output=f"{Colors.RED}Error: {e}{Colors.ENDC}",
                )

        return CommandResult(
            success=False,
            output=f"{Colors.YELLOW}Usage: /skills [list|search <query>]{Colors.ENDC}",
        )

    def _cmd_traces(self, args: List[str]) -> CommandResult:
        """View traces."""
        subcmd = args[0] if args else "list"

        try:
            from agent0.storage import TraceStore
            store = TraceStore()

            if subcmd == "list":
                # List recent traces
                output = f"{Colors.BOLD}Recent Traces{Colors.ENDC}\n"
                output += f"{Colors.DIM}Trace storage location: {store.backend.__class__.__name__}{Colors.ENDC}\n"
                # Note: Full list would require backend enumeration
                output += f"\n{Colors.DIM}Use trace IDs from task execution{Colors.ENDC}"
                return CommandResult(success=True, output=output)

            elif subcmd == "show" and len(args) > 1:
                trace_id = args[1]
                trace = store.get_trace(trace_id)
                if not trace:
                    return CommandResult(
                        success=False,
                        output=f"{Colors.RED}Trace not found: {trace_id}{Colors.ENDC}",
                    )
                output = f"{Colors.BOLD}Trace: {trace_id}{Colors.ENDC}\n"
                output += f"  Task: {trace.task_id}\n"
                output += f"  Domain: {trace.domain}\n"
                output += f"  Success: {trace.success}\n"
                output += f"  Steps: {len(trace.steps)}\n"
                return CommandResult(success=True, output=output)

            return CommandResult(
                success=False,
                output=f"{Colors.YELLOW}Usage: /traces [list|show <trace_id>]{Colors.ENDC}",
            )
        except Exception as e:
            return CommandResult(
                success=False,
                output=f"{Colors.RED}Error: {e}{Colors.ENDC}",
            )

    def _cmd_quit(self, args: List[str]) -> CommandResult:
        """Quit chat."""
        return CommandResult(
            success=True,
            output=f"{Colors.DIM}Goodbye!{Colors.ENDC}",
            action="quit",
        )

    def _cmd_solve(self, args: List[str]) -> CommandResult:
        """Solve a problem directly."""
        if not args:
            return CommandResult(
                success=False,
                output=f"{Colors.YELLOW}Usage: /solve <problem>{Colors.ENDC}",
            )

        problem = " ".join(args)
        return CommandResult(
            success=True,
            output=f"{Colors.DIM}Solving: {problem}{Colors.ENDC}",
            action="solve",
            data={"problem": problem},
        )

    def _cmd_tools(self, args: List[str]) -> CommandResult:
        """List available tools."""
        tools = [
            ("python", "Execute Python code"),
            ("calculator", "Mathematical calculations"),
            ("shell", "Shell command execution"),
            ("filesystem", "File operations"),
            ("http", "HTTP requests"),
            ("search", "Web search"),
        ]

        if args:
            # Show specific tool
            tool_name = args[0]
            for name, desc in tools:
                if name == tool_name:
                    return CommandResult(
                        success=True,
                        output=f"{Colors.BOLD}{name}{Colors.ENDC}\n{desc}",
                    )
            return CommandResult(
                success=False,
                output=f"{Colors.RED}Unknown tool: {tool_name}{Colors.ENDC}",
            )

        output = f"{Colors.BOLD}Available Tools{Colors.ENDC}\n"
        for name, desc in tools:
            output += f"  • {Colors.GREEN}{name}{Colors.ENDC}: {desc}\n"
        return CommandResult(success=True, output=output)

    def _cmd_backend(self, args: List[str]) -> CommandResult:
        """Manage backends."""
        subcmd = args[0] if args else "list"

        backends = {
            "ollama": self._check_ollama()[0],
            "claude": self._check_claude_cli(),
            "openai": bool(os.environ.get("OPENAI_API_KEY")),
            "gemini": bool(os.environ.get("GOOGLE_API_KEY")),
        }

        if subcmd == "list":
            output = f"{Colors.BOLD}LLM Backends{Colors.ENDC}\n"
            for name, available in backends.items():
                status = f"{Colors.GREEN}●{Colors.ENDC}" if available else f"{Colors.RED}○{Colors.ENDC}"
                output += f"  {status} {name}\n"
            return CommandResult(success=True, output=output, data={"backends": backends})

        elif subcmd == "switch" and len(args) > 1:
            backend = args[1]
            if backend not in backends:
                return CommandResult(
                    success=False,
                    output=f"{Colors.RED}Unknown backend: {backend}{Colors.ENDC}",
                )
            if not backends[backend]:
                return CommandResult(
                    success=False,
                    output=f"{Colors.RED}Backend not available: {backend}{Colors.ENDC}",
                )
            return CommandResult(
                success=True,
                output=f"Switched to: {Colors.GREEN}{backend}{Colors.ENDC}",
                action="switch_backend",
                data={"backend": backend},
            )

        return CommandResult(
            success=False,
            output=f"{Colors.YELLOW}Usage: /backend [list|switch <name>]{Colors.ENDC}",
        )

    def _cmd_info(self, args: List[str]) -> CommandResult:
        """Show Agent0 info."""
        output = f"""
{Colors.CYAN}╔═══════════════════════════════════════╗
║  {Colors.BOLD}Agent0{Colors.ENDC}{Colors.CYAN} - Self-Evolving AI Agents    ║
╚═══════════════════════════════════════╝{Colors.ENDC}

{Colors.BOLD}Version:{Colors.ENDC} 0.1.0
{Colors.BOLD}Features:{Colors.ENDC}
  • Dual-agent co-evolution
  • Tool-integrated reasoning
  • VeRL-style RL training
  • Multi-backend LLM support
  • MCP server integration

{Colors.DIM}https://github.com/agent0{Colors.ENDC}
"""
        return CommandResult(success=True, output=output)

    def _cmd_debug(self, args: List[str]) -> CommandResult:
        """Toggle debug mode."""
        self.settings['verbose'] = not self.settings['verbose']
        status = "enabled" if self.settings['verbose'] else "disabled"
        color = Colors.GREEN if self.settings['verbose'] else Colors.DIM
        return CommandResult(
            success=True,
            output=f"Debug mode: {color}{status}{Colors.ENDC}",
        )

    # ========================================================================
    # Helpers
    # ========================================================================

    def _check_ollama(self) -> tuple[bool, List[str]]:
        """Check Ollama connection."""
        try:
            import requests
            response = requests.get(
                f"{self.settings['ollama_host']}/api/tags",
                timeout=5,
            )
            if response.status_code == 200:
                models = [m.get('name', '') for m in response.json().get('models', [])]
                return True, models
            return False, []
        except Exception:
            return False, []

    def _check_claude_cli(self) -> bool:
        """Check if Claude CLI is available."""
        import shutil
        return shutil.which("claude") is not None


# Convenience function
def handle_command(text: str, config: Dict[str, Any], conversation: Any = None) -> CommandResult:
    """Handle a slash command."""
    handler = CommandHandler(config, conversation)
    return handler.execute(text)
