"""
Agent0 Storage Module.

Provides persistent storage for:
- Traces: Full execution logs with summaries
- Skills: Cached reusable procedures
"""
from agent0.storage.trace_store import (
    TraceStore,
    Trace,
    TraceStep,
    TraceSummary,
    TraceContext,
)
from agent0.storage.skill_cache import (
    SkillCache,
    Skill,
    SkillStep as SkillProcedureStep,
    SkillExecutionResult,
    create_default_cache,
)

__all__ = [
    # Traces
    'TraceStore',
    'Trace',
    'TraceStep',
    'TraceSummary',
    'TraceContext',
    # Skills
    'SkillCache',
    'Skill',
    'SkillProcedureStep',
    'SkillExecutionResult',
    'create_default_cache',
]
