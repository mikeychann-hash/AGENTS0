#!/usr/bin/env python3
"""
Agent0 CLI - Unified command-line interface for Agent0.

Usage:
    agent0 run [OPTIONS]           Run co-evolution training loop
    agent0 train [OPTIONS]         Run RL training
    agent0 benchmark [OPTIONS]     Run benchmark evaluation
    agent0 status                  Check system status
    agent0 chat [OPTIONS]          Interactive chat with agent
    agent0 solve PROBLEM           Solve a single problem

Examples:
    agent0 run --steps 100 --domains math logic
    agent0 train --epochs 10 --use-grpo
    agent0 benchmark --type math --limit 50
    agent0 status
    agent0 solve "What is 2x + 5 = 15?"
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure agent0 is importable
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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
        """Disable colors (for non-TTY output)."""
        cls.HEADER = cls.BLUE = cls.CYAN = cls.GREEN = ''
        cls.YELLOW = cls.RED = cls.ENDC = cls.BOLD = cls.DIM = ''


# Disable colors if not a TTY
if not sys.stdout.isatty():
    Colors.disable()


def print_banner():
    """Print Agent0 banner."""
    banner = f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════╗
║  {Colors.BOLD}Agent0{Colors.ENDC}{Colors.CYAN} - Self-Evolving AI Agents                        ║
║  {Colors.DIM}Dual-agent co-evolution with tool-integrated reasoning{Colors.ENDC}{Colors.CYAN}   ║
╚═══════════════════════════════════════════════════════════╝{Colors.ENDC}
"""
    print(banner)


def print_status(label: str, value: str, color: str = Colors.GREEN):
    """Print a status line."""
    print(f"  {Colors.DIM}{label}:{Colors.ENDC} {color}{value}{Colors.ENDC}")


def print_section(title: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}▸ {title}{Colors.ENDC}")


def print_success(msg: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.ENDC} {msg}")


def print_error(msg: str):
    """Print error message."""
    print(f"{Colors.RED}✗{Colors.ENDC} {msg}", file=sys.stderr)


def print_warning(msg: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.ENDC} {msg}")


def print_info(msg: str):
    """Print info message."""
    print(f"{Colors.CYAN}ℹ{Colors.ENDC} {msg}")


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    import yaml
    with config_path.open('r') as f:
        return yaml.safe_load(f)


def check_ollama_connection(host: str = "http://127.0.0.1:11434") -> tuple[bool, List[str]]:
    """Check Ollama connection and return available models."""
    try:
        import requests
        response = requests.get(f"{host}/api/tags", timeout=5)
        if response.status_code == 200:
            models = [m.get('name', 'unknown') for m in response.json().get('models', [])]
            return True, models
        return False, []
    except Exception:
        return False, []


# ============================================================================
# Command: status
# ============================================================================

def cmd_status(args):
    """Check system status and configuration."""
    print_banner()
    print_section("System Status")

    # Check Ollama
    connected, models = check_ollama_connection()
    if connected:
        print_status("Ollama", f"Connected ({len(models)} models)", Colors.GREEN)
        if args.verbose and models:
            for m in models[:5]:
                print(f"           {Colors.DIM}• {m}{Colors.ENDC}")
            if len(models) > 5:
                print(f"           {Colors.DIM}... and {len(models)-5} more{Colors.ENDC}")
    else:
        print_status("Ollama", "Not connected", Colors.RED)
        print_warning("Start Ollama with: ollama serve")

    # Check config
    config_path = Path(args.config)
    if config_path.exists():
        print_status("Config", str(config_path), Colors.GREEN)
        config = load_config(config_path)

        if args.verbose:
            print_section("Configuration")
            print_status("Teacher Model", config['models']['teacher']['model'])
            print_status("Student Model", config['models']['student']['model'])

            curriculum = config.get('curriculum', {})
            print_status("Frontier Mode", "Enabled" if curriculum.get('enable_frontier', True) else "Disabled")
            print_status("Target Success", f"{curriculum.get('target_success', 0.5):.0%}")
    else:
        print_status("Config", "Not found", Colors.RED)

    # Check directories
    print_section("Directories")
    dirs = [
        ("Runs", "./runs"),
        ("Checkpoints", "./checkpoints"),
        ("Data", "./data"),
        ("Sandbox", "./sandbox"),
    ]
    for name, path in dirs:
        exists = Path(path).exists()
        print_status(name, path, Colors.GREEN if exists else Colors.DIM)

    print()


# ============================================================================
# Command: run
# ============================================================================

