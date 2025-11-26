import argparse
import json
import logging
from pathlib import Path

import yaml

from agent0.agents.student import StudentAgent
from agent0.logging.setup import configure_logging
from agent0.tasks.schema import TaskSpec, VerifierSpec
from agent0.tasks.verifier import verify


def load_bench(path: Path, domain: str) -> list[TaskSpec]:
    tasks = []
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            obj = json.loads(line)
            prompt = obj["question"]
            answer = obj.get("answer")
            kind = obj.get("verifier_kind", "expected_number")
            spec = obj.get("verifier_spec", {"answer": str(answer) if answer is not None else ""})
            verifier = VerifierSpec(kind=kind, spec=spec) if answer is not None else None
            tasks.append(
                TaskSpec(
                    task_id=f"bench-{idx}",
                    domain=domain,
                    prompt=prompt,
                    constraints=["provide answer"],
                    verifier=verifier,
                    seed=None,
                )
            )
    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark runner.")
    parser.add_argument("--config", type=Path, default=Path("agent0/configs/3070ti.yaml"))
    parser.add_argument("--data", type=Path, default=Path("benchmarks/math_sample.jsonl"))
    parser.add_argument("--domain", type=str, default="math")
    args = parser.parse_args()

    with args.config.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger = configure_logging(Path(config["logging"]["base_dir"]), level=logging.INFO)
    student = StudentAgent(config["models"]["student"], tool_config=config.get("tooling", {}))
    tasks = load_bench(args.data, args.domain)
    correct = 0
    for task in tasks:
        traj = student.solve(task)
        verdict = verify(task, traj.result)
        ok = verdict.get("status") == "pass"
        correct += int(ok)
        logger.info("Task %s => %s (ok=%s)", task.task_id, traj.result, ok)
    logger.info("Accuracy: %.2f%% (%d/%d)", 100 * correct / max(1, len(tasks)), correct, len(tasks))


if __name__ == "__main__":
    main()
