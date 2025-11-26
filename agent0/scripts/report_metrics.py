import argparse
import json
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate trajectory metrics.")
    parser.add_argument("--runs", type=Path, default=Path("runs/trajectories.jsonl"))
    args = parser.parse_args()

    totals = defaultdict(int)
    rewards = defaultdict(float)
    count = 0
    with args.runs.open("r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            count += 1
            domain = obj["task"].get("domain", "unknown")
            success = obj.get("success", False)
            totals[domain] += int(success)
            rewards[domain] += obj.get("reward", {}).get("total", 0.0)
    print(f"Total trajectories: {count}")
    for domain, succ in totals.items():
        avg_reward = rewards[domain] / max(1, count)
        print(f"{domain}: success={succ} avg_reward={avg_reward:.3f}")


if __name__ == "__main__":
    main()
