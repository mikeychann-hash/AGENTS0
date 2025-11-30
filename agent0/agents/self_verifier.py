"""
Self-verification system for Agent0.

Allows the student agent to verify its own solutions through
multiple sampling and consensus checking.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of self-verification"""
    verified: bool
    confidence: float
    consensus_answer: Optional[str]
    all_answers: List[str]
    agreement_rate: float
    verification_method: str


class SelfVerifier:
    """
    Self-verification through multiple solution attempts.
    
    The agent generates multiple solutions to the same problem
    and uses consensus/voting to determine confidence.
    """
    
    def __init__(
        self,
        student_agent: Any,
        num_samples: int = 3,
        confidence_threshold: float = 0.7,
        enable_chain_of_thought: bool = True
    ):
        """
        Args:
            student_agent: StudentAgent instance
            num_samples: Number of solutions to generate
            confidence_threshold: Min agreement rate to verify (0.7 = 70%)
            enable_chain_of_thought: Add "think step by step" to prompts
        """
        self.student = student_agent
        self.num_samples = num_samples
        self.confidence_threshold = confidence_threshold
        self.enable_cot = enable_chain_of_thought
    
    def verify_solution(
        self,
        task: Any,
        initial_solution: Optional[str] = None
    ) -> VerificationResult:
        """
        Verify a solution through multiple attempts.
        
        Args:
            task: TaskSpec to solve
            initial_solution: Optional initial solution to verify
            
        Returns:
            VerificationResult with consensus and confidence
        """
        logger.info(f"Self-verifying task {task.task_id} with {self.num_samples} samples")
        
        # Generate multiple solutions
        solutions = []
        
        if initial_solution:
            solutions.append(initial_solution)
        
        # Generate additional solutions
        for i in range(self.num_samples):
            logger.debug(f"Generating verification sample {i+1}/{self.num_samples}")
            
            # Optionally add chain-of-thought prompt
            if self.enable_cot and not task.prompt.lower().endswith("step by step"):
                enhanced_task = self._add_cot_prompt(task)
            else:
                enhanced_task = task
            
            # Solve task
            trajectory = self.student.solve(enhanced_task)
            solutions.append(trajectory.result)
        
        # Analyze consensus
        return self._compute_consensus(solutions)
    
    def _add_cot_prompt(self, task: Any) -> Any:
        """Add chain-of-thought prompt to task"""
        from agent0.tasks.schema import TaskSpec
        
        enhanced_prompt = f"{task.prompt}\n\nThink step by step and show your reasoning."
        
        return TaskSpec(
            task_id=task.task_id,
            domain=task.domain,
            prompt=enhanced_prompt,
            constraints=task.constraints,
            verifier=task.verifier,
            seed=task.seed
        )
    
    def _compute_consensus(
        self,
        solutions: List[str]
    ) -> VerificationResult:
        """
        Compute consensus from multiple solutions.
        
        Uses voting/agreement to determine confidence.
        """
        # Normalize solutions (strip whitespace, lowercase)
        normalized = [self._normalize_answer(s) for s in solutions]
        
        # Count occurrences
        counts = Counter(normalized)
        
        if not counts:
            return VerificationResult(
                verified=False,
                confidence=0.0,
                consensus_answer=None,
                all_answers=solutions,
                agreement_rate=0.0,
                verification_method="consensus_voting"
            )
        
        # Get most common answer
        consensus, count = counts.most_common(1)[0]
        agreement_rate = count / len(solutions)
        
        # Determine if verified
        verified = agreement_rate >= self.confidence_threshold
        
        logger.info(
            f"Consensus: '{consensus}' ({count}/{len(solutions)} = {agreement_rate:.1%}), "
            f"verified={verified}"
        )
        
        return VerificationResult(
            verified=verified,
            confidence=agreement_rate,
            consensus_answer=consensus if verified else None,
            all_answers=solutions,
            agreement_rate=agreement_rate,
            verification_method="consensus_voting"
        )
    
    def _normalize_answer(self, answer: str) -> str:
        """
        Normalize answer for comparison.
        
        Handles numbers, strings, and common variations.
        """
        if not answer:
            return ""
        
        # Strip whitespace
        normalized = answer.strip().lower()
        
        # Try to parse as number
        try:
            # Handle numbers
            num = float(normalized)
            # Round to 2 decimal places for comparison
            normalized = f"{num:.2f}"
        except (ValueError, TypeError):
            pass
        
        # Remove common punctuation
        for char in ['.', ',', '!', '?', ';', ':']:
            if normalized.endswith(char):
                normalized = normalized[:-1]
        
        return normalized


