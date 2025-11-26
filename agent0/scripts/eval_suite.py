import argparse
import logging
from pathlib import Path
from typing import List

import yaml
from datasets import load_dataset  # type: ignore

from agent0.agents.student import StudentAgent
from agent0.logging.setup import configure_logging
from agent0.tasks.schema import TaskSpec, VerifierSpec
from agent0.tasks.verifier import verify


def load_gsm8k(limit: int) -> List[TaskSpec]:
    ds = load_dataset("gsm8k", "main", split="test")
    tasks = []
    for idx, row in enumerate(ds):
        if idx >= limit:
            break
        prompt = row["question"]
        answer = row["answer"].split("####")[-1].strip()
        tasks.append(
            TaskSpec(
                task_id=f"gsm8k-{idx}",
                domain="math",
                prompt=prompt,
                constraints=["provide numeric answer"],
                verifier=VerifierSpec(kind="expected_number", spec={"answer": answer}),
                seed=None,
            )
        )
    return tasks


def load_arc(split_name: str, limit: int, difficulty: str) -> List[TaskSpec]:
    ds = load_dataset("ai2_arc", split=split_name)
    tasks = []
    for idx, row in enumerate(ds):
        if idx >= limit:
            break
        question = row["question"]
        choices = row["choices"]["text"]
        labels = row["choices"]["label"]
        answer = row["answerKey"]
        prompt = f"{question}\nChoices:\n" + "\n".join(f"{l}) {c}" for l, c in zip(labels, choices))
        tasks.append(
            TaskSpec(
                task_id=f"arc-{difficulty}-{idx}",
                domain="logic",
                prompt=prompt,
                constraints=["answer with the correct option letter"],
                verifier=VerifierSpec(kind="contains", spec={"text": answer}),
                seed=None,
            )
        )
    return tasks


def evaluate(tasks: List[TaskSpec], student: StudentAgent, logger: logging.Logger) -> float:
    correct = 0
    for task in tasks:
        traj = student.solve(task)
        verdict = verify(task, traj.result)
        ok = verdict.get("status") == "pass"
        correct += int(ok)
        logger.info("Task %s => %s (ok=%s)", task.task_id, traj.result, ok)
    return 100 * correct / max(1, len(tasks))


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate on standard benchmarks (GSM8K, ARC).")
    parser.add_argument("--config", type=Path, default=Path("agent0/configs/3070ti.yaml"))
    parser.add_argument("--suites", type=str, default="gsm8k,arc_easy,arc_challenge", help="comma-separated suites")
    parser.add_argument("--limit", type=int, default=20, help="samples per suite")
    args = parser.parse_args()

    with args.config.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger = configure_logging(Path(config["logging"]["base_dir"]), level=logging.INFO)
    student = StudentAgent(config["models"]["student"], tool_config=config.get("tooling", {}))

    suites = [s.strip() for s in args.suites.split(",") if s.strip()]
    for suite in suites:
        if suite == "gsm8k":
            tasks = load_gsm8k(args.limit)
        elif suite == "arc_easy":
            tasks = load_arc("train", args.limit, "easy")
        elif suite == "arc_challenge":
            tasks = load_arc("test", args.limit, "challenge")
        else:
            logger.warning("Unknown suite: %s", suite)
            continue
        acc = evaluate(tasks, student, logger)
        logger.info("Suite %s accuracy: %.2f%% on %d samples", suite, acc, len(tasks))


if __name__ == "__main__":
    main()
