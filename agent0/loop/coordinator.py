from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import json
from dataclasses import asdict
from agent0.agents.student import StudentAgent
from agent0.agents.teacher import TeacherAgent
from agent0.agents.uncertainty import UncertaintyEstimator
from agent0.agents.self_verifier import SelfVerifier  # NEW
from agent0.rewards.calculator import RewardCalculator, RewardWeights
from agent0.memory.embedder import create_embedder, cosine_similarity
from agent0.memory.faiss_store import FaissIndex
from agent0.loop.curriculum_scheduler import CurriculumScheduler
from agent0.validation.input_validator import InputValidator
from agent0.validation.config_validator import validate_config
from agent0.tasks.schema import Trajectory
from agent0.tasks.verifier import verify
from agent0.utils.file_lock import file_lock
from agent0.logging.security_logger import SecurityLogger, SecurityEventType


class Coordinator:
    """
    Runs the co-evolution loop between teacher and student.
    
    Enhanced with:
    - Frontier-based curriculum scheduling
    - Multi-domain task generation
    - Self-verification system
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize security logger
        security_log_dir = Path(config.get("logging", {}).get("base_dir", "./runs"))
        self.security_logger = SecurityLogger(security_log_dir, enable_monitoring=True)
        
        # Validate configuration first
        try:
            validate_config(config)
            self.logger.info("Configuration validation passed")
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            self.security_logger.log_security_event(
                event_type=SecurityEventType.CONFIG_VALIDATION_FAILED,
                severity="HIGH",
                message=f"Configuration validation failed: {str(e)}",
                details={"error": str(e)}
            )
            raise ValueError(f"Invalid configuration: {e}")
        
        # Rate limiting for security
        self._task_rate_limiter = {
            'count': 0,
            'window_start': time.time(),
            'max_per_minute': config.get('rate_limiting', {}).get('max_tasks_per_minute', 60),
            'max_per_hour': config.get('rate_limiting', {}).get('max_tasks_per_hour', 1000)
        }
        
        # Core agents
        self.teacher = TeacherAgent(config["models"]["teacher"])
        self.student = StudentAgent(config["models"]["student"], tool_config=config.get("tooling", {}))
        self.validator = InputValidator()
        
        # Reward calculation
        weights = RewardWeights(
            weight_uncertainty=config["rewards"]["weight_uncertainty"],
            weight_tool_use=config["rewards"]["weight_tool_use"],
            weight_novelty=config["rewards"]["weight_novelty"],
            target_success_rate=config["rewards"]["target_success_rate"],
            repetition_similarity_threshold=config["rewards"]["repetition_similarity_threshold"],
        )
        self.reward_calc = RewardCalculator(weights)
        
        # Logging
        self.run_dir = Path(config["logging"]["base_dir"])
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        # Embeddings for novelty
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
        except (ImportError, AttributeError, RuntimeError, OSError) as embed_error:
            self.logger.warning("Failed to initialize FAISS index: %s. Using memory-based embeddings only.", embed_error)
            self.faiss = None
        
        # Uncertainty estimation
        self.uncertainty = UncertaintyEstimator(config["models"]["student"])
        
        # Enhanced curriculum scheduler
        curriculum_config = config.get("curriculum", {})
        self.scheduler = CurriculumScheduler(
            target_success=curriculum_config.get("target_success", weights.target_success_rate),
            frontier_window=curriculum_config.get("frontier_window", 0.1),
            enable_frontier=curriculum_config.get("enable_frontier", True)
        )
        
        # Self-verification system (optional)
        verification_config = config.get("verification", {})
        self.enable_verification = verification_config.get("enable", False)
        if self.enable_verification:
            self.verifier = SelfVerifier(
                student_agent=self.student,
                num_samples=verification_config.get("num_samples", 3),
                confidence_threshold=verification_config.get("confidence_threshold", 0.7),
                enable_chain_of_thought=verification_config.get("enable_cot", True)
            )
            self.logger.info("Self-verification enabled (samples=%d, threshold=%.2f)",
                           verification_config.get("num_samples", 3),
                           verification_config.get("confidence_threshold", 0.7))
        else:
            self.verifier = None

    def _log_trajectory(self, trajectory: Trajectory) -> None:
        """Log trajectory to JSONL file with file locking for concurrent access."""
        out_file = self.run_dir / "trajectories.jsonl"
        
        try:
            with file_lock(out_file, timeout=5.0):
                with out_file.open("a", encoding="utf-8") as f:
                    data = asdict(trajectory)
                    f.write(json.dumps(data) + "\n")
        except TimeoutError:
            self.logger.error(f"Failed to acquire lock for trajectory logging: {out_file}")
            # Fallback: try to write to a backup file without locking
            try:
                backup_file = self.run_dir / f"trajectories_backup_{hash(trajectory.task.task_id)}.jsonl"
                with backup_file.open("a", encoding="utf-8") as f:
                    data = asdict(trajectory)
                    f.write(json.dumps(data) + "\n")
                self.logger.warning(f"Wrote trajectory to backup file: {backup_file}")
            except Exception as backup_error:
                self.logger.error(f"Failed to write trajectory to backup file: {backup_error}")
        except Exception as e:
            self.logger.error(f"Error logging trajectory: {e}")

    def _check_rate_limits(self) -> bool:
        """Check if task execution is within rate limits."""
        current_time = time.time()
        
        # Reset counters if window has passed
        if current_time - self._task_rate_limiter['window_start'] > 3600:  # 1 hour
            self._task_rate_limiter['count'] = 0
            self._task_rate_limiter['window_start'] = current_time
        
        # Check hourly limit
        if self._task_rate_limiter['count'] >= self._task_rate_limiter['max_per_hour']:
            self.logger.error("Hourly task rate limit exceeded (%d tasks/hour)", 
                            self._task_rate_limiter['max_per_hour'])
            self.security_logger.log_security_event(
                event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                severity="MEDIUM",
                message="Hourly task rate limit exceeded",
                details={
                    "current_count": self._task_rate_limiter['count'],
                    "limit": self._task_rate_limiter['max_per_hour'],
                    "limit_type": "hourly"
                }
            )
            return False
        
        # Check per-minute limit (sliding window)
        tasks_this_minute = getattr(self, '_tasks_this_minute', 0)
        minute_start = getattr(self, '_minute_start', current_time)
        
        if current_time - minute_start > 60:  # New minute
            self._tasks_this_minute = 0
            self._minute_start = current_time
        
        if tasks_this_minute >= self._task_rate_limiter['max_per_minute']:
            self.logger.error("Per-minute task rate limit exceeded (%d tasks/minute)", 
                            self._task_rate_limiter['max_per_minute'])
            self.security_logger.log_security_event(
                event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                severity="MEDIUM",
                message="Per-minute task rate limit exceeded",
                details={
                    "current_count": tasks_this_minute,
                    "limit": self._task_rate_limiter['max_per_minute'],
                    "limit_type": "per_minute"
                }
            )
            return False
        
        return True
    
    def run_once(self, student_signal: Dict[str, Any]) -> Optional[Trajectory]:
        """
        Run one iteration of the co-evolution loop.
        
        Enhanced with:
        - Multi-domain task generation
        - Optional self-verification
        - Enhanced curriculum feedback
        - Rate limiting for security
        """
        try:
            self.logger.warning("LOCAL MODE ACTIVE - code executes directly on your machine (no isolation)")
            
            # Check rate limits first
            if not self._check_rate_limits():
                return None
            
            # Update rate limit counters
            self._task_rate_limiter['count'] += 1
            self._tasks_this_minute = getattr(self, '_tasks_this_minute', 0) + 1
            
            # Get curriculum signal (includes domain, difficulty)
            signal = {**self.scheduler.next_signal(), **student_signal}
            
            # Log curriculum status
            status = self.scheduler.get_status()
            self.logger.info(
                "Curriculum: step=%d, domain=%s, difficulty=%.2f, global_sr=%.2f",
                status["step"],
                signal.get("domain_override", "math"),
                signal.get("difficulty", 0.5),
                status["global_success_rate"]
            )
            
            # Generate task (multi-domain support)
            task = self.teacher.generate_task(signal)
            self.logger.info("Generated %s task: %s", task.domain, task.prompt[:100])
            
            # Validate task
            validation_errors = self.validator.validate_task(task)
            if validation_errors:
                self.logger.error("Task validation failed: %s", validation_errors)
                self.security_logger.log_security_event(
                    event_type=SecurityEventType.INPUT_VALIDATION_FAILED,
                    severity="HIGH",
                    message=f"Task validation failed for task {task.task_id}",
                    details={"task_id": task.task_id, "errors": validation_errors},
                    task_id=task.task_id
                )
                return None
            
            # Student solves task
            traj = self.student.solve(task)

            if any(call.get("tool") == "python" for call in traj.tool_calls):
                self.logger.warning("Python code executed locally - review ./sandbox for generated files")
                # Log code execution for security monitoring
                self.security_logger.log_security_event(
                    event_type=SecurityEventType.CODE_EXECUTION_BLOCKED,
                    severity="LOW",
                    message="Python code execution completed",
                    details={"task_id": task.task_id, "tool_calls": len(traj.tool_calls)},
                    task_id=task.task_id
                )

            # Verify solution
            verdict = verify(task, traj.result)
            traj.success = verdict.get("status") == "pass"
            
            # Self-verification (optional)
            verification_confidence = 1.0
            if self.enable_verification and self.verifier:
                self.logger.info("Running self-verification...")
                verification = self.verifier.verify_solution(task, traj.result)
                
                if not verification.verified:
                    self.logger.warning(
                        "Self-verification failed: confidence=%.2f < threshold",
                        verification.confidence
                    )
                    # Mark as failure if verification rejects
                    traj.success = False
                else:
                    self.logger.info("Self-verification passed: confidence=%.2f", verification.confidence)
                
                verification_confidence = verification.confidence
                # Add to trajectory metadata
                traj.metrics["verification_confidence"] = verification_confidence
                traj.metrics["verification_method"] = verification.verification_method

            # Estimate uncertainty
            success_prob = self.uncertainty.estimate(task.prompt, traj.result)
            
            # Compute novelty
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

            # Calculate reward
            reward = self.reward_calc.compute(traj, success_prob, novelty_sig, similarity=similarity)
            
            # Add verification bonus to reward
            if self.enable_verification:
                reward["verification"] = verification_confidence * 0.1  # 10% weight
                reward["total"] += reward["verification"]
            
            traj.reward = reward
            
            # Log trajectory
            self._log_trajectory(traj)
            
            # Update curriculum (with domain tracking)
            self.scheduler.update(traj.success, domain=task.domain)
            
            # Log completion
            self.logger.info(
                "Task completed: domain=%s success=%s reward=%.3f verification=%.2f",
                task.domain,
                traj.success,
                reward["total"],
                verification_confidence
            )
            
            return traj
            
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Iteration interrupted by user")
            raise  # Re-raise to allow proper shutdown
        except (OSError, IOError) as io_error:
            self.logger.error("I/O error during iteration: %s", io_error)
            return None
        except (ValueError, TypeError) as data_error:
            self.logger.error("Data validation error: %s", data_error)
            return None
        except Exception as unexpected_error:
            self.logger.error("Unexpected error during iteration: %s", unexpected_error, exc_info=True)
            self.logger.error("Check sandbox directory for any generated files.")
            return None