def cmd_run(args):
    """Run co-evolution training loop."""
    print_banner()

    # Setup logging
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    logger = logging.getLogger(__name__)

    # Load config
    config = load_config(Path(args.config))

    # Apply CLI overrides
    if args.verify:
        config.setdefault("verification", {})["enable"] = True

    if args.no_frontier:
        config.setdefault("curriculum", {})["enable_frontier"] = False

    if args.domains:
        config.setdefault("curriculum", {})["domains"] = args.domains

    # Check Ollama
    connected, models = check_ollama_connection()
    if not connected:
        print_error("Ollama not connected. Start with: ollama serve")
        if not args.force:
            sys.exit(1)
        print_warning("Continuing anyway (--force)")

    # Print config summary
    print_section("Configuration")
    print_status("Steps", str(args.steps))
    print_status("Teacher", config['models']['teacher']['model'])
    print_status("Student", config['models']['student']['model'])
    print_status("Domains", ", ".join(config.get('curriculum', {}).get('domains', ['math'])))
    print_status("Verification", "Enabled" if config.get('verification', {}).get('enable') else "Disabled")

    # Initialize coordinator
    print_section("Initializing")
    from agent0.loop.coordinator import Coordinator
    coord = Coordinator(config)
    print_success("Coordinator initialized")

    # Setup signal handler for graceful shutdown
    running = True

    def signal_handler(sig, frame):
        nonlocal running
        print(f"\n{Colors.YELLOW}Received interrupt, finishing current iteration...{Colors.ENDC}")
        running = False

    signal.signal(signal.SIGINT, signal_handler)

    # Run loop
    print_section(f"Running {args.steps} iterations")
    print()

    stats = {
        'successes': 0,
        'failures': 0,
        'total_reward': 0.0,
        'domains': {},
        'start_time': time.time(),
    }

    for i in range(args.steps):
        if not running:
            break

        task_id = f"task-{i:04d}"

        # Progress indicator
        progress = (i + 1) / args.steps
        bar_width = 30
        filled = int(bar_width * progress)
        bar = '█' * filled + '░' * (bar_width - filled)

        print(f"\r{Colors.CYAN}[{bar}]{Colors.ENDC} {i+1}/{args.steps} ", end='', flush=True)

        # Run iteration
        traj = coord.run_once({"next_task_id": task_id})

        if traj:
            domain = traj.task.domain
            if domain not in stats['domains']:
                stats['domains'][domain] = {'success': 0, 'total': 0}

            stats['domains'][domain]['total'] += 1
            stats['total_reward'] += traj.reward.get('total', 0.0)

            if traj.success:
                stats['successes'] += 1
                stats['domains'][domain]['success'] += 1
                status = f"{Colors.GREEN}✓{Colors.ENDC}"
            else:
                stats['failures'] += 1
                status = f"{Colors.RED}✗{Colors.ENDC}"

            if args.verbose:
                print(f"\r{Colors.DIM}[{i+1}]{Colors.ENDC} {status} {domain}: {traj.task.prompt[:50]}...")
        else:
            stats['failures'] += 1
            if args.verbose:
                print(f"\r{Colors.DIM}[{i+1}]{Colors.ENDC} {Colors.RED}✗{Colors.ENDC} Failed")

    # Final summary
    elapsed = time.time() - stats['start_time']
    total = stats['successes'] + stats['failures']

    print(f"\r{' ' * 60}\r", end='')  # Clear progress bar
    print_section("Results")
    print_status("Total", f"{total} iterations in {elapsed:.1f}s")
    print_status("Success Rate", f"{stats['successes']}/{total} ({stats['successes']/total:.1%})" if total > 0 else "N/A")
    print_status("Avg Reward", f"{stats['total_reward']/total:.3f}" if total > 0 else "N/A")

    if stats['domains']:
        print_section("Per-Domain")
        for domain, d_stats in stats['domains'].items():
            rate = d_stats['success'] / d_stats['total'] if d_stats['total'] > 0 else 0
            color = Colors.GREEN if rate >= 0.5 else Colors.YELLOW if rate >= 0.3 else Colors.RED
            print_status(domain.capitalize(), f"{d_stats['success']}/{d_stats['total']} ({rate:.0%})", color)

    print_success(f"Trajectories saved to: {config['logging']['base_dir']}/trajectories.jsonl")
    print()


# ============================================================================
# Command: train
# ============================================================================

