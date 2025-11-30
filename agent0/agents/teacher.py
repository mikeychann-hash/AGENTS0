from __future__ import annotations

import json
import random
from typing import Any, Dict, Optional
import logging

from agent0.models.factory import create_model
from agent0.agents.prompts import TEACHER_PROMPT
from agent0.tasks.schema import TaskSpec, VerifierSpec

logger = logging.getLogger(__name__)


class TeacherAgent:
    """
    Generates tasks targeting the student's learning frontier.
    
    Supports multiple domains (math, logic, code) with difficulty scaling.
    """

    def __init__(self, model_config: Dict[str, Any]) -> None:
        self.model_config = model_config
        self.model = create_model(model_config)
        
        # Domain generators
        self.domain_generators = {
            "math": self._generate_math_task,
            "logic": self._generate_logic_task,
            "code": self._generate_code_task,
        }

    def _parse_params(self, raw: str) -> Dict[str, int]:
        """Parse LLM response for task parameters"""
        try:
            data = json.loads(raw.strip().splitlines()[-1])
            a, b, c = int(data["a"]), int(data["b"]), int(data["c"])
            if a == 0:
                raise ValueError("a must be non-zero")
            return {"a": a, "b": b, "c": c}
        except Exception:
            return {}

    def generate_task(self, student_signal: Dict[str, Any]) -> TaskSpec:
        """
        Produce a new task using student performance signals.
        
        Args:
            student_signal: Contains domain, difficulty, and curriculum params
            
        Returns:
            TaskSpec with task prompt and verifier
        """
        # Handle prompt override (manual task specification)
        if "prompt_override" in student_signal:
            return self._generate_override_task(student_signal)
        
        # Get domain from signal
        domain = student_signal.get("domain_override", "math")
        task_id = student_signal.get("next_task_id", "task-0001")
        difficulty = student_signal.get("difficulty", 0.5)  # 0-1 scale
        
        # Generate task for specific domain
        if domain in self.domain_generators:
            logger.info(f"Generating {domain} task (difficulty={difficulty:.2f})")
            return self.domain_generators[domain](
                task_id=task_id,
                difficulty=difficulty,
                student_signal=student_signal
            )
        else:
            logger.warning(f"Unknown domain {domain}, defaulting to math")
            return self._generate_math_task(task_id, difficulty, student_signal)

    def _generate_override_task(self, student_signal: Dict[str, Any]) -> TaskSpec:
        """Generate task from explicit prompt override"""
        task_id = student_signal.get("next_task_id", "task-0001")
        domain = student_signal.get("domain_override", "logic")
        prompt = str(student_signal["prompt_override"])
        verifier = None
        
        return TaskSpec(
            task_id=task_id,
            domain=domain,
            prompt=prompt,
            constraints=["show reasoning", "use tools if needed"],
            verifier=verifier,
            seed=student_signal.get("seed"),
        )

    def _generate_math_task(
        self,
        task_id: str,
        difficulty: float,
        student_signal: Dict[str, Any]
    ) -> TaskSpec:
        """
        Generate mathematical task with difficulty scaling.
        
        Difficulty 0.0-0.3: Linear equations (ax + b = c)
        Difficulty 0.3-0.6: Quadratic equations
        Difficulty 0.6-1.0: Systems of equations or complex algebra
        """
        # Get parameters (from LLM or defaults) with validation
        raw = self.model.generate(
            TEACHER_PROMPT,
            max_tokens=64,
            temperature=self.model_config.get("temperature", 0.7)
        )
        params = self._parse_params(raw)
        
        # Validate and sanitize parameters
        try:
            a = int(params.get("a", student_signal.get("a", 2)))
            b = int(params.get("b", student_signal.get("b", 3)))
            c = int(params.get("c", student_signal.get("c", 11)))
            
            # Ensure parameters are within safe bounds
            a = max(1, min(a, 100))  # a must be positive and reasonable
            b = max(-50, min(b, 50))  # b within reasonable range
            c = max(-100, min(c, 100))  # c within reasonable range
            
        except (ValueError, TypeError):
            # Fallback to safe defaults if conversion fails
            a, b, c = 2, 3, 11
        
        # Scale complexity based on difficulty
        if difficulty < 0.3:
            # Simple linear: ax + b = c
            prompt = f"Solve for x: {a}x + {b} = {c}."
            answer = (c - b) / a
            
        elif difficulty < 0.6:
            # Quadratic: x^2 + bx + c = 0
            discriminant = b**2 - 4*c
            if discriminant >= 0:
                prompt = f"Solve for x: x² + {b}x + {c} = 0."
                import math
                x1 = (-b + math.sqrt(discriminant)) / 2
                x2 = (-b - math.sqrt(discriminant)) / 2
                answer = f"{x1:.2f}" if abs(x1) < abs(x2) else f"{x2:.2f}"
            else:
                # Fall back to linear if no real solutions
                prompt = f"Solve for x: {a}x + {b} = {c}."
                answer = (c - b) / a
        
        else:
            # System of equations or multi-step with proper error handling
            prompt = f"Solve for x and y: {a}x + {b}y = {c} and x - y = 1."
            
            try:
                # x - y = 1 => x = y + 1
                # a(y+1) + by = c => (a+b)y = c - a => y = (c-a)/(a+b)
                denominator = a + b
                if abs(denominator) > 1e-10:  # Proper floating point comparison
                    y = (c - a) / denominator
                    x = y + 1
                    
                    # Validate results are reasonable
                    if abs(x) < 1000 and abs(y) < 1000:  # Prevent huge numbers
                        answer = f"x={x:.2f}"
                    else:
                        # Results too large, fall back to simpler problem
                        prompt = f"Solve for x: {a}x + {b} = {c}."
                        answer = (c - b) / a if abs(a) > 1e-10 else "0"
                else:
                    # Denominator too small, fall back to linear equation
                    prompt = f"Solve for x: {a}x + {b} = {c}."
                    answer = (c - b) / a if abs(a) > 1e-10 else "0"
                    
            except (ZeroDivisionError, OverflowError, ValueError):
                # Any mathematical error, use safe fallback
                prompt = f"Solve for x: {a}x + {b} = {c}."
                answer = "0"  # Safe fallback answer
        
        verifier = VerifierSpec(
            kind="expected_number",
            spec={"answer": str(answer)}
        )
        
        return TaskSpec(
            task_id=task_id,
            domain="math",
            prompt=prompt,
            constraints=["show reasoning", "use tools if needed"],
            verifier=verifier,
            seed=student_signal.get("seed"),
        )

    def _generate_logic_task(
        self,
        task_id: str,
        difficulty: float,
        student_signal: Dict[str, Any]
    ) -> TaskSpec:
        """
        Generate logical reasoning task.
        
        Difficulty 0.0-0.3: Simple deduction
        Difficulty 0.3-0.6: Multi-step reasoning
        Difficulty 0.6-1.0: Complex logical puzzles
        """
        templates = {
            "easy": [
                "If all cats are animals, and Fluffy is a cat, is Fluffy an animal?",
                "If it rains, the ground gets wet. The ground is wet. Did it rain?",
                "All squares are rectangles. Is a rectangle always a square?",
            ],
            "medium": [
                "If A > B and B > C, what is the relationship between A and C?",
                "Either it is day or it is night. It is not day. What time is it?",
                "If no cats are dogs, and some pets are cats, can some pets be dogs?",
            ],
            "hard": [
                "Five people are in a race. Alice beat Bob. Carol finished before David but after Alice. Eve came in last. Who came in second?",
                "If all A are B, and no B are C, what can we conclude about A and C?",
                "Three boxes contain either apples or oranges. Box 1 has a label that's wrong. Box 2's label is correct. Box 3 is unlabeled. If Box 1 says 'apples', what does Box 2 contain?",
            ]
        }
        
        # Select difficulty tier
        if difficulty < 0.3:
            prompt = random.choice(templates["easy"])
            # Simple yes/no verification
            verifier = VerifierSpec(kind="contains", spec={"substring": "yes"})
        elif difficulty < 0.6:
            prompt = random.choice(templates["medium"])
            verifier = None  # Manual verification
        else:
            prompt = random.choice(templates["hard"])
            verifier = None
        
        return TaskSpec(
            task_id=task_id,
            domain="logic",
            prompt=prompt,
            constraints=["explain your reasoning step by step"],
            verifier=verifier,
            seed=student_signal.get("seed"),
        )

    def _generate_code_task(
        self,
        task_id: str,
        difficulty: float,
        student_signal: Dict[str, Any]
    ) -> TaskSpec:
        """
        Generate coding task.
        
        Difficulty 0.0-0.3: Simple function implementation
        Difficulty 0.3-0.6: Data structure manipulation
        Difficulty 0.6-1.0: Algorithm implementation
        """
        templates = {
            "easy": [
                "Write a Python function that returns the sum of two numbers.",
                "Write a function that checks if a number is even.",
                "Write a function that returns the length of a string.",
            ],
            "medium": [
                "Write a function that reverses a list in Python.",
                "Write a function that finds the maximum value in a list.",
                "Write a function that counts the occurrences of each character in a string.",
            ],
            "hard": [
                "Write a function that finds all prime numbers up to n using the Sieve of Eratosthenes.",
                "Write a function that implements binary search on a sorted list.",
                "Write a function that checks if a string is a valid palindrome, ignoring spaces and punctuation.",
            ]
        }
        
        # Select difficulty tier
        if difficulty < 0.3:
            prompt = random.choice(templates["easy"])
        elif difficulty < 0.6:
            prompt = random.choice(templates["medium"])
        else:
            prompt = random.choice(templates["hard"])
        
        # Code tasks need execution verification (test cases)
        verifier = VerifierSpec(
            kind="python_predicate",
            spec={"code": "True"}  # Placeholder - would need actual test cases
        )
        
        return TaskSpec(
            task_id=task_id,
            domain="code",
            prompt=prompt,
            constraints=["write working Python code", "include docstring"],
            verifier=verifier,
            seed=student_signal.get("seed"),
        )
