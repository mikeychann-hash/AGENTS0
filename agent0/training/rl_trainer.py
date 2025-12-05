"""
VeRL-style Reinforcement Learning Trainer for Agent0.

Implements PPO/GRPO-style training for dual-agent co-evolution,
inspired by the original Agent0 paper's VeRL approach.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RLConfig:
    """Configuration for RL training."""
    # Model settings
    model_name: str = "qwen2.5:3b"

    # PPO hyperparameters
    learning_rate: float = 1e-5
    ppo_epochs: int = 4
    clip_epsilon: float = 0.2
    value_loss_coef: float = 0.5
    entropy_coef: float = 0.01
    max_grad_norm: float = 0.5

    # GRPO (Group Relative Policy Optimization) settings
    use_grpo: bool = True
    group_size: int = 4  # Number of samples for relative comparison

    # Training settings
    batch_size: int = 8
    rollout_buffer_size: int = 256
    gamma: float = 0.99  # Discount factor
    gae_lambda: float = 0.95  # GAE lambda

    # Curriculum settings
    curriculum_warmup_steps: int = 100
    difficulty_scale_factor: float = 0.1

    # Checkpointing
    save_every: int = 100
    output_dir: str = "./checkpoints"


@dataclass
class Experience:
    """Single experience from agent interaction."""
    state: str  # Task prompt
    action: str  # Agent response
    reward: float
    value: float  # Estimated value
    log_prob: float  # Log probability of action
    done: bool
    domain: str = "math"
    tool_calls: List[Dict] = field(default_factory=list)


@dataclass
class TrajectoryBatch:
    """Batch of trajectories for training."""
    states: List[str]
    actions: List[str]
    rewards: List[float]
    values: List[float]
    log_probs: List[float]
    advantages: List[float]
    returns: List[float]
    domains: List[str]


class RolloutBuffer:
    """Buffer for storing and processing rollout experiences."""

    def __init__(self, max_size: int = 256):
        self.max_size = max_size
        self.experiences: List[Experience] = []

    def add(self, exp: Experience) -> None:
        """Add experience to buffer."""
        self.experiences.append(exp)
        if len(self.experiences) > self.max_size:
            self.experiences.pop(0)

    def compute_advantages(self, gamma: float = 0.99, gae_lambda: float = 0.95) -> TrajectoryBatch:
        """Compute GAE advantages and returns."""
        if not self.experiences:
            return None

        rewards = [exp.reward for exp in self.experiences]
        values = [exp.value for exp in self.experiences]
        dones = [exp.done for exp in self.experiences]

        # Compute advantages using GAE
        advantages = []
        last_gae = 0.0

        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = 0.0
            else:
                next_value = values[t + 1]

            delta = rewards[t] + gamma * next_value * (1 - int(dones[t])) - values[t]
            last_gae = delta + gamma * gae_lambda * (1 - int(dones[t])) * last_gae
            advantages.insert(0, last_gae)

        # Compute returns
        returns = [adv + val for adv, val in zip(advantages, values)]

        # Normalize advantages
        adv_mean = sum(advantages) / len(advantages)
        adv_std = math.sqrt(sum((a - adv_mean) ** 2 for a in advantages) / len(advantages))
        if adv_std > 1e-8:
            advantages = [(a - adv_mean) / adv_std for a in advantages]

        return TrajectoryBatch(
            states=[exp.state for exp in self.experiences],
            actions=[exp.action for exp in self.experiences],
            rewards=rewards,
            values=values,
            log_probs=[exp.log_prob for exp in self.experiences],
            advantages=advantages,
            returns=returns,
            domains=[exp.domain for exp in self.experiences],
        )

    def clear(self) -> None:
        """Clear the buffer."""
        self.experiences = []

    def __len__(self) -> int:
        return len(self.experiences)


class PPOTrainer:
    """
    PPO-style trainer for Agent0.

    Implements the core PPO algorithm with optional GRPO extensions
    for group-relative policy optimization.
    """

    def __init__(self, config: RLConfig):
        self.config = config
        self.buffer = RolloutBuffer(config.rollout_buffer_size)
        self.step = 0
        self.best_reward = float('-inf')

        # Training statistics
        self.stats = {
            'policy_loss': [],
            'value_loss': [],
            'entropy': [],
            'mean_reward': [],
            'mean_advantage': [],
        }

    def compute_ppo_loss(
        self,
        old_log_probs: List[float],
        new_log_probs: List[float],
        advantages: List[float],
    ) -> float:
        """Compute clipped PPO policy loss."""
        total_loss = 0.0

        for old_lp, new_lp, adv in zip(old_log_probs, new_log_probs, advantages):
            ratio = math.exp(new_lp - old_lp)
            clipped_ratio = max(min(ratio, 1 + self.config.clip_epsilon), 1 - self.config.clip_epsilon)

            # Clipped surrogate objective
            loss = -min(ratio * adv, clipped_ratio * adv)
            total_loss += loss

        return total_loss / len(old_log_probs) if old_log_probs else 0.0

    def compute_grpo_loss(
        self,
        group_log_probs: List[List[float]],
        group_rewards: List[List[float]],
    ) -> float:
        """
        Compute GRPO (Group Relative Policy Optimization) loss.

        GRPO compares multiple responses within a group and uses
        relative rankings rather than absolute rewards.
        """
        if not group_log_probs or not group_rewards:
            return 0.0

        total_loss = 0.0

        for log_probs, rewards in zip(group_log_probs, group_rewards):
            if len(rewards) < 2:
                continue

            # Compute relative advantages within group
            mean_reward = sum(rewards) / len(rewards)
            std_reward = math.sqrt(sum((r - mean_reward) ** 2 for r in rewards) / len(rewards))

            if std_reward < 1e-8:
                continue

            # Normalize rewards within group
            normalized = [(r - mean_reward) / std_reward for r in rewards]

            # GRPO loss: weighted by normalized reward
            for lp, norm_r in zip(log_probs, normalized):
                total_loss -= lp * norm_r

        return total_loss / len(group_log_probs) if group_log_probs else 0.0

    def collect_experience(
        self,
        state: str,
        action: str,
        reward: float,
        value: float,
        log_prob: float,
        done: bool,
        domain: str = "math",
        tool_calls: Optional[List[Dict]] = None,
    ) -> None:
        """Collect a single experience."""
        exp = Experience(
            state=state,
            action=action,
            reward=reward,
            value=value,
            log_prob=log_prob,
            done=done,
            domain=domain,
            tool_calls=tool_calls or [],
        )
        self.buffer.add(exp)

    def train_step(self, get_new_log_prob_fn=None) -> Dict[str, float]:
        """
        Perform a single training step.

        Args:
            get_new_log_prob_fn: Optional function to get new log probs
                                 for policy gradient updates

        Returns:
            Dictionary of training metrics
        """
        if len(self.buffer) < self.config.batch_size:
            return {}

        # Compute advantages
        batch = self.buffer.compute_advantages(
            gamma=self.config.gamma,
            gae_lambda=self.config.gae_lambda,
        )

        if batch is None:
            return {}

        self.step += 1
        metrics = {}

        # Compute losses
        if self.config.use_grpo and len(batch.rewards) >= self.config.group_size:
            # Group samples for GRPO
            groups_lp = []
            groups_r = []

            for i in range(0, len(batch.rewards), self.config.group_size):
                end = min(i + self.config.group_size, len(batch.rewards))
                groups_lp.append(batch.log_probs[i:end])
                groups_r.append(batch.rewards[i:end])

            policy_loss = self.compute_grpo_loss(groups_lp, groups_r)
            metrics['grpo_loss'] = policy_loss
        else:
            # Standard PPO loss
            new_log_probs = batch.log_probs  # Would need model forward pass
            policy_loss = self.compute_ppo_loss(
                batch.log_probs,
                new_log_probs,
                batch.advantages,
            )

        # Value loss (MSE)
        value_loss = sum(
            (ret - val) ** 2 for ret, val in zip(batch.returns, batch.values)
        ) / len(batch.values)

        # Entropy bonus (placeholder - needs actual entropy computation)
        entropy = 0.0

        # Total loss
        total_loss = (
            policy_loss +
            self.config.value_loss_coef * value_loss -
            self.config.entropy_coef * entropy
        )

        # Update statistics
        mean_reward = sum(batch.rewards) / len(batch.rewards)
        mean_advantage = sum(batch.advantages) / len(batch.advantages)

        self.stats['policy_loss'].append(policy_loss)
        self.stats['value_loss'].append(value_loss)
        self.stats['entropy'].append(entropy)
        self.stats['mean_reward'].append(mean_reward)
        self.stats['mean_advantage'].append(mean_advantage)

        metrics.update({
            'step': self.step,
            'policy_loss': policy_loss,
            'value_loss': value_loss,
            'total_loss': total_loss,
            'mean_reward': mean_reward,
            'mean_advantage': mean_advantage,
            'buffer_size': len(self.buffer),
        })

        # Check for best model
        if mean_reward > self.best_reward:
            self.best_reward = mean_reward
            metrics['is_best'] = True

        # Clear buffer after training
        if self.step % self.config.ppo_epochs == 0:
            self.buffer.clear()

        logger.info(
            f"RL Step {self.step}: policy_loss={policy_loss:.4f}, "
            f"value_loss={value_loss:.4f}, mean_reward={mean_reward:.4f}"
        )

        return metrics

    def save_checkpoint(self, path: Optional[Path] = None) -> Path:
        """Save training checkpoint."""
        if path is None:
            path = Path(self.config.output_dir) / f"checkpoint_{self.step}.json"

        path.parent.mkdir(parents=True, exist_ok=True)

        checkpoint = {
            'step': self.step,
            'best_reward': self.best_reward,
            'config': {
                'learning_rate': self.config.learning_rate,
                'ppo_epochs': self.config.ppo_epochs,
                'clip_epsilon': self.config.clip_epsilon,
                'use_grpo': self.config.use_grpo,
            },
            'stats': {k: v[-100:] for k, v in self.stats.items()},  # Last 100
        }

        with path.open('w') as f:
            json.dump(checkpoint, f, indent=2)

        logger.info(f"Saved checkpoint to {path}")
        return path

    def load_checkpoint(self, path: Path) -> None:
        """Load training checkpoint."""
        with path.open('r') as f:
            checkpoint = json.load(f)

        self.step = checkpoint['step']
        self.best_reward = checkpoint['best_reward']
        self.stats = checkpoint.get('stats', self.stats)

        logger.info(f"Loaded checkpoint from {path} (step={self.step})")

    def get_summary(self) -> Dict[str, Any]:
        """Get training summary."""
        def safe_mean(lst):
            return sum(lst) / len(lst) if lst else 0.0

        return {
            'total_steps': self.step,
            'best_reward': self.best_reward,
            'avg_policy_loss': safe_mean(self.stats['policy_loss'][-50:]),
            'avg_value_loss': safe_mean(self.stats['value_loss'][-50:]),
            'avg_reward': safe_mean(self.stats['mean_reward'][-50:]),
            'buffer_size': len(self.buffer),
        }


class DualAgentRLTrainer:
    """
    Dual-agent RL trainer implementing symbiotic competition.

    Trains both curriculum (teacher) and executor (student) agents
    in an adversarial yet cooperative manner.
    """

    def __init__(
        self,
        teacher_config: RLConfig,
        student_config: RLConfig,
    ):
        self.teacher_trainer = PPOTrainer(teacher_config)
        self.student_trainer = PPOTrainer(student_config)

        # Symbiotic competition parameters
        self.teacher_reward_scale = 1.0
        self.student_reward_scale = 1.0
        self.competition_balance = 0.5  # 0 = pure cooperation, 1 = pure competition

    def compute_teacher_reward(
        self,
        student_success: bool,
        task_difficulty: float,
        student_uncertainty: float,
    ) -> float:
        """
        Compute reward for curriculum agent.

        Teacher is rewarded for:
        - Generating tasks at the frontier (moderate success rate)
        - High student uncertainty (challenging tasks)
        - Novel task patterns
        """
        # Frontier reward: peak at ~50% success rate
        frontier_reward = 1.0 - abs(0.5 - float(student_success)) * 2

        # Uncertainty bonus: reward tasks that challenge the student
        uncertainty_bonus = student_uncertainty * 0.5

        # Difficulty scaling: slight bonus for appropriate difficulty
        difficulty_bonus = (1.0 - abs(task_difficulty - 0.5)) * 0.2

        total = frontier_reward + uncertainty_bonus + difficulty_bonus
        return total * self.teacher_reward_scale

    def compute_student_reward(
        self,
        success: bool,
        tool_use_quality: float,
        reasoning_steps: int,
    ) -> float:
        """
        Compute reward for executor agent.

        Student is rewarded for:
        - Correct solutions
        - Effective tool usage
        - Clear reasoning chains
        """
        # Base correctness reward
        correct_reward = 1.0 if success else -0.5

        # Tool use bonus
        tool_bonus = tool_use_quality * 0.3

        # Reasoning chain bonus (capped)
        reasoning_bonus = min(reasoning_steps * 0.05, 0.2)

        total = correct_reward + tool_bonus + reasoning_bonus
        return total * self.student_reward_scale

    def adversarial_update(
        self,
        teacher_success_rate: float,
        student_success_rate: float,
    ) -> None:
        """
        Adjust reward scales based on competition dynamics.

        If one agent is "winning" too much, boost the other.
        """
        # Target: both agents near 50% effectiveness
        teacher_gap = abs(teacher_success_rate - 0.5)
        student_gap = abs(student_success_rate - 0.5)

        # Boost underperforming agent
        if teacher_gap > student_gap:
            self.teacher_reward_scale = min(1.5, self.teacher_reward_scale * 1.05)
            self.student_reward_scale = max(0.5, self.student_reward_scale * 0.95)
        else:
            self.student_reward_scale = min(1.5, self.student_reward_scale * 1.05)
            self.teacher_reward_scale = max(0.5, self.teacher_reward_scale * 0.95)

        logger.debug(
            f"Adversarial update: teacher_scale={self.teacher_reward_scale:.2f}, "
            f"student_scale={self.student_reward_scale:.2f}"
        )

    def train_iteration(
        self,
        teacher_experiences: List[Experience],
        student_experiences: List[Experience],
    ) -> Dict[str, Any]:
        """Run one training iteration for both agents."""
        # Add experiences to buffers
        for exp in teacher_experiences:
            self.teacher_trainer.collect_experience(
                state=exp.state,
                action=exp.action,
                reward=exp.reward,
                value=exp.value,
                log_prob=exp.log_prob,
                done=exp.done,
                domain=exp.domain,
            )

        for exp in student_experiences:
            self.student_trainer.collect_experience(
                state=exp.state,
                action=exp.action,
                reward=exp.reward,
                value=exp.value,
                log_prob=exp.log_prob,
                done=exp.done,
                domain=exp.domain,
            )

        # Train both agents
        teacher_metrics = self.teacher_trainer.train_step()
        student_metrics = self.student_trainer.train_step()

        return {
            'teacher': teacher_metrics,
            'student': student_metrics,
            'teacher_reward_scale': self.teacher_reward_scale,
            'student_reward_scale': self.student_reward_scale,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get combined training summary."""
        return {
            'teacher': self.teacher_trainer.get_summary(),
            'student': self.student_trainer.get_summary(),
            'competition_balance': self.competition_balance,
            'teacher_reward_scale': self.teacher_reward_scale,
            'student_reward_scale': self.student_reward_scale,
        }