def cmd_train(args):
    """Run RL training."""
    print_banner()
    print_section("RL Training")

    # Import training modules
    from agent0.training.rl_trainer import RLConfig, PPOTrainer, DualAgentRLTrainer

    # Load config
    config = load_config(Path(args.config))

    # Create RL config
    rl_config = RLConfig(
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        use_grpo=args.use_grpo,
        clip_epsilon=args.clip_epsilon,
        gamma=args.gamma,
        save_every=args.save_every,
        output_dir=args.output_dir,
    )

    print_status("Epochs", str(args.epochs))
    print_status("Steps/Epoch", str(args.steps_per_epoch))
    print_status("Algorithm", "GRPO" if args.use_grpo else "PPO")
    print_status("Mode", "Single-Agent" if args.single_agent else "Dual-Agent")
    print_status("Output", args.output_dir)

    # Import and run training
    from agent0.scripts.train_rl import run_training_loop

    print_section("Training")
    run_training_loop(
        config=config,
        rl_config=rl_config,
        num_epochs=args.epochs,
        steps_per_epoch=args.steps_per_epoch,
        use_dual_agent=not args.single_agent,
    )


# ============================================================================
# Command: benchmark
# ============================================================================

def cmd_benchmark(args):
    """Run benchmark evaluation."""
    print_banner()
    print_section("Benchmark Evaluation")

    from agent0.benchmarks import BenchmarkLoader, BenchmarkEvaluator
    from agent0.agents.student import StudentAgent
    from agent0.tasks.schema import TaskSpec

    # Load config and create solver
    config = load_config(Path(args.config))
    student = StudentAgent(config["models"]["student"], tool_config=config.get("tooling", {}))

    def solver(problem: str) -> str:
        task = TaskSpec(task_id="bench", domain="math", prompt=problem, constraints=[], verifier=None)
        traj = student.solve(task)
        return traj.result

    # Load benchmark
    loader = BenchmarkLoader(Path(args.data_dir))

    print_status("Benchmark", args.type)
    print_status("Limit", str(args.limit) if args.limit else "All")

    if args.type.lower() == "math":
        difficulties = args.difficulty.split(",") if args.difficulty else None
        count = loader.load_math(difficulties=difficulties, limit=args.limit)
    elif args.type.lower() == "gsm8k":
        count = loader.load_gsm8k(limit=args.limit)
    else:
        count = loader.load_custom(Path(args.data_dir) / "custom.jsonl", limit=args.limit)

    if count == 0:
        print_error(f"No samples loaded. Check data directory: {args.data_dir}")
        sys.exit(1)

    print_status("Samples", str(count))
    print_section("Running")

    # Run evaluation with progress
    evaluator = BenchmarkEvaluator(output_dir=Path(args.output))
    correct = 0
    total_latency = 0.0

    for i, sample in enumerate(loader.samples):
        progress = (i + 1) / count
        bar_width = 30
        filled = int(bar_width * progress)
        bar = '█' * filled + '░' * (bar_width - filled)

        print(f"\r{Colors.CYAN}[{bar}]{Colors.ENDC} {i+1}/{count} ", end='', flush=True)

        result = evaluator.evaluate_sample(sample, solver)
        total_latency += result.latency_ms

        if result.correct:
            correct += 1

    # Results
    accuracy = correct / count if count > 0 else 0
    avg_latency = total_latency / count if count > 0 else 0

    print(f"\r{' ' * 60}\r", end='')
    print_section("Results")
    print_status("Accuracy", f"{correct}/{count} ({accuracy:.1%})",
                Colors.GREEN if accuracy >= 0.5 else Colors.YELLOW)
    print_status("Avg Latency", f"{avg_latency:.1f}ms")

    # Save results
    from agent0.benchmarks.evaluator import BenchmarkResults
    results = BenchmarkResults(
        benchmark_name=args.type,
        total_samples=count,
        correct=correct,
        accuracy=accuracy,
        avg_latency_ms=avg_latency,
        results=[],
    )
    output_path = evaluator.save_results(results)
    print_success(f"Results saved to: {output_path}")
    print()


# ============================================================================
# Command: solve
# ============================================================================

