import argparse
import sys
from pathlib import Path

# Ensure repository root is on sys.path when executed directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent0.config import load_config
from agent0.loop import run_round


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local Agent0 round.")
    parser.add_argument("--config", type=Path, default=Path("runs/default_config.yaml"))
    args = parser.parse_args()

    cfg = load_config(args.config)
    attempts = run_round(cfg)

    for attempt in attempts:
        passed = getattr(attempt, "evaluation", None).passed if getattr(attempt, "evaluation", None) else False
        score = getattr(attempt, "evaluation", None).score if getattr(attempt, "evaluation", None) else 0.0
        print(f"Task {attempt.task.task_id}: passed={passed} score={score}")

    log_path = Path(cfg.logs_dir)
    print(f"Logs written under: {log_path}")


if __name__ == "__main__":
    main()
