from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import json
from dataclasses import asdict
from agent0.agents.student import StudentAgent
from agent0.agents.teacher import TeacherAgent
from agent0.agents.uncertainty import UncertaintyEstimator
from agent0.rewards.calculator import RewardCalculator, RewardWeights
from agent0.memory.embedder import create_embedder, cosine_similarity
from agent0.memory.faiss_store import FaissIndex
from agent0.loop.curriculum_scheduler import CurriculumScheduler
from agent0.validation.input_validator import InputValidator
from agent0.tasks.schema import Trajectory
from agent0.tasks.verifier import verify


class Coordinator:
    """Runs the co-evolution loop between teacher and student."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.teacher = TeacherAgent(config["models"]["teacher"])
        self.student = StudentAgent(config["models"]["student"], tool_config=config.get("tooling", {}))
        self.validator = InputValidator()
        weights = RewardWeights(
            weight_uncertainty=config["rewards"]["weight_uncertainty"],
            weight_tool_use=config["rewards"]["weight_tool_use"],
            weight_novelty=config["rewards"]["weight_novelty"],
            target_success_rate=config["rewards"]["target_success_rate"],
            repetition_similarity_threshold=config["rewards"]["repetition_similarity_threshold"],
        )
        self.reward_calc = RewardCalculator(weights)
        self.run_dir = Path(config["logging"]["base_dir"])
        self.run_dir.mkdir(parents=True, exist_ok=True)
        embed_conf = config.get("embedding", {})
        self.embedder = create_embedder(
            prefer_transformer=embed_conf.get("use_transformer", True),
            model_name=embed_conf.get("model_name", "all-MiniLM-L6-v2"),
        )
        self.recent_embeddings = []
        self.faiss = None
        try:
            dim = len(self.embedder.embed("dimension_probe"))
            self.faiss = FaissIndex(dim)
        except Exception:
            self.faiss = None
        self.uncertainty = UncertaintyEstimator(config["models"]["student"])
        self.scheduler = CurriculumScheduler(weights.target_success_rate)

    def _log_trajectory(self, trajectory: Trajectory) -> None:
        out_file = self.run_dir / "trajectories.jsonl"
        with out_file.open("a", encoding="utf-8") as f:
            data = asdict(trajectory)
            f.write(json.dumps(data) + "\n")

    def run_once(self, student_signal: Dict[str, Any]) -> Optional[Trajectory]:
        try:
            self.logger.warning("LOCAL MODE ACTIVE - code executes directly on your machine (no isolation)")
            signal = {**self.scheduler.next_signal(), **student_signal}
            task = self.teacher.generate_task(signal)
            self.logger.info("Generated task: %s", task.prompt[:100])
            validation_errors = self.validator.validate_task(task)
            if validation_errors:
                self.logger.error("Task validation failed: %s", validation_errors)
                return None
            traj = self.student.solve(task)

            if any(call.get("tool") == "python" for call in traj.tool_calls):
                self.logger.warning("Python code executed locally - review ./sandbox for generated files")

            verdict = verify(task, traj.result)
            traj.success = verdict.get("status") == "pass"

            success_prob = self.uncertainty.estimate(task.prompt, traj.result)
            novelty_sig = f"{task.domain}:{hash(task.prompt) % 10_000}"
            emb = self.embedder.embed(task.prompt)
            similarity = 0.0
            if self.faiss:
                similarity = self.faiss.max_similarity(emb)
                self.faiss.add(emb)
            else:
                if self.recent_embeddings:
                    similarity = max(cosine_similarity(emb, e) for e in self.recent_embeddings)
                self.recent_embeddings.append(emb)
                self.recent_embeddings = self.recent_embeddings[-200:]

            reward = self.reward_calc.compute(traj, success_prob, novelty_sig, similarity=similarity)
            traj.reward = reward
            self._log_trajectory(traj)
            self.scheduler.update(traj.success)
            self.logger.info("Task completed: success=%s reward=%.3f", traj.success, reward["total"])
            return traj
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Iteration failed: %s", exc, exc_info=True)
            self.logger.error("Check sandbox directory for any generated files.")
            return None
