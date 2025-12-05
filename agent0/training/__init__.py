"""
Training module for Agent0.

Includes:
- PEFT/LoRA fine-tuning
- VeRL-style RL training with PPO/GRPO
- Dual-agent symbiotic training
"""
from agent0.training.peft_trainer import PeftConfig, train_peft, load_trajectories
from agent0.training.rl_trainer import (
    RLConfig,
    Experience,
    PPOTrainer,
    DualAgentRLTrainer,
    RolloutBuffer,
)

__all__ = [
    'PeftConfig',
    'train_peft',
    'load_trajectories',
    'RLConfig',
    'Experience',
    'PPOTrainer',
    'DualAgentRLTrainer',
    'RolloutBuffer',
]
