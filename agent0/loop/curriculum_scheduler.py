from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DomainState:
    """Track performance for a specific domain"""
    success_rate: float = 0.5
    difficulty: float = 0.3  # 0.0 = easy, 1.0 = hard
    total_attempts: int = 0
    recent_successes: List[bool] = field(default_factory=list)
    
    def update(self, success: bool, window: int = 20):
        """Update domain performance with windowed history"""
        self.recent_successes.append(success)
        if len(self.recent_successes) > window:
            self.recent_successes.pop(0)
        
        self.total_attempts += 1
        if self.recent_successes:
            self.success_rate = sum(self.recent_successes) / len(self.recent_successes)


@dataclass
class SchedulerState:
    success_rate: float = 0.5
    step: int = 0
    a: int = 2
    b: int = 3
    c: int = 11
    domain: str = "math"
    domains: List[str] = None
    domain_states: Dict[str, DomainState] = field(default_factory=dict)


class CurriculumScheduler:
    """
    Advanced curriculum scheduler with frontier-based difficulty adjustment.
    
    Maintains per-domain difficulty tracking and selects tasks at the frontier
    of the agent's capabilities (where success rate ~= target).
    """

    def __init__(
        self, 
        target_success: float = 0.5,
        frontier_window: float = 0.1,
        enable_frontier: bool = True
    ) -> None:
        """
        Args:
            target_success: Target success rate (0.5 = 50%)
            frontier_window: Acceptable range around target (0.5 +/- 0.1)
            enable_frontier: Use frontier-based domain selection
        """
        self.target = target_success
        self.frontier_window = frontier_window
        self.enable_frontier = enable_frontier
        
        # Initialize state with domain tracking
        domains = ["math", "logic", "code"]
        domain_states = {d: DomainState() for d in domains}
        
        self.state = SchedulerState(
            domains=domains,
            domain_states=domain_states
        )
        
        logger.info(f"Curriculum initialized: target={target_success}, domains={domains}")

    def update(self, success: bool, domain: Optional[str] = None) -> None:
        """
        Update curriculum based on task performance.
        
        Args:
            success: Whether the task was solved successfully
            domain: Domain of the task (if None, uses current domain)
        """
        self.state.step += 1
        
        # Determine which domain to update
        update_domain = domain if domain else self.state.domain
        
        # Update global success rate (simple moving average)
        self.state.success_rate = (self.state.success_rate * 0.9) + (0.1 if success else 0.0)
        
        # Update domain-specific tracking
        if update_domain in self.state.domain_states:
            self.state.domain_states[update_domain].update(success)
            domain_sr = self.state.domain_states[update_domain].success_rate
            
            logger.info(
                f"Step {self.state.step}: domain={update_domain}, "
                f"success={success}, domain_sr={domain_sr:.2f}, "
                f"global_sr={self.state.success_rate:.2f}"
            )
            
            # Adjust domain difficulty based on performance
            self._adjust_domain_difficulty(update_domain)
        
        # Adjust global difficulty parameters (for math domain)
        self._adjust_global_difficulty()
        
        # Select next domain (frontier-based or round-robin)
        if self.state.step % 3 == 0:  # Every 3 steps, consider domain switch
            self._select_next_domain()

    def _adjust_domain_difficulty(self, domain: str) -> None:
        """Adjust difficulty for a specific domain"""
        domain_state = self.state.domain_states[domain]
        sr = domain_state.success_rate
        
        # Move difficulty toward frontier
        if sr > self.target + self.frontier_window:
            # Too easy - increase difficulty
            domain_state.difficulty = min(domain_state.difficulty + 0.05, 1.0)
            logger.debug(f"{domain} too easy ({sr:.2f}), increasing difficulty to {domain_state.difficulty:.2f}")
        elif sr < self.target - self.frontier_window:
            # Too hard - decrease difficulty
            domain_state.difficulty = max(domain_state.difficulty - 0.05, 0.0)
            logger.debug(f"{domain} too hard ({sr:.2f}), decreasing difficulty to {domain_state.difficulty:.2f}")

    def _adjust_global_difficulty(self) -> None:
        """Adjust global difficulty parameters (a, b, c for math)"""
        # Use global success rate for backward compatibility
        if self.state.success_rate > self.target + 0.05:
            self.state.a = min(self.state.a + 1, 9)
            self.state.b = min(self.state.b + 1, 20)
            self.state.c = min(self.state.c + 1, 20)
        elif self.state.success_rate < self.target - 0.05:
            self.state.a = max(self.state.a - 1, 1)
            self.state.b = max(self.state.b - 1, -20)
            self.state.c = max(self.state.c - 1, -20)

    def _select_next_domain(self) -> None:
        """
        Select next domain using frontier-based selection.
        
        Chooses domain whose success rate is closest to target
        (the frontier of capabilities).
        """
        if not self.enable_frontier or not self.state.domains:
            # Fallback to round-robin
            self._round_robin_domain()
            return
        
        # Find domain closest to frontier
        frontier_scores = {}
        for domain in self.state.domains:
            if domain not in self.state.domain_states:
                continue
            
            state = self.state.domain_states[domain]
            # Score: how close to target (lower is better)
            score = abs(state.success_rate - self.target)
            frontier_scores[domain] = score
        
        if frontier_scores:
            # Select domain closest to target success rate
            next_domain = min(frontier_scores, key=frontier_scores.get)
            
            # Add some exploration: occasionally pick second-best
            import random
            if random.random() < 0.2 and len(frontier_scores) > 1:
                sorted_domains = sorted(frontier_scores.items(), key=lambda x: x[1])
                next_domain = sorted_domains[1][0]  # Second closest
            
            if next_domain != self.state.domain:
                logger.info(
                    f"Domain switch: {self.state.domain} -> {next_domain} "
                    f"(frontier score: {frontier_scores[next_domain]:.3f})"
                )
                self.state.domain = next_domain
        else:
            self._round_robin_domain()

    def _round_robin_domain(self) -> None:
        """Simple round-robin domain selection"""
        if not self.state.domains:
            return
        
        idx = self.state.domains.index(self.state.domain) if self.state.domain in self.state.domains else 0
        new_domain = self.state.domains[(idx + 1) % len(self.state.domains)]
        
        if new_domain != self.state.domain:
            logger.info(f"Round-robin domain switch: {self.state.domain} -> {new_domain}")
            self.state.domain = new_domain

    def next_signal(self) -> Dict[str, object]:
        """
        Get signal for next task generation.
        
        Returns:
            Dict with domain and difficulty parameters
        """
        # Get domain-specific difficulty
        difficulty = 0.5  # default
        if self.state.domain in self.state.domain_states:
            difficulty = self.state.domain_states[self.state.domain].difficulty
        
        return {
            "a": self.state.a,
            "b": self.state.b,
            "c": self.state.c,
            "domain_override": self.state.domain,
            "difficulty": difficulty,  # New: normalized difficulty 0-1
            "frontier_mode": self.enable_frontier,
        }

    def get_status(self) -> Dict[str, object]:
        """Get detailed curriculum status for logging/debugging"""
        status = {
            "step": self.state.step,
            "global_success_rate": self.state.success_rate,
            "current_domain": self.state.domain,
            "domains": {}
        }
        
        for domain, state in self.state.domain_states.items():
            status["domains"][domain] = {
                "success_rate": state.success_rate,
                "difficulty": state.difficulty,
                "total_attempts": state.total_attempts,
                "recent_history": len(state.recent_successes),
            }
        
        return status
