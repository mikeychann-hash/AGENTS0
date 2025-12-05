"""
Benchmark evaluation for Agent0.

Evaluates model performance on standard benchmarks
with proper answer extraction and comparison.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from agent0.benchmarks.loader import BenchmarkLoader, BenchmarkSample

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of evaluating a single sample."""
    sample_id: str
    predicted: str
    expected: str
    correct: bool
    reasoning: str = ""
    tool_calls: List[Dict] = field(default_factory=list)
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResults:
    """Aggregate results for a benchmark run."""
    benchmark_name: str
    total_samples: int
    correct: int
    accuracy: float
    by_difficulty: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_subject: Dict[str, Dict[str, float]] = field(default_factory=dict)
    avg_latency_ms: float = 0.0
    results: List[EvaluationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "benchmark_name": self.benchmark_name,
            "total_samples": self.total_samples,
            "correct": self.correct,
            "accuracy": self.accuracy,
            "by_difficulty": self.by_difficulty,
            "by_subject": self.by_subject,
            "avg_latency_ms": self.avg_latency_ms,
        }


class AnswerExtractor:
    """Extract and normalize answers from model outputs."""

    @staticmethod
    def extract_number(text: str) -> Optional[str]:
        """Extract numerical answer."""
        # Remove commas from numbers
        text = text.replace(',', '')

        # Look for boxed format first
        match = re.search(r'\\boxed\{([^}]+)\}', text)
        if match:
            return match.group(1).strip()

        # Look for "answer is" format
        match = re.search(r'[Aa]nswer[:\s]+([+-]?\d+\.?\d*)', text)
        if match:
            return match.group(1)

        # Look for "= " followed by number at end
        match = re.search(r'=\s*([+-]?\d+\.?\d*)\s*$', text)
        if match:
            return match.group(1)

        # Extract last number in text
        numbers = re.findall(r'[+-]?\d+\.?\d*', text)
        return numbers[-1] if numbers else None

    @staticmethod
    def extract_fraction(text: str) -> Optional[str]:
        """Extract fraction answer."""
        # Look for \frac{a}{b}
        match = re.search(r'\\frac\{(\d+)\}\{(\d+)\}', text)
        if match:
            return f"{match.group(1)}/{match.group(2)}"

        # Look for a/b format
        match = re.search(r'(\d+)/(\d+)', text)
        if match:
            return f"{match.group(1)}/{match.group(2)}"

        return None

    @staticmethod
    def normalize_answer(answer: str) -> str:
        """Normalize answer for comparison."""
        # Remove whitespace
        answer = answer.strip()

        # Remove $ signs and other LaTeX
        answer = re.sub(r'[\$\\]', '', answer)

        # Normalize fractions
        answer = answer.replace('\\frac', '')

        # Remove trailing zeros after decimal
        if '.' in answer:
            answer = answer.rstrip('0').rstrip('.')

        return answer.lower()


