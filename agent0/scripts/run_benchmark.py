#!/usr/bin/env python3
"""
CLI script for running Agent0 benchmarks.

Usage:
    python -m agent0.scripts.run_benchmark --benchmark math --limit 100
    python -m agent0.scripts.run_benchmark --benchmark gsm8k --config configs/3070ti.yaml
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent0.benchmarks import BenchmarkLoader, BenchmarkEvaluator
from agent0.agents.student import StudentAgent
from agent0.config import load_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_solver(config: dict) -> callable:
    """Create solver function from config."""
    student = StudentAgent(config["models"]["student"], tool_config=config.get("tooling", {}))

    def solver(problem: str):
        # Create minimal task spec
        from agent0.tasks.schema import TaskSpec
        task = TaskSpec(
            task_id="bench_task",
            domain="math",
            prompt=problem,
            constraints=[],
            verifier=None,
        )
        trajectory = student.solve(task)
        return trajectory.result

    return solver


def main():
    parser = argparse.ArgumentParser(description="Run Agent0 benchmarks")

    parser.add_argument(
        "--benchmark",
        choices=["math", "gsm8k", "custom"],
        default="math",
        help="Benchmark to run"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="agent0/configs/3070ti.yaml",
        help="Path to config file"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="./data/benchmarks",
        help="Directory containing benchmark data"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of samples to evaluate"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./eval_results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--difficulty",
        type=str,
        default=None,
        help="Filter by difficulty level (e.g., '3,4,5')"
    )
    parser.add_argument(
        "--subject",
        type=str,
        default=None,
        help="Filter by subject (e.g., 'algebra,geometry')"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    config = load_config(config_path)

    # Initialize loader
    loader = BenchmarkLoader(Path(args.data_dir))

    # Load benchmark
    if args.benchmark == "math":
        difficulties = args.difficulty.split(",") if args.difficulty else None
        subjects = args.subject.split(",") if args.subject else None
        count = loader.load_math(difficulties=difficulties, limit=args.limit)
        if subjects:
            loader.samples = [s for s in loader.samples if s.subject in subjects]
    elif args.benchmark == "gsm8k":
        count = loader.load_gsm8k(limit=args.limit)
    else:
        custom_path = Path(args.data_dir) / "custom.jsonl"
        if not custom_path.exists():
            logger.error(f"Custom benchmark file not found: {custom_path}")
            sys.exit(1)
        count = loader.load_custom(custom_path, limit=args.limit)

    if len(loader) == 0:
        logger.error("No samples loaded. Check data directory and benchmark name.")
        sys.exit(1)

    logger.info(f"Loaded {len(loader)} samples")
    logger.info(f"Summary: {json.dumps(loader.summary(), indent=2)}")

    # Create solver
    solver = create_solver(config)

    # Run evaluation
    evaluator = BenchmarkEvaluator(output_dir=Path(args.output))

    def progress_callback(current, total):
        if current % 10 == 0:
            print(f"\rProgress: {current}/{total} ({current/total*100:.1f}%)", end="", flush=True)

    print(f"\nRunning {args.benchmark} benchmark...")
    results = evaluator.evaluate_benchmark(
        loader,
        solver,
        benchmark_name=args.benchmark,
        limit=args.limit,
        progress_callback=progress_callback,
    )

    print("\n")  # New line after progress

    # Save and display results
    output_path = evaluator.save_results(results)

    print("\n" + "=" * 50)
    print(f"BENCHMARK RESULTS: {args.benchmark.upper()}")
    print("=" * 50)
    print(f"Total Samples:  {results.total_samples}")
    print(f"Correct:        {results.correct}")
    print(f"Accuracy:       {results.accuracy:.2%}")
    print(f"Avg Latency:    {results.avg_latency_ms:.1f}ms")
    print()

    if results.by_difficulty:
        print("By Difficulty:")
        for diff, stats in sorted(results.by_difficulty.items()):
            print(f"  Level {diff}: {stats['accuracy']:.2%} ({stats['total']} samples)")
        print()

    if results.by_subject:
        print("By Subject:")
        for subj, stats in sorted(results.by_subject.items(), key=lambda x: -x[1]['accuracy']):
            print(f"  {subj}: {stats['accuracy']:.2%} ({stats['total']} samples)")
        print()

    print(f"Results saved to: {output_path}")
    print("=" * 50)


if __name__ == "__main__":
    main()
