#!/usr/bin/env python3
"""
Agent0 Trace Storage System.

Provides local storage for full agent traces with:
- Redis backend (fast, structured)
- File backend (simple, portable)
- Summary extraction for external systems
- Trace compression and rotation

Usage:
    from agent0.storage.trace_store import TraceStore, Trace

    store = TraceStore(backend="redis")  # or "file"

    trace = Trace(task_id="task-001", ...)
    store.save(trace)

    summary = store.get_summary("task-001")
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class TraceStep:
    """A single step in an agent trace."""
    step_id: int
    timestamp: float
    action_type: str  # "llm_call", "tool_call", "reasoning", "decision"
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    latency_ms: float
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Trace:
    """Complete trace of an agent execution."""
    trace_id: str
    task_id: str
    start_time: float
    end_time: float = 0.0
    domain: str = "general"
    success: bool = False
    result: str = ""
    steps: List[TraceStep] = field(default_factory=list)
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: TraceStep) -> None:
        """Add a step to the trace."""
        self.steps.append(step)
        self.total_tokens += step.tokens_used
        self.total_latency_ms += step.latency_ms

    def finalize(self, success: bool, result: str, error: str = None) -> None:
        """Finalize the trace."""
        self.end_time = time.time()
        self.success = success
        self.result = result
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "domain": self.domain,
            "success": self.success,
            "result": self.result,
            "steps": [asdict(s) for s in self.steps],
            "total_tokens": self.total_tokens,
            "total_latency_ms": self.total_latency_ms,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trace":
        """Create from dictionary."""
        steps = [TraceStep(**s) for s in data.pop("steps", [])]
        return cls(steps=steps, **data)


@dataclass
class TraceSummary:
    """Compact summary of a trace for external systems."""
    trace_id: str
    task_id: str
    domain: str
    success: bool
    result_preview: str  # First 200 chars
    step_count: int
    tool_calls: List[str]
    total_tokens: int
    total_latency_ms: float
    duration_seconds: float
    error_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class TraceBackend(ABC):
    """Abstract base for trace storage backends."""

    @abstractmethod
    def save(self, trace: Trace) -> bool:
        pass

    @abstractmethod
    def load(self, trace_id: str) -> Optional[Trace]:
        pass

    @abstractmethod
    def list_traces(self, limit: int = 100, offset: int = 0) -> List[str]:
        pass

    @abstractmethod
    def delete(self, trace_id: str) -> bool:
        pass

    @abstractmethod
    def search(self, query: Dict[str, Any]) -> List[str]:
        pass


class FileTraceBackend(TraceBackend):
    """File-based trace storage with compression."""

    def __init__(self, base_dir: Path, compress: bool = True, max_traces: int = 1000):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.compress = compress
        self.max_traces = max_traces
        self.index_file = self.base_dir / "index.json"
        self._load_index()

    def _load_index(self) -> None:
        """Load or create trace index."""
        if self.index_file.exists():
            with self.index_file.open('r') as f:
                self.index = json.load(f)
        else:
            self.index = {"traces": [], "metadata": {}}

    def _save_index(self) -> None:
        """Save trace index."""
        with self.index_file.open('w') as f:
            json.dump(self.index, f, indent=2)

    def _get_trace_path(self, trace_id: str) -> Path:
        """Get path for a trace file."""
        ext = ".json.gz" if self.compress else ".json"
        return self.base_dir / f"{trace_id}{ext}"

    def save(self, trace: Trace) -> bool:
        """Save trace to file."""
        try:
            path = self._get_trace_path(trace.trace_id)
            data = json.dumps(trace.to_dict(), indent=2)

            if self.compress:
                with gzip.open(path, 'wt', encoding='utf-8') as f:
                    f.write(data)
            else:
                with path.open('w') as f:
                    f.write(data)

            # Update index
            entry = {
                "trace_id": trace.trace_id,
                "task_id": trace.task_id,
                "domain": trace.domain,
                "success": trace.success,
                "timestamp": trace.start_time,
            }

            # Remove old entry if exists
            self.index["traces"] = [
                t for t in self.index["traces"]
                if t["trace_id"] != trace.trace_id
            ]
            self.index["traces"].insert(0, entry)

            # Enforce max traces
            if len(self.index["traces"]) > self.max_traces:
                old_traces = self.index["traces"][self.max_traces:]
                self.index["traces"] = self.index["traces"][:self.max_traces]
                for old in old_traces:
                    self.delete(old["trace_id"])

            self._save_index()
            return True

        except Exception as e:
            logger.error(f"Failed to save trace {trace.trace_id}: {e}")
            return False

    def load(self, trace_id: str) -> Optional[Trace]:
        """Load trace from file."""
        path = self._get_trace_path(trace_id)

        if not path.exists():
            # Try without compression
            path = self.base_dir / f"{trace_id}.json"
            if not path.exists():
                return None

        try:
            if path.suffix == ".gz":
                with gzip.open(path, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with path.open('r') as f:
                    data = json.load(f)

            return Trace.from_dict(data)

        except Exception as e:
            logger.error(f"Failed to load trace {trace_id}: {e}")
            return None

    def list_traces(self, limit: int = 100, offset: int = 0) -> List[str]:
        """List trace IDs."""
        return [
            t["trace_id"]
            for t in self.index["traces"][offset:offset + limit]
        ]

    def delete(self, trace_id: str) -> bool:
        """Delete a trace."""
        path = self._get_trace_path(trace_id)
        try:
            if path.exists():
                path.unlink()
            self.index["traces"] = [
                t for t in self.index["traces"]
                if t["trace_id"] != trace_id
            ]
            self._save_index()
            return True
        except Exception as e:
            logger.error(f"Failed to delete trace {trace_id}: {e}")
            return False

    def search(self, query: Dict[str, Any]) -> List[str]:
        """Search traces by criteria."""
        results = []
        for entry in self.index["traces"]:
            match = True
            for key, value in query.items():
                if entry.get(key) != value:
                    match = False
                    break
            if match:
                results.append(entry["trace_id"])
        return results


class RedisTraceBackend(TraceBackend):
    """Redis-based trace storage."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        prefix: str = "agent0:trace:",
        ttl: int = 86400 * 7,  # 7 days
    ):
        self.prefix = prefix
        self.ttl = ttl
        self._redis = None

        try:
            import redis
            self._redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            self._redis.ping()
            logger.info(f"Connected to Redis at {host}:{port}")
        except ImportError:
            logger.warning("redis package not installed, falling back to file storage")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, falling back to file storage")

    @property
    def is_available(self) -> bool:
        return self._redis is not None

    def _key(self, trace_id: str) -> str:
        return f"{self.prefix}{trace_id}"

    def save(self, trace: Trace) -> bool:
        if not self._redis:
            return False

        try:
            key = self._key(trace.trace_id)
            data = json.dumps(trace.to_dict())
            self._redis.setex(key, self.ttl, data)

            # Add to sorted set for listing
            self._redis.zadd(
                f"{self.prefix}index",
                {trace.trace_id: trace.start_time}
            )

            # Add to domain index
            self._redis.sadd(f"{self.prefix}domain:{trace.domain}", trace.trace_id)

            return True
        except Exception as e:
            logger.error(f"Redis save failed: {e}")
            return False

    def load(self, trace_id: str) -> Optional[Trace]:
        if not self._redis:
            return None

        try:
            data = self._redis.get(self._key(trace_id))
            if data:
                return Trace.from_dict(json.loads(data))
            return None
        except Exception as e:
            logger.error(f"Redis load failed: {e}")
            return None

    def list_traces(self, limit: int = 100, offset: int = 0) -> List[str]:
        if not self._redis:
            return []

        try:
            return self._redis.zrevrange(
                f"{self.prefix}index",
                offset,
                offset + limit - 1
            )
        except Exception as e:
            logger.error(f"Redis list failed: {e}")
            return []

    def delete(self, trace_id: str) -> bool:
        if not self._redis:
            return False

        try:
            self._redis.delete(self._key(trace_id))
            self._redis.zrem(f"{self.prefix}index", trace_id)
            return True
        except Exception as e:
            logger.error(f"Redis delete failed: {e}")
            return False

    def search(self, query: Dict[str, Any]) -> List[str]:
        if not self._redis:
            return []

        try:
            if "domain" in query:
                return list(self._redis.smembers(f"{self.prefix}domain:{query['domain']}"))
            return self.list_traces()
        except Exception as e:
            logger.error(f"Redis search failed: {e}")
            return []


