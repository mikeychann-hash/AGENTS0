#!/usr/bin/env python3
"""
CLI script for RL training with Agent0.

Usage:
    python -m agent0.scripts.train_rl --config configs/3070ti.yaml --epochs 100
    python -m agent0.scripts.train_rl --use-grpo --batch-size 16
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent0.config import load_config
from agent0.loop.coordinator import Coordinator
from agent0.training.rl_trainer import RLConfig, PPOTrainer, DualAgentRLTrainer, Experience

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_training_loop(
    config: dict,
    rl_config: RLConfig,
    num_epochs: int,
    steps_per_epoch: int,
    use_dual_agent: bool = True,
):
    """Run the RL training loop."""
    # Initialize coordinator
    coordinator = Coordinator(config)

    # Initialize RL trainer
    if use_dual_agent:
        teacher_config = RLConfig(
            model_name=config["models"]["teacher"].get("model", "qwen2.5:3b"),
            **{k: v for k, v in vars(rl_config).items() if k != "model_name"}
        )
        student_config = RLConfig(
            model_name=config["models"]["student"].get("model", "qwen2.5:7b"),
            **{k: v for k, v in vars(rl_config).items() if k != "model_name"}
        )
        trainer = DualAgentRLTrainer(teacher_config, student_config)
        logger.info("Using dual-agent RL training (symbiotic competition)")
    else:
        trainer = PPOTrainer(rl_config)
        logger.info("Using single-agent RL training")

    # Training statistics
    stats = {
        'total_steps': 0,
        'total_success': 0,
        'epoch_rewards': [],
        'best_accuracy': 0.0,
    }

    logger.info(f"Starting RL training: {num_epochs} epochs, {steps_per_epoch} steps/epoch")
    logger.info(f"GRPO enabled: {rl_config.use_grpo}, Batch size: {rl_config.batch_size}")

    start_time = time.time()

    for epoch in range(num_epochs):
        epoch_start = time.time()
        epoch_rewards = []
        epoch_successes = 0

        for step in range(steps_per_epoch):
            # Run one co-evolution step
            student_signal = {
                "next_task_id": f"task-{epoch:03d}-{step:04d}",
            }

            try:
                trajectory = coordinator.run_once(student_signal)

                if trajectory is None:
                    logger.warning(f"Step {step} returned None trajectory")
                    continue

                # Compute RL reward
                task_difficulty = coordinator.scheduler.state.domain_states.get(
                    trajectory.task.domain,
                    type('', (), {'difficulty': 0.5})()
                ).difficulty

                if use_dual_agent:
                    # Dual-agent rewards
                    teacher_reward = trainer.compute_teacher_reward(
                        student_success=trajectory.success,
                        task_difficulty=task_difficulty,
                        student_uncertainty=trajectory.metrics.get("uncertainty", 0.5),
                    )

                    tool_quality = len([t for t in trajectory.tool_calls if t.get("status") == "ok"]) / max(len(trajectory.tool_calls), 1)
                    student_reward = trainer.compute_student_reward(
                        success=trajectory.success,
                        tool_use_quality=tool_quality,
                        reasoning_steps=len(trajectory.messages),
                    )

                    # Collect experiences
                    teacher_exp = Experience(
                        state=trajectory.task.prompt,
                        action=str(trajectory.task.to_dict() if hasattr(trajectory.task, 'to_dict') else trajectory.task),
                        reward=teacher_reward,
                        value=0.5,  # Placeholder - would need value network
                        log_prob=-1.0,  # Placeholder - would need policy log prob
                        done=True,
                        domain=trajectory.task.domain,
                    )

                    student_exp = Experience(
                        state=trajectory.task.prompt,
                        action=trajectory.result,
                        reward=student_reward,
                        value=0.5,
                        log_prob=-1.0,
                        done=True,
                        domain=trajectory.task.domain,
                        tool_calls=trajectory.tool_calls,
                    )

                    # Train
                    train_metrics = trainer.train_iteration([teacher_exp], [student_exp])
                    epoch_rewards.append(student_reward)
                else:
                    # Single-agent
                    reward = trajectory.reward.get("total", 0.0)

                    trainer.collect_experience(
                        state=trajectory.task.prompt,
                        action=trajectory.result,
                        reward=reward,
                        value=0.5,
                        log_prob=-1.0,
                        done=True,
                        domain=trajectory.task.domain,
                        tool_calls=trajectory.tool_calls,
                    )

                    train_metrics = trainer.train_step()
                    epoch_rewards.append(reward)

                if trajectory.success:
                    epoch_successes += 1
                    stats['total_success'] += 1

                stats['total_steps'] += 1

            except KeyboardInterrupt:
                logger.info("Training interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in step {step}: {e}", exc_info=True)
                continue

        # Epoch summary
        epoch_time = time.time() - epoch_start
        avg_reward = sum(epoch_rewards) / len(epoch_rewards) if epoch_rewards else 0.0
        accuracy = epoch_successes / steps_per_epoch

        stats['epoch_rewards'].append(avg_reward)

        if accuracy > stats['best_accuracy']:
            stats['best_accuracy'] = accuracy
            # Save best model checkpoint
            if use_dual_agent:
                trainer.student_trainer.save_checkpoint(
                    Path(rl_config.output_dir) / "best_student.json"
                )
                trainer.teacher_trainer.save_checkpoint(
                    Path(rl_config.output_dir) / "best_teacher.json"
                )
            else:
                trainer.save_checkpoint(
                    Path(rl_config.output_dir) / "best_model.json"
                )
            logger.info(f"New best accuracy: {accuracy:.2%}")

        logger.info(
            f"Epoch {epoch+1}/{num_epochs} | "
            f"Accuracy: {accuracy:.2%} | "
            f"Avg Reward: {avg_reward:.3f} | "
            f"Time: {epoch_time:.1f}s"
        )

        # Adversarial update for dual-agent
        if use_dual_agent:
            global_sr = coordinator.scheduler.state.success_rate
            trainer.adversarial_update(0.5, global_sr)  # Simplified

        # Save periodic checkpoint
        if (epoch + 1) % rl_config.save_every == 0:
            if use_dual_agent:
                trainer.student_trainer.save_checkpoint()
                trainer.teacher_trainer.save_checkpoint()
            else:
                trainer.save_checkpoint()

    # Final summary
    total_time = time.time() - start_time
    final_accuracy = stats['total_success'] / stats['total_steps'] if stats['total_steps'] > 0 else 0.0

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Total Steps:     {stats['total_steps']}")
    print(f"Total Successes: {stats['total_success']}")
    print(f"Final Accuracy:  {final_accuracy:.2%}")
    print(f"Best Accuracy:   {stats['best_accuracy']:.2%}")
    print(f"Total Time:      {total_time/60:.1f} minutes")
    print(f"Avg Time/Step:   {total_time/max(stats['total_steps'], 1)*1000:.1f}ms")

    if use_dual_agent:
        summary = trainer.get_summary()
        print(f"\nTeacher Summary:")
        print(f"  Steps: {summary['teacher']['total_steps']}")
        print(f"  Best Reward: {summary['teacher']['best_reward']:.3f}")
        print(f"\nStudent Summary:")
        print(f"  Steps: {summary['student']['total_steps']}")
        print(f"  Best Reward: {summary['student']['best_reward']:.3f}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="RL Training for Agent0")

    # Config
    parser.add_argument(
        "--config",
        type=str,
        default="agent0/configs/3070ti.yaml",
        help="Path to config file"
    )

    # Training parameters
    parser.add_argument("--epochs", type=int, default=10, help="Number of epochs")
    parser.add_argument("--steps-per-epoch", type=int, default=50, help="Steps per epoch")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size")
    parser.add_argument("--learning-rate", type=float, default=1e-5, help="Learning rate")

    # RL algorithm
    parser.add_argument("--use-grpo", action="store_true", help="Use GRPO instead of PPO")
    parser.add_argument("--clip-epsilon", type=float, default=0.2, help="PPO clip epsilon")
    parser.add_argument("--gamma", type=float, default=0.99, help="Discount factor")

    # Dual-agent
    parser.add_argument("--single-agent", action="store_true", help="Use single-agent training")

    # Output
    parser.add_argument("--output-dir", type=str, default="./checkpoints", help="Output directory")
    parser.add_argument("--save-every", type=int, default=10, help="Save checkpoint every N epochs")

    # Misc
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    config = load_config(config_path)

    # Create RL config
    rl_config = RLConfig(
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        use_grpo=args.use_grpo,
        clip_epsilon=args.clip_epsilon,
        gamma=args.gamma,
        save_every=args.save_every,
        output_dir=args.output_dir,
    )

    # Run training
    run_training_loop(
        config=config,
        rl_config=rl_config,
        num_epochs=args.epochs,
        steps_per_epoch=args.steps_per_epoch,
        use_dual_agent=not args.single_agent,
    )


if __name__ == "__main__":
    main()