class BenchmarkEvaluator:
    """
    Evaluate model performance on benchmarks.

    Supports multiple evaluation modes:
    - Direct answer comparison
    - Numerical tolerance comparison
    - Custom evaluation functions
    """

    def __init__(
        self,
        tolerance: float = 1e-5,
        timeout_per_sample: float = 30.0,
        output_dir: Optional[Path] = None,
    ):
        self.tolerance = tolerance
        self.timeout = timeout_per_sample
        self.output_dir = Path(output_dir) if output_dir else Path("./eval_results")
        self.extractor = AnswerExtractor()

    def compare_answers(
        self,
        predicted: str,
        expected: str,
        mode: str = "auto",
    ) -> bool:
        """
        Compare predicted and expected answers.

        Args:
            predicted: Model's predicted answer
            expected: Ground truth answer
            mode: Comparison mode (auto, exact, numeric, contains)

        Returns:
            True if answers match
        """
        # Normalize both answers
        pred_norm = self.extractor.normalize_answer(predicted)
        exp_norm = self.extractor.normalize_answer(expected)

        # Exact match
        if pred_norm == exp_norm:
            return True

        if mode == "exact":
            return False

        # Try numeric comparison
        try:
            pred_num = float(pred_norm)
            exp_num = float(exp_norm)
            if abs(pred_num - exp_num) < self.tolerance:
                return True
        except (ValueError, TypeError):
            pass

        # Try fraction comparison
        try:
            pred_frac = self._parse_fraction(pred_norm)
            exp_frac = self._parse_fraction(exp_norm)
            if pred_frac is not None and exp_frac is not None:
                if abs(pred_frac - exp_frac) < self.tolerance:
                    return True
        except (ValueError, ZeroDivisionError):
            pass

        # Contains check for mode="contains"
        if mode == "contains":
            return exp_norm in pred_norm or pred_norm in exp_norm

        return False

    def _parse_fraction(self, text: str) -> Optional[float]:
        """Parse fraction string to float."""
        if '/' in text:
            parts = text.split('/')
            if len(parts) == 2:
                return float(parts[0]) / float(parts[1])
        return None

    def evaluate_sample(
        self,
        sample: BenchmarkSample,
        solver_fn: Callable[[str], str],
    ) -> EvaluationResult:
        """
        Evaluate a single benchmark sample.

        Args:
            sample: Benchmark sample to evaluate
            solver_fn: Function that takes problem text and returns solution

        Returns:
            EvaluationResult with correctness and metadata
        """
        start_time = time.time()

        try:
            # Get model response
            response = solver_fn(sample.problem)
            latency = (time.time() - start_time) * 1000

            # Extract predicted answer
            predicted = self.extractor.extract_number(response) or response

            # Compare with expected
            correct = self.compare_answers(predicted, sample.answer)

            return EvaluationResult(
                sample_id=sample.id,
                predicted=predicted,
                expected=sample.answer,
                correct=correct,
                reasoning=response,
                latency_ms=latency,
                metadata={
                    "difficulty": sample.difficulty,
                    "subject": sample.subject,
                    "domain": sample.domain,
                },
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error(f"Error evaluating {sample.id}: {e}")

            return EvaluationResult(
                sample_id=sample.id,
                predicted="ERROR",
                expected=sample.answer,
                correct=False,
                latency_ms=latency,
                metadata={"error": str(e)},
            )

    def evaluate_benchmark(
        self,
        loader: BenchmarkLoader,
        solver_fn: Callable[[str], str],
        benchmark_name: str = "benchmark",
        limit: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> BenchmarkResults:
        """
        Evaluate full benchmark.

        Args:
            loader: BenchmarkLoader with samples
            solver_fn: Solver function
            benchmark_name: Name for results
            limit: Max samples to evaluate
            progress_callback: Optional callback(current, total)

        Returns:
            BenchmarkResults with aggregate metrics
        """
        samples = loader.samples[:limit] if limit else loader.samples
        results: List[EvaluationResult] = []

        # Track by difficulty and subject
        by_difficulty: Dict[str, Dict[str, int]] = {}
        by_subject: Dict[str, Dict[str, int]] = {}

        total_latency = 0.0
        correct_count = 0

        for i, sample in enumerate(samples):
            result = self.evaluate_sample(sample, solver_fn)
            results.append(result)

            if result.correct:
                correct_count += 1

            total_latency += result.latency_ms

            # Track by difficulty
            diff = sample.difficulty
            if diff not in by_difficulty:
                by_difficulty[diff] = {"correct": 0, "total": 0}
            by_difficulty[diff]["total"] += 1
            if result.correct:
                by_difficulty[diff]["correct"] += 1

            # Track by subject
            if sample.subject:
                if sample.subject not in by_subject:
                    by_subject[sample.subject] = {"correct": 0, "total": 0}
                by_subject[sample.subject]["total"] += 1
                if result.correct:
                    by_subject[sample.subject]["correct"] += 1

            if progress_callback:
                progress_callback(i + 1, len(samples))

            if (i + 1) % 10 == 0:
                current_acc = correct_count / (i + 1)
                logger.info(f"Progress: {i+1}/{len(samples)}, Accuracy: {current_acc:.2%}")

        # Compute final metrics
        accuracy = correct_count / len(samples) if samples else 0.0
        avg_latency = total_latency / len(samples) if samples else 0.0

        # Convert counts to accuracy
        by_diff_acc = {
            k: {"accuracy": v["correct"] / v["total"], "total": v["total"]}
            for k, v in by_difficulty.items()
        }
        by_subj_acc = {
            k: {"accuracy": v["correct"] / v["total"], "total": v["total"]}
            for k, v in by_subject.items()
        }

        return BenchmarkResults(
            benchmark_name=benchmark_name,
            total_samples=len(samples),
            correct=correct_count,
            accuracy=accuracy,
            by_difficulty=by_diff_acc,
            by_subject=by_subj_acc,
            avg_latency_ms=avg_latency,
            results=results,
        )

    def save_results(self, results: BenchmarkResults, filename: Optional[str] = None) -> Path:
        """Save evaluation results to file."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{results.benchmark_name}_{timestamp}.json"

        output_path = self.output_dir / filename

        # Prepare serializable data
        data = results.to_dict()
        data["individual_results"] = [
            {
                "sample_id": r.sample_id,
                "predicted": r.predicted,
                "expected": r.expected,
                "correct": r.correct,
                "latency_ms": r.latency_ms,
                "metadata": r.metadata,
            }
            for r in results.results
        ]

        with output_path.open('w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved results to {output_path}")
        return output_path

    def compare_runs(
        self,
        results_a: BenchmarkResults,
        results_b: BenchmarkResults,
    ) -> Dict[str, Any]:
        """Compare two benchmark runs."""
        return {
            "accuracy_diff": results_b.accuracy - results_a.accuracy,
            "latency_diff_ms": results_b.avg_latency_ms - results_a.avg_latency_ms,
            "run_a": {
                "name": results_a.benchmark_name,
                "accuracy": results_a.accuracy,
                "samples": results_a.total_samples,
            },
            "run_b": {
                "name": results_b.benchmark_name,
                "accuracy": results_b.accuracy,
                "samples": results_b.total_samples,
            },
            "improvement": f"{(results_b.accuracy - results_a.accuracy) * 100:+.2f}%",
        }