class TraceStore:
    """
    Main trace storage interface.

    Handles trace storage, retrieval, and summary generation.
    """

    def __init__(
        self,
        backend: str = "auto",
        base_dir: Path = None,
        redis_host: str = "localhost",
        redis_port: int = 6379,
    ):
        self.base_dir = Path(base_dir or "./runs/traces")

        if backend == "auto":
            # Try Redis first, fall back to file
            redis_backend = RedisTraceBackend(redis_host, redis_port)
            if redis_backend.is_available:
                self._backend = redis_backend
                self._backend_type = "redis"
            else:
                self._backend = FileTraceBackend(self.base_dir)
                self._backend_type = "file"
        elif backend == "redis":
            self._backend = RedisTraceBackend(redis_host, redis_port)
            self._backend_type = "redis"
        else:
            self._backend = FileTraceBackend(self.base_dir)
            self._backend_type = "file"

        logger.info(f"TraceStore initialized with {self._backend_type} backend")

    def save(self, trace: Trace) -> bool:
        """Save a trace."""
        return self._backend.save(trace)

    def load(self, trace_id: str) -> Optional[Trace]:
        """Load a trace."""
        return self._backend.load(trace_id)

    def list_traces(self, limit: int = 100, offset: int = 0) -> List[str]:
        """List trace IDs."""
        return self._backend.list_traces(limit, offset)

    def delete(self, trace_id: str) -> bool:
        """Delete a trace."""
        return self._backend.delete(trace_id)

    def search(self, **kwargs) -> List[str]:
        """Search for traces."""
        return self._backend.search(kwargs)

    def get_summary(self, trace_id: str) -> Optional[TraceSummary]:
        """Get a compact summary of a trace."""
        trace = self.load(trace_id)
        if not trace:
            return None

        # Extract tool calls
        tool_calls = [
            s.action_type for s in trace.steps
            if s.action_type.startswith("tool_")
        ]

        # Create preview
        result_preview = trace.result[:200] if trace.result else ""
        if len(trace.result) > 200:
            result_preview += "..."

        # Error summary
        error_summary = None
        if trace.error:
            error_summary = trace.error[:100]

        return TraceSummary(
            trace_id=trace.trace_id,
            task_id=trace.task_id,
            domain=trace.domain,
            success=trace.success,
            result_preview=result_preview,
            step_count=len(trace.steps),
            tool_calls=tool_calls,
            total_tokens=trace.total_tokens,
            total_latency_ms=trace.total_latency_ms,
            duration_seconds=trace.end_time - trace.start_time if trace.end_time else 0,
            error_summary=error_summary,
        )

    def get_summaries(self, limit: int = 10) -> List[TraceSummary]:
        """Get summaries for recent traces."""
        trace_ids = self.list_traces(limit)
        summaries = []
        for tid in trace_ids:
            summary = self.get_summary(tid)
            if summary:
                summaries.append(summary)
        return summaries


class TraceContext:
    """Context manager for tracing agent execution."""

    def __init__(self, store: TraceStore, task_id: str, domain: str = "general"):
        self.store = store
        self.task_id = task_id
        self.domain = domain
        self.trace = None
        self._step_counter = 0

    def __enter__(self) -> "TraceContext":
        trace_id = f"{self.task_id}_{int(time.time() * 1000)}"
        self.trace = Trace(
            trace_id=trace_id,
            task_id=self.task_id,
            start_time=time.time(),
            domain=self.domain,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.trace.finalize(False, "", str(exc_val))
        self.store.save(self.trace)

    def add_step(
        self,
        action_type: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        latency_ms: float = 0,
        tokens: int = 0,
        **metadata
    ) -> None:
        """Add a step to the current trace."""
        self._step_counter += 1
        step = TraceStep(
            step_id=self._step_counter,
            timestamp=time.time(),
            action_type=action_type,
            input_data=input_data,
            output_data=output_data,
            latency_ms=latency_ms,
            tokens_used=tokens,
            metadata=metadata,
        )
        self.trace.add_step(step)

    def finalize(self, success: bool, result: str, error: str = None) -> None:
        """Finalize the trace."""
        self.trace.finalize(success, result, error)