def cmd_solve(args):
    """Solve a single problem."""
    config = load_config(Path(args.config))

    from agent0.agents.student import StudentAgent
    from agent0.tasks.schema import TaskSpec

    # Check connection
    connected, _ = check_ollama_connection()
    if not connected:
        print_error("Ollama not connected")
        sys.exit(1)

    # Create agent and solve
    student = StudentAgent(config["models"]["student"], tool_config=config.get("tooling", {}))

    task = TaskSpec(
        task_id="cli-task",
        domain=args.domain,
        prompt=args.problem,
        constraints=[],
        verifier=None,
    )

    print(f"{Colors.DIM}Solving...{Colors.ENDC}")
    start = time.time()
    traj = student.solve(task)
    elapsed = time.time() - start

    # Output result
    print(f"\n{Colors.BOLD}Result:{Colors.ENDC} {traj.result}")

    if args.verbose:
        print(f"\n{Colors.DIM}Time: {elapsed:.2f}s")
        print(f"Tools: {len(traj.tool_calls)}")
        for call in traj.tool_calls:
            print(f"  • {call.get('tool', 'unknown')}: {call.get('status', 'unknown')}{Colors.ENDC}")


# ============================================================================
# Command: chat
# ============================================================================

def cmd_monitor(args):
    """Real-time training monitor."""
    from agent0.cli_monitor import Monitor

    monitor = Monitor(Path(args.runs_dir))
    monitor.run(args.refresh)


def cmd_backends(args):
    """Check available LLM backends."""
    print_banner()
    print_section("LLM Backends")

    # Check Ollama
    ollama_available = False
    try:
        import requests
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        ollama_available = response.status_code == 200
    except Exception:
        pass

    # Check Claude CLI
    claude_available = shutil.which("claude") is not None

    # Check OpenAI
    openai_available = bool(os.environ.get("OPENAI_API_KEY"))

    # Check Gemini
    gemini_available = bool(os.environ.get("GOOGLE_API_KEY"))

    backends = {
        "Ollama": ollama_available,
        "Claude CLI": claude_available,
        "OpenAI": openai_available,
        "Gemini": gemini_available,
    }

    for name, available in backends.items():
        if available:
            print_status(name, "Available", Colors.GREEN)
        else:
            print_status(name, "Not available", Colors.DIM)

    if args.test:
        print_section("Testing Backends")
        print_warning("Use --test with full install (pip install -e .)")

    print_section("Configuration")
    print_info("Set these environment variables to enable backends:")
    print(f"  {Colors.DIM}OPENAI_API_KEY{Colors.ENDC}  - For OpenAI")
    print(f"  {Colors.DIM}GOOGLE_API_KEY{Colors.ENDC}  - For Gemini")
    print(f"  {Colors.DIM}ollama serve{Colors.ENDC}    - For Ollama (local)")
    print(f"  {Colors.DIM}claude (CLI){Colors.ENDC}    - Install Claude CLI")
    print()


def cmd_mcp(args):
    """Start MCP server."""
    print(f"Starting Agent0 MCP server ({args.transport} transport)...", file=sys.stderr)

    from agent0.mcp_server import main as mcp_main
    import sys
    sys.argv = ['mcp_server', '--transport', args.transport]
    mcp_main()


