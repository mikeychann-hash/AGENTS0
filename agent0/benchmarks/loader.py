"""
Benchmark dataset loaders for Agent0.

Supports loading and parsing standard benchmarks:
- MATH dataset (Hendrycks et al.)
- GSM8K dataset (Cobbe et al.)
- Custom benchmark formats
"""
from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkSample:
    """A single benchmark sample."""
    id: str
    problem: str
    answer: str
    domain: str = "math"
    difficulty: str = "medium"
    subject: str = ""
    solution: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_task_spec_dict(self) -> Dict[str, Any]:
        """Convert to TaskSpec-compatible dictionary."""
        return {
            "task_id": self.id,
            "domain": self.domain,
            "prompt": self.problem,
            "expected_answer": self.answer,
            "difficulty": self.difficulty,
            "subject": self.subject,
        }


class BenchmarkLoader:
    """
    Load and manage benchmark datasets.

    Supports multiple formats:
    - MATH: JSONL with problem, solution, answer fields
    - GSM8K: JSONL with question, answer fields
    - Custom: Flexible JSON/JSONL format
    """

    SUPPORTED_BENCHMARKS = {
        "math": {
            "subjects": ["algebra", "counting_and_probability", "geometry",
                        "intermediate_algebra", "number_theory", "prealgebra",
                        "precalculus"],
            "difficulty_levels": ["1", "2", "3", "4", "5"],
        },
        "gsm8k": {
            "splits": ["train", "test"],
        },
    }

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else Path("./data/benchmarks")
        self.samples: List[BenchmarkSample] = []
        self._loaded_benchmarks: Dict[str, bool] = {}

    def load_math(
        self,
        path: Optional[Path] = None,
        subjects: Optional[List[str]] = None,
        difficulties: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> int:
        """
        Load MATH dataset.

        Args:
            path: Path to MATH dataset directory or file
            subjects: Filter by subjects (e.g., ["algebra", "geometry"])
            difficulties: Filter by difficulty levels (e.g., ["3", "4", "5"])
            limit: Maximum samples to load

        Returns:
            Number of samples loaded
        """
        if path is None:
            path = self.data_dir / "MATH"

        count = 0
        subjects = subjects or self.SUPPORTED_BENCHMARKS["math"]["subjects"]
        difficulties = difficulties or self.SUPPORTED_BENCHMARKS["math"]["difficulty_levels"]

        if path.is_file():
            # Single file mode
            count = self._load_math_file(path, subjects, difficulties, limit)
        elif path.is_dir():
            # Directory mode (standard MATH format)
            for subject_dir in path.iterdir():
                if not subject_dir.is_dir():
                    continue
                subject = subject_dir.name
                if subject not in subjects:
                    continue

                for problem_file in subject_dir.glob("*.json"):
                    if limit and count >= limit:
                        break

                    try:
                        with problem_file.open('r') as f:
                            data = json.load(f)

                        level = data.get("level", "Level 3").replace("Level ", "")
                        if level not in difficulties:
                            continue

                        sample = BenchmarkSample(
                            id=f"math_{subject}_{problem_file.stem}",
                            problem=data.get("problem", ""),
                            answer=self._extract_math_answer(data.get("solution", "")),
                            domain="math",
                            difficulty=level,
                            subject=subject,
                            solution=data.get("solution", ""),
                            metadata={"type": data.get("type", "")},
                        )
                        self.samples.append(sample)
                        count += 1

                    except (json.JSONDecodeError, IOError) as e:
                        logger.warning(f"Failed to load {problem_file}: {e}")

        self._loaded_benchmarks["math"] = True
        logger.info(f"Loaded {count} MATH samples")
        return count

    def _load_math_file(
        self,
        path: Path,
        subjects: List[str],
        difficulties: List[str],
        limit: Optional[int],
    ) -> int:
        """Load MATH from single JSONL file."""
        count = 0

        with path.open('r') as f:
            for line in f:
                if limit and count >= limit:
                    break

                try:
                    data = json.loads(line.strip())
                    subject = data.get("subject", data.get("type", "algebra")).lower()
                    level = str(data.get("level", "3")).replace("Level ", "")

                    if subject not in subjects or level not in difficulties:
                        continue

                    sample = BenchmarkSample(
                        id=f"math_{count:05d}",
                        problem=data.get("problem", data.get("question", "")),
                        answer=self._extract_math_answer(
                            data.get("solution", data.get("answer", ""))
                        ),
                        domain="math",
                        difficulty=level,
                        subject=subject,
                        solution=data.get("solution", ""),
                    )
                    self.samples.append(sample)
                    count += 1

                except json.JSONDecodeError:
                    continue

        return count

    def _extract_math_answer(self, solution: str) -> str:
        """Extract final answer from MATH solution."""
        # Look for boxed answer format: \boxed{...}
        match = re.search(r'\\boxed\{([^}]+)\}', solution)
        if match:
            return match.group(1).strip()

        # Look for "The answer is" format
        match = re.search(r'[Tt]he answer is[:\s]+([^\n\.]+)', solution)
        if match:
            return match.group(1).strip()

        # Return last line as fallback
        lines = solution.strip().split('\n')
        return lines[-1].strip() if lines else ""

    def load_gsm8k(
        self,
        path: Optional[Path] = None,
        split: str = "test",
        limit: Optional[int] = None,
    ) -> int:
        """
        Load GSM8K dataset.

        Args:
            path: Path to GSM8K JSONL file
            split: Dataset split ("train" or "test")
            limit: Maximum samples to load

        Returns:
            Number of samples loaded
        """
        if path is None:
            path = self.data_dir / f"gsm8k_{split}.jsonl"

        if not path.exists():
            logger.warning(f"GSM8K file not found: {path}")
            return 0

        count = 0

        with path.open('r') as f:
            for line in f:
                if limit and count >= limit:
                    break

                try:
                    data = json.loads(line.strip())

                    # GSM8K format: question, answer
                    question = data.get("question", "")
                    answer_text = data.get("answer", "")

                    # Extract numerical answer from GSM8K format
                    # Format: "explanation #### numerical_answer"
                    answer = self._extract_gsm8k_answer(answer_text)

                    sample = BenchmarkSample(
                        id=f"gsm8k_{split}_{count:05d}",
                        problem=question,
                        answer=answer,
                        domain="math",
                        difficulty="medium",
                        subject="arithmetic",
                        solution=answer_text,
                    )
                    self.samples.append(sample)
                    count += 1

                except json.JSONDecodeError:
                    continue

        self._loaded_benchmarks["gsm8k"] = True
        logger.info(f"Loaded {count} GSM8K samples ({split})")
        return count

    def _extract_gsm8k_answer(self, answer_text: str) -> str:
        """Extract numerical answer from GSM8K format."""
        # GSM8K uses #### to mark the final answer
        if "####" in answer_text:
            return answer_text.split("####")[-1].strip()

        # Fallback: extract last number
        numbers = re.findall(r'-?\d+(?:,\d{3})*(?:\.\d+)?', answer_text)
        if numbers:
            return numbers[-1].replace(',', '')

        return answer_text.strip()

    def load_custom(
        self,
        path: Path,
        problem_field: str = "problem",
        answer_field: str = "answer",
        domain: str = "math",
        limit: Optional[int] = None,
    ) -> int:
        """
        Load custom benchmark format.

        Args:
            path: Path to JSONL file
            problem_field: Field name for problem text
            answer_field: Field name for answer
            domain: Domain classification
            limit: Maximum samples to load

        Returns:
            Number of samples loaded
        """
        count = 0

        with path.open('r') as f:
            for line in f:
                if limit and count >= limit:
                    break

                try:
                    data = json.loads(line.strip())

                    sample = BenchmarkSample(
                        id=f"custom_{count:05d}",
                        problem=data.get(problem_field, ""),
                        answer=str(data.get(answer_field, "")),
                        domain=domain,
                        difficulty=data.get("difficulty", "medium"),
                        subject=data.get("subject", ""),
                        solution=data.get("solution", ""),
                        metadata=data,
                    )
                    self.samples.append(sample)
                    count += 1

                except json.JSONDecodeError:
                    continue

        logger.info(f"Loaded {count} custom samples from {path}")
        return count

    def get_by_difficulty(self, difficulty: str) -> List[BenchmarkSample]:
        """Filter samples by difficulty."""
        return [s for s in self.samples if s.difficulty == difficulty]

    def get_by_subject(self, subject: str) -> List[BenchmarkSample]:
        """Filter samples by subject."""
        return [s for s in self.samples if s.subject == subject]

    def get_by_domain(self, domain: str) -> List[BenchmarkSample]:
        """Filter samples by domain."""
        return [s for s in self.samples if s.domain == domain]

    def sample(self, n: int = 1, replace: bool = False) -> List[BenchmarkSample]:
        """Randomly sample from loaded benchmarks."""
        if n >= len(self.samples) and not replace:
            return self.samples.copy()
        return random.choices(self.samples, k=n) if replace else random.sample(self.samples, min(n, len(self.samples)))

    def iter_batches(self, batch_size: int = 32) -> Iterator[List[BenchmarkSample]]:
        """Iterate over samples in batches."""
        for i in range(0, len(self.samples), batch_size):
            yield self.samples[i:i + batch_size]

    def shuffle(self) -> None:
        """Shuffle samples in place."""
        random.shuffle(self.samples)

    def __len__(self) -> int:
        return len(self.samples)

    def __iter__(self) -> Iterator[BenchmarkSample]:
        return iter(self.samples)

    def __getitem__(self, idx: int) -> BenchmarkSample:
        return self.samples[idx]

    def summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        difficulties = {}
        subjects = {}
        domains = {}

        for s in self.samples:
            difficulties[s.difficulty] = difficulties.get(s.difficulty, 0) + 1
            if s.subject:
                subjects[s.subject] = subjects.get(s.subject, 0) + 1
            domains[s.domain] = domains.get(s.domain, 0) + 1

        return {
            "total_samples": len(self.samples),
            "loaded_benchmarks": list(self._loaded_benchmarks.keys()),
            "by_difficulty": difficulties,
            "by_subject": subjects,
            "by_domain": domains,
        }
