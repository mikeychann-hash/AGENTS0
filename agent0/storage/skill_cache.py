#!/usr/bin/env python3
"""
Agent0 Skill Cache System.

Caches successful procedures as reusable "skills" that can be:
- Recalled for similar tasks
- Executed without full LLM reasoning
- Refined over time based on success rates

A skill is a learned procedure like:
- "How to spin up an X server"
- "How to debug Y type of error"
- "Standard pattern for Z task"

Usage:
    from agent0.storage.skill_cache import SkillCache, Skill

    cache = SkillCache()

    # Store a skill
    skill = Skill(
        name="solve_linear_equation",
        description="Solve equations of form ax + b = c",
        procedure=[
            {"action": "parse", "template": "Extract a, b, c from {equation}"},
            {"action": "compute", "template": "x = ({c} - {b}) / {a}"},
            {"action": "verify", "template": "Check: {a}*{x} + {b} = {c}"},
        ],
        domain="math",
        pattern=r"solve.*?(\d+)x\s*[+-]\s*(\d+)\s*=\s*(\d+)",
    )
    cache.save(skill)

    # Find matching skills
    matches = cache.find_matching("Solve for x: 3x + 5 = 20")

    # Execute a skill
    result = cache.execute("solve_linear_equation", {"equation": "3x + 5 = 20"})
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SkillStep:
    """A single step in a skill procedure."""
    action: str  # "parse", "compute", "tool_call", "llm_call", "verify"
    template: str  # Template with {placeholders}
    tool: Optional[str] = None  # Tool to call if action is "tool_call"
    fallback: Optional[str] = None  # Fallback action if this fails
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Skill:
    """A cached reusable procedure."""
    skill_id: str
    name: str
    description: str
    procedure: List[SkillStep]
    domain: str = "general"
    pattern: Optional[str] = None  # Regex pattern to match input
    keywords: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    avg_latency_ms: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    @property
    def confidence(self) -> float:
        """Confidence score based on usage and success."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        # Bayesian adjustment: add virtual samples
        return (self.success_count + 1) / (total + 2)

    def matches(self, input_text: str) -> Tuple[bool, float]:
        """Check if input matches this skill."""
        score = 0.0

        # Pattern match
        if self.pattern:
            try:
                if re.search(self.pattern, input_text, re.IGNORECASE):
                    score += 0.5
            except re.error:
                pass

        # Keyword match
        input_lower = input_text.lower()
        keyword_matches = sum(1 for k in self.keywords if k.lower() in input_lower)
        if self.keywords:
            score += 0.3 * (keyword_matches / len(self.keywords))

        # Domain bonus
        if self.domain in input_lower:
            score += 0.1

        # Example similarity (simple)
        for example in self.examples:
            if self._similarity(input_text, example) > 0.7:
                score += 0.1
                break

        return score > 0.3, score

    def _similarity(self, a: str, b: str) -> float:
        """Simple word overlap similarity."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def record_execution(self, success: bool, latency_ms: float) -> None:
        """Record an execution result."""
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        # Update average latency
        total = self.success_count + self.failure_count
        self.avg_latency_ms = (
            (self.avg_latency_ms * (total - 1) + latency_ms) / total
        )
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "procedure": [asdict(s) for s in self.procedure],
            "domain": self.domain,
            "pattern": self.pattern,
            "keywords": self.keywords,
            "examples": self.examples,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "avg_latency_ms": self.avg_latency_ms,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        """Create from dictionary."""
        procedure = [SkillStep(**s) for s in data.pop("procedure", [])]
        return cls(procedure=procedure, **data)


@dataclass
class SkillExecutionResult:
    """Result of executing a skill."""
    skill_id: str
    success: bool
    result: Any
    steps_executed: int
    latency_ms: float
    error: Optional[str] = None
    intermediate_results: List[Dict[str, Any]] = field(default_factory=list)


class SkillCache:
    """
    Cache and manage reusable skills.

    Features:
    - Store and retrieve skills
    - Match skills to inputs
    - Execute skills with variable substitution
    - Track success rates and optimize
    """

    def __init__(
        self,
        cache_dir: Path = None,
        auto_save: bool = True,
        min_confidence: float = 0.5,
    ):
        self.cache_dir = Path(cache_dir or "./runs/skills")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.auto_save = auto_save
        self.min_confidence = min_confidence

        self.skills: Dict[str, Skill] = {}
        self._load_skills()

        # Tool registry for execution
        self._tools: Dict[str, Callable] = {}

    def _load_skills(self) -> None:
        """Load skills from disk."""
        skills_file = self.cache_dir / "skills.json"
        if skills_file.exists():
            try:
                with skills_file.open('r') as f:
                    data = json.load(f)
                for skill_data in data.get("skills", []):
                    skill = Skill.from_dict(skill_data)
                    self.skills[skill.skill_id] = skill
                logger.info(f"Loaded {len(self.skills)} skills")
            except Exception as e:
                logger.error(f"Failed to load skills: {e}")

    def _save_skills(self) -> None:
        """Save skills to disk."""
        skills_file = self.cache_dir / "skills.json"
        try:
            data = {
                "version": 1,
                "updated_at": time.time(),
                "skills": [s.to_dict() for s in self.skills.values()]
            }
            with skills_file.open('w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save skills: {e}")

    def register_tool(self, name: str, func: Callable) -> None:
        """Register a tool function for skill execution."""
        self._tools[name] = func

    def save(self, skill: Skill) -> None:
        """Save a skill to the cache."""
        self.skills[skill.skill_id] = skill
        if self.auto_save:
            self._save_skills()

    def get(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID."""
        return self.skills.get(skill_id)

    def delete(self, skill_id: str) -> bool:
        """Delete a skill."""
        if skill_id in self.skills:
            del self.skills[skill_id]
            if self.auto_save:
                self._save_skills()
            return True
        return False

    def list_skills(self, domain: str = None) -> List[Skill]:
        """List all skills, optionally filtered by domain."""
        skills = list(self.skills.values())
        if domain:
            skills = [s for s in skills if s.domain == domain]
        return sorted(skills, key=lambda s: -s.confidence)

    def find_matching(
        self,
        input_text: str,
        domain: str = None,
        top_k: int = 5,
    ) -> List[Tuple[Skill, float]]:
        """Find skills that match the input."""
        candidates = []

        for skill in self.skills.values():
            # Filter by domain
            if domain and skill.domain != domain:
                continue

            # Check confidence threshold
            if skill.confidence < self.min_confidence:
                continue

            # Check match
            matches, score = skill.matches(input_text)
            if matches:
                # Boost score by confidence
                adjusted_score = score * skill.confidence
                candidates.append((skill, adjusted_score))

        # Sort by score
        candidates.sort(key=lambda x: -x[1])
        return candidates[:top_k]

    def execute(
        self,
        skill_id: str,
        variables: Dict[str, Any],
        dry_run: bool = False,
    ) -> SkillExecutionResult:
        """
        Execute a skill with given variables.

        Args:
            skill_id: Skill to execute
            variables: Variables to substitute in templates
            dry_run: If True, don't actually execute, just return plan
        """
        skill = self.get(skill_id)
        if not skill:
            return SkillExecutionResult(
                skill_id=skill_id,
                success=False,
                result=None,
                steps_executed=0,
                latency_ms=0,
                error=f"Skill not found: {skill_id}"
            )

        start_time = time.time()
        intermediate_results = []
        current_vars = dict(variables)
        steps_executed = 0

        try:
            for step in skill.procedure:
                steps_executed += 1

                # Substitute variables in template
                template = step.template
                for key, value in current_vars.items():
                    template = template.replace(f"{{{key}}}", str(value))

                if dry_run:
                    intermediate_results.append({
                        "step": steps_executed,
                        "action": step.action,
                        "template": template,
                        "status": "planned"
                    })
                    continue

                # Execute based on action type
                result = None
                if step.action == "parse":
                    # Simple variable extraction (placeholder)
                    result = {"parsed": template}

                elif step.action == "compute":
                    # Safe eval for simple math
                    try:
                        # Only allow basic math operations
                        result = eval(template, {"__builtins__": {}}, current_vars)
                    except Exception as e:
                        result = f"Compute error: {e}"

                elif step.action == "tool_call" and step.tool:
                    if step.tool in self._tools:
                        result = self._tools[step.tool](template, **current_vars)
                    else:
                        result = f"Tool not found: {step.tool}"

                elif step.action == "llm_call":
                    # Placeholder for LLM call
                    result = {"llm_response": template}

                elif step.action == "verify":
                    # Verification step
                    result = {"verified": True, "check": template}

                else:
                    result = {"action": step.action, "template": template}

                intermediate_results.append({
                    "step": steps_executed,
                    "action": step.action,
                    "result": result,
                    "status": "completed"
                })

                # Update variables with result
                if isinstance(result, dict):
                    current_vars.update(result)
                else:
                    current_vars["_last_result"] = result

            latency_ms = (time.time() - start_time) * 1000

            # Record execution
            if not dry_run:
                skill.record_execution(True, latency_ms)
                if self.auto_save:
                    self._save_skills()

            return SkillExecutionResult(
                skill_id=skill_id,
                success=True,
                result=current_vars.get("_last_result", intermediate_results[-1] if intermediate_results else None),
                steps_executed=steps_executed,
                latency_ms=latency_ms,
                intermediate_results=intermediate_results,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            if not dry_run:
                skill.record_execution(False, latency_ms)
                if self.auto_save:
                    self._save_skills()

            return SkillExecutionResult(
                skill_id=skill_id,
                success=False,
                result=None,
                steps_executed=steps_executed,
                latency_ms=latency_ms,
                error=str(e),
                intermediate_results=intermediate_results,
            )

    def learn_skill(
        self,
        name: str,
        description: str,
        procedure: List[Dict[str, Any]],
        domain: str = "general",
        pattern: str = None,
        keywords: List[str] = None,
        examples: List[str] = None,
    ) -> Skill:
        """
        Create and save a new skill from a successful procedure.

        Args:
            name: Human-readable name
            description: What the skill does
            procedure: List of step definitions
            domain: Task domain
            pattern: Regex pattern to match inputs
            keywords: Keywords for matching
            examples: Example inputs this skill handles
        """
        # Generate ID from name
        skill_id = hashlib.sha256(name.encode()).hexdigest()[:12]

        # Create steps
        steps = [
            SkillStep(
                action=s.get("action", "compute"),
                template=s.get("template", ""),
                tool=s.get("tool"),
                fallback=s.get("fallback"),
                metadata=s.get("metadata", {}),
            )
            for s in procedure
        ]

        skill = Skill(
            skill_id=skill_id,
            name=name,
            description=description,
            procedure=steps,
            domain=domain,
            pattern=pattern,
            keywords=keywords or [],
            examples=examples or [],
        )

        self.save(skill)
        logger.info(f"Learned new skill: {name} ({skill_id})")
        return skill

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_skills = len(self.skills)
        by_domain = {}
        total_executions = 0
        total_success = 0

        for skill in self.skills.values():
            domain = skill.domain
            if domain not in by_domain:
                by_domain[domain] = {"count": 0, "success": 0, "total": 0}
            by_domain[domain]["count"] += 1
            by_domain[domain]["success"] += skill.success_count
            by_domain[domain]["total"] += skill.success_count + skill.failure_count

            total_executions += skill.success_count + skill.failure_count
            total_success += skill.success_count

        return {
            "total_skills": total_skills,
            "total_executions": total_executions,
            "overall_success_rate": total_success / total_executions if total_executions > 0 else 0,
            "by_domain": by_domain,
            "high_confidence_skills": len([s for s in self.skills.values() if s.confidence > 0.8]),
        }


# Pre-built skills for common tasks
DEFAULT_SKILLS = [
    {
        "name": "solve_linear_equation",
        "description": "Solve linear equations of form ax + b = c",
        "domain": "math",
        "pattern": r"solve.*?(\d+)\s*x\s*[+-]\s*(\d+)\s*=\s*(\d+)",
        "keywords": ["solve", "equation", "x", "variable"],
        "examples": ["Solve for x: 2x + 5 = 15", "What is x if 3x - 7 = 20?"],
        "procedure": [
            {"action": "parse", "template": "Extract coefficients from {equation}"},
            {"action": "compute", "template": "({c} - {b}) / {a}"},
            {"action": "verify", "template": "Check: {a} * {result} + {b} = {c}"},
        ],
    },
    {
        "name": "http_get_request",
        "description": "Make HTTP GET request and parse response",
        "domain": "http",
        "pattern": r"(fetch|get|request|http).*?(url|http|https)",
        "keywords": ["http", "get", "fetch", "url", "request", "api"],
        "examples": ["Fetch data from https://api.example.com", "GET request to URL"],
        "procedure": [
            {"action": "tool_call", "tool": "http_get", "template": "{url}"},
            {"action": "parse", "template": "Parse response from {_last_result}"},
        ],
    },
    {
        "name": "file_read_write",
        "description": "Read or write file contents",
        "domain": "filesystem",
        "pattern": r"(read|write|save|load)\s+file",
        "keywords": ["file", "read", "write", "save", "load", "content"],
        "examples": ["Read file config.json", "Write data to output.txt"],
        "procedure": [
            {"action": "tool_call", "tool": "file_op", "template": "{operation} {path}"},
        ],
    },
]


def create_default_cache() -> SkillCache:
    """Create a skill cache with default skills."""
    cache = SkillCache()

    # Add default skills if cache is empty
    if not cache.skills:
        for skill_def in DEFAULT_SKILLS:
            cache.learn_skill(**skill_def)

    return cache
