#!/usr/bin/env python
"""
Monitor local execution outputs for safety signals.
Reviews generated sandbox code and recent trajectories.
"""

import argparse
import json
from pathlib import Path
from typing import List


def check_sandbox_files(sandbox_dir: Path) -> None:
    print("\n[Sandbox Files]")
    if not sandbox_dir.exists():
        print("No sandbox directory")
        return

    py_files: List[Path] = list(sandbox_dir.glob("*.py"))
    if not py_files:
        print("No Python files generated")
        return

    print(f"Found {len(py_files)} Python files:")
    for file_path in py_files:
        print(f"\n  File: {file_path.name}")
        print(f"  Size: {file_path.stat().st_size} bytes")
        print("  Content preview:")
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines()[:10]:
            print(f"    {line}")
        if len(content.splitlines()) > 10:
            print("    ...")


def check_trajectories(traj_file: Path, last_n: int) -> None:
    print("\n[Recent Trajectories]")
    if not traj_file.exists():
        print("No trajectories file")
        return

    lines = traj_file.read_text(encoding="utf-8").splitlines()
    recent = lines[-last_n:] if len(lines) >= last_n else lines

    print(f"Reviewing last {len(recent)} trajectories:")
    for idx, line in enumerate(recent, 1):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            print(f"  Trajectory {idx}: could not parse JSON")
            continue

        task = data.get("task", {})
        prompt_preview = (task.get("prompt") or "")[:60]
        print(f"\n  Trajectory {idx}:")
        print(f"    Task: {prompt_preview}...")
        print(f"    Success: {data.get('success')}")
        tool_calls = data.get("tool_calls", []) or []
        print(f"    Tools used: {len(tool_calls)}")

        for call in tool_calls:
            tool = call.get("tool", "unknown")
            status = call.get("status", "unknown")
            print(f"      - {tool}: {status}")
            if tool == "python":
                code = call.get("input") or call.get("result", {}).get("stdout", "")
                if code:
                    print(f"        Code: {str(code)[:100]}...")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sandbox", default="./sandbox", help="Sandbox directory")
    parser.add_argument("--trajectories", default="./runs/trajectories.jsonl", help="Trajectories file path")
    parser.add_argument("--last", type=int, default=5, help="Number of trajectories to review")
    args = parser.parse_args()

    print("=" * 60)
    print("LOCAL EXECUTION MONITOR")
    print("=" * 60)

    check_sandbox_files(Path(args.sandbox))
    check_trajectories(Path(args.trajectories), args.last)

    print("\n" + "=" * 60)
    print("Review complete. Inspect any risky code before proceeding.")
    print("=" * 60)


if __name__ == "__main__":
    main()
