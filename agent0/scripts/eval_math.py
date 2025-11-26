import argparse
import json
from pathlib import Path
from typing import List

import yaml

from agent0.agents.student import StudentAgent
from agent0.logging.setup import configure_logging
from agent0.tasks.schema import TaskSpec, VerifierSpec
from agent0.tasks.verifier import verify


def load_math_samples(path: Path) -> List[TaskSpec]:
    tasks = []
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            obj = json.loads(line)
            prompt = obj["question"]
            answer = obj["answer"]
            verifier = VerifierSpec(kind="expected_number", spec={"answer": str(answer)})
            tasks.append(
                TaskSpec(
                    task_id=f"eval-{idx}",
                    domain="math",
                    prompt=prompt,
                    constraints=["numeric answer"],
                    verifier=verifier,
                    seed=None,
                )
            )
    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple math eval.")
    parser.add_argument("--config", type=Path, default=Path("agent0/configs/3070ti.yaml"))
    parser.add_argument("--data", type=Path, required=True, help="Path to JSONL with question/answer")
    args = parser.parse_args()

    with args.config.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger = configure_logging(Path(config["logging"]["base_dir"]))
    student = StudentAgent(config["models"]["student"], tool_config=config.get("tooling", {}))

    tasks = load_math_samples(args.data)
    correct = 0
    for task in tasks:
        traj = student.solve(task)
        verdict = verify(task, traj.result)
        ok = verdict.get("status") == "pass"
        correct += int(ok)
        logger.info("Task %s => %s (answer=%s)", task.task_id, traj.result, ok)

    logger.info("Accuracy: %.2f%% (%d/%d)", 100 * correct / max(1, len(tasks)), correct, len(tasks))


if __name__ == "__main__":
    main()