class MultiStepVerifier:
    """
    Verification through multi-step decomposition.
    
    Breaks complex problems into steps and verifies each step.
    """
    
    def __init__(self, student_agent: Any):
        self.student = student_agent
    
    def verify_with_steps(
        self,
        task: Any,
        solution: str
    ) -> VerificationResult:
        """
        Verify solution by checking intermediate steps.
        
        Args:
            task: Original task
            solution: Proposed solution
            
        Returns:
            VerificationResult based on step verification
        """
        logger.info(f"Multi-step verification for task {task.task_id}")
        
        # Ask agent to break down solution into steps
        decomposition_prompt = (
            f"Original problem: {task.prompt}\n"
            f"Solution: {solution}\n\n"
            f"Break this solution into clear steps. Number each step."
        )
        
        from agent0.tasks.schema import TaskSpec
        
        decomp_task = TaskSpec(
            task_id=f"{task.task_id}_decomp",
            domain=task.domain,
            prompt=decomposition_prompt,
            constraints=["list steps clearly"],
            verifier=None,
            seed=task.seed
        )
        
        # Get step decomposition
        decomp_result = self.student.solve(decomp_task)
        steps = self._parse_steps(decomp_result.result)
        
        logger.info(f"Decomposed into {len(steps)} steps")
        
        # Verify each step
        step_verifications = []
        for i, step in enumerate(steps):
            is_valid = self._verify_step(step, task.domain)
            step_verifications.append(is_valid)
            logger.debug(f"Step {i+1}: {'✓' if is_valid else '✗'} - {step[:50]}...")
        
        # Overall verification
        if not step_verifications:
            verified = False
            confidence = 0.0
        else:
            verified = all(step_verifications)
            confidence = sum(step_verifications) / len(step_verifications)
        
        return VerificationResult(
            verified=verified,
            confidence=confidence,
            consensus_answer=solution if verified else None,
            all_answers=[solution],
            agreement_rate=confidence,
            verification_method="multi_step_decomposition"
        )
    
    def _parse_steps(self, text: str) -> List[str]:
        """Parse numbered steps from text"""
        import re
        
        steps = []
        lines = text.strip().split('\n')
        
        for line in lines:
            # Match patterns like "1.", "Step 1:", etc.
            if re.match(r'^\s*\d+[.):]\s*', line) or re.match(r'^\s*Step\s+\d+', line, re.I):
                # Remove numbering
                clean_step = re.sub(r'^\s*(\d+[.):]\s*|Step\s+\d+[.):]\s*)', '', line, flags=re.I)
                if clean_step.strip():
                    steps.append(clean_step.strip())
        
        return steps
    
    def _verify_step(self, step: str, domain: str) -> bool:
        """
        Verify a single step (placeholder implementation).
        
        In a full implementation, this would check step validity
        using domain-specific rules or an LLM judge.
        """
        # Simple heuristic: step should be substantial
        return len(step.split()) > 3


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # This would normally use a real StudentAgent
    class MockStudent:
        def solve(self, task):
            from agent0.tasks.schema import Trajectory
            return Trajectory(
                task=task,
                messages=[],
                tool_calls=[],
                result="42",
                success=True,
                reward={},
                metrics={}
            )
    
    # Create verifier
    verifier = SelfVerifier(
        student_agent=MockStudent(),
        num_samples=3,
        confidence_threshold=0.7
    )
    
    # Mock task
    from agent0.tasks.schema import TaskSpec
    task = TaskSpec(
        task_id="test",
        domain="math",
        prompt="What is 6 * 7?",
        constraints=[],
        verifier=None
    )
    
    # Verify
    result = verifier.verify_solution(task)
    print(f"Verified: {result.verified}")
    print(f"Confidence: {result.confidence:.1%}")
    print(f"Consensus: {result.consensus_answer}")
