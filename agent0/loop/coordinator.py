from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from agent0.agents.student import StudentAgent
from agent0.agents.teacher import TeacherAgent
from agent0.agents.uncertainty import UncertaintyEstimator
from agent0.rewards.calculator import RewardCalculator, RewardWeights
from agent0.memory.embedder import create_embedder, cosine_similarity
from agent0.memory.faiss_store import FaissIndex
from agent0.loop.curriculum_scheduler import CurriculumScheduler
from agent0.tasks.schema import Trajectory
from agent0.tasks.verifier import verify


class Coordinator:
    """Runs the co-evolution loop between teacher and student."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.teacher = TeacherAgent(config["models"]["teacher"])
        self.student = StudentAgent(config["models"]["student"], tool_config=config.get("tooling", {}))
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
            data = {
                "task": trajectory.task.__dict__,
                "messages": trajectory.messages,
                "tool_calls": trajectory.tool_calls,
                "result": trajectory.result,
                "success": trajectory.success,
                "reward": trajectory.reward,
                "metrics": trajectory.metrics,
            }
            f.write(json.dumps(data) + "\n")

    def run_once(self, student_signal: Dict[str, Any]) -> Trajectory:
        signal = {**self.scheduler.next_signal(), **student_signal}
        task = self.teacher.generate_task(signal)
        traj = self.student.solve(task)

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
        return traj