def cmd_chat(args):
    """Interactive chat mode."""
    print_banner()

    config = load_config(Path(args.config))

    from agent0.agents.multi_turn import MultiTurnAgent
    from agent0.tasks.schema import TaskSpec

    # Check connection
    connected, _ = check_ollama_connection()
    if not connected:
        print_error("Ollama not connected")
        sys.exit(1)

    agent = MultiTurnAgent(
        config["models"]["student"],
        max_turns=args.max_turns,
        enable_reflection=not args.no_reflection,
    )

    conv = agent.start_conversation("chat-session")

    print(f"{Colors.DIM}Type 'quit' or 'exit' to end, 'clear' to reset{Colors.ENDC}\n")

    while True:
        try:
            user_input = input(f"{Colors.CYAN}You:{Colors.ENDC} ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print(f"\n{Colors.DIM}Goodbye!{Colors.ENDC}")
                break

            if user_input.lower() == 'clear':
                conv = agent.start_conversation("chat-session")
                print(f"{Colors.DIM}Conversation cleared{Colors.ENDC}\n")
                continue

            response = agent.generate_response(conv, user_input)
            print(f"\n{Colors.GREEN}Agent:{Colors.ENDC} {response}\n")

        except KeyboardInterrupt:
            print(f"\n{Colors.DIM}Goodbye!{Colors.ENDC}")
            break
        except EOFError:
            break


# ============================================================================
# Main entry point
# ============================================================================

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Agent0 - Self-Evolving AI Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  run        Run co-evolution training loop
  train      Run RL training with PPO/GRPO
  benchmark  Run benchmark evaluation (MATH, GSM8K)
  status     Check system status
  solve      Solve a single problem
  chat       Interactive chat mode

Examples:
  agent0 status
  agent0 run --steps 100
  agent0 benchmark --type math --limit 50
  agent0 solve "What is 2x + 5 = 15?"
  agent0 chat
        """
    )

    parser.add_argument('--config', type=str, default='agent0/configs/3070ti.yaml',
                       help='Path to config file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # status command
    status_parser = subparsers.add_parser('status', help='Check system status')

    # run command
    run_parser = subparsers.add_parser('run', help='Run co-evolution loop')
    run_parser.add_argument('--steps', type=int, default=10, help='Number of iterations')
    run_parser.add_argument('--domains', nargs='+', choices=['math', 'logic', 'code'],
                           help='Domains to train on')
    run_parser.add_argument('--verify', action='store_true', help='Enable self-verification')
    run_parser.add_argument('--no-frontier', action='store_true', help='Disable frontier mode')
    run_parser.add_argument('--force', action='store_true', help='Run even if Ollama not connected')
    run_parser.add_argument('--log-level', default='WARNING',
                           choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])

    # train command
    train_parser = subparsers.add_parser('train', help='Run RL training')
    train_parser.add_argument('--epochs', type=int, default=10, help='Number of epochs')
    train_parser.add_argument('--steps-per-epoch', type=int, default=50, help='Steps per epoch')
    train_parser.add_argument('--batch-size', type=int, default=8, help='Batch size')
    train_parser.add_argument('--learning-rate', type=float, default=1e-5, help='Learning rate')
    train_parser.add_argument('--use-grpo', action='store_true', help='Use GRPO instead of PPO')
    train_parser.add_argument('--clip-epsilon', type=float, default=0.2, help='PPO clip epsilon')
    train_parser.add_argument('--gamma', type=float, default=0.99, help='Discount factor')
    train_parser.add_argument('--single-agent', action='store_true', help='Single-agent training')
    train_parser.add_argument('--output-dir', type=str, default='./checkpoints', help='Output directory')
    train_parser.add_argument('--save-every', type=int, default=10, help='Save every N epochs')

    # benchmark command
    bench_parser = subparsers.add_parser('benchmark', help='Run benchmark evaluation')
    bench_parser.add_argument('--type', choices=['math', 'gsm8k', 'custom'], default='math',
                             help='Benchmark type')
    bench_parser.add_argument('--limit', type=int, default=50, help='Max samples')
    bench_parser.add_argument('--difficulty', type=str, help='Difficulty filter (e.g., "3,4,5")')
    bench_parser.add_argument('--data-dir', type=str, default='./data/benchmarks',
                             help='Data directory')
    bench_parser.add_argument('--output', type=str, default='./eval_results',
                             help='Output directory')

    # solve command
    solve_parser = subparsers.add_parser('solve', help='Solve a single problem')
    solve_parser.add_argument('problem', type=str, help='Problem to solve')
    solve_parser.add_argument('--domain', choices=['math', 'logic', 'code'], default='math',
                             help='Problem domain')

    # chat command
    chat_parser = subparsers.add_parser('chat', help='Interactive chat mode')
    chat_parser.add_argument('--max-turns', type=int, default=10, help='Max conversation turns')
    chat_parser.add_argument('--no-reflection', action='store_true', help='Disable reflection')

    # monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Real-time training monitor')
    monitor_parser.add_argument('--runs-dir', type=str, default='./runs',
                               help='Directory containing training runs')
    monitor_parser.add_argument('--refresh', type=float, default=1.0,
                               help='Refresh rate in seconds')

    # backends command
    backends_parser = subparsers.add_parser('backends', help='Check available LLM backends')
    backends_parser.add_argument('--test', action='store_true',
                                help='Test each backend with a simple prompt')

    # mcp command
    mcp_parser = subparsers.add_parser('mcp', help='Start MCP server')
    mcp_parser.add_argument('--transport', choices=['stdio'], default='stdio',
                           help='Transport type')

    args = parser.parse_args()

    if args.no_color:
        Colors.disable()

    # Dispatch to command handler
    if args.command == 'status':
        cmd_status(args)
    elif args.command == 'run':
        cmd_run(args)
    elif args.command == 'train':
        cmd_train(args)
    elif args.command == 'benchmark':
        cmd_benchmark(args)
    elif args.command == 'solve':
        cmd_solve(args)
    elif args.command == 'chat':
        cmd_chat(args)
    elif args.command == 'monitor':
        cmd_monitor(args)
    elif args.command == 'backends':
        cmd_backends(args)
    elif args.command == 'mcp':
        cmd_mcp(args)
    else:
        # Default: show status
        parser.print_help()


if __name__ == '__main__':
    main()
