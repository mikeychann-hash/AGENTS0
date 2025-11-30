"""
Tool composition framework for multi-turn, chained tool execution.

Allows tools to use outputs from previous tools as inputs,
enabling complex multi-step reasoning and computation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ToolStep:
    """Single step in a tool execution plan"""
    step_id: str
    tool: str
    input: str
    depends_on: Optional[List[str]] = None  # IDs of steps this depends on
    result: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, running, success, failed
    

class ToolComposer:
    """
    Compose multiple tool calls into a coherent execution plan.
    
    Features:
    - Dependency resolution
    - Result passing between tools
    - Error handling and recovery
    - Execution logging
    """
    
    def __init__(self, tools_registry: Dict[str, callable]):
        """
        Args:
            tools_registry: Map of tool name -> tool function
        """
        self.tools = tools_registry
        self.execution_history: List[ToolStep] = []
    
    def execute_plan(
        self,
        steps: List[ToolStep],
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Execute a multi-step tool plan with dependency resolution.
        
        Args:
            steps: List of tool steps to execute
            max_retries: Max retries per step on failure
            
        Returns:
            Dict with results from all steps
        """
        results = {}
        execution_order = self._resolve_dependencies(steps)
        
        logger.info(f"Executing {len(steps)} tool steps in order: {execution_order}")
        
        for step_id in execution_order:
            step = next(s for s in steps if s.step_id == step_id)
            
            logger.info(f"Executing step {step_id}: {step.tool}")
            step.status = "running"
            
            # Prepare input with dependency results
            tool_input = self._prepare_input(step, results)
            
            # Execute tool with retries
            for attempt in range(max_retries + 1):
                try:
                    result = self._execute_tool(step.tool, tool_input)
                    
                    step.result = result
                    step.status = "success"
                    results[step_id] = result
                    
                    logger.info(f"Step {step_id} succeeded: {result.get('status')}")
                    break
                    
                except Exception as e:
                    if attempt < max_retries:
                        logger.warning(f"Step {step_id} failed (attempt {attempt+1}/{max_retries}): {e}")
                    else:
                        logger.error(f"Step {step_id} failed after {max_retries} retries: {e}")
                        step.status = "failed"
                        step.result = {"status": "error", "error": str(e)}
                        results[step_id] = step.result
            
            self.execution_history.append(step)
        
        return results
    
    def _resolve_dependencies(self, steps: List[ToolStep]) -> List[str]:
        """
        Topological sort of steps based on dependencies.
        
        Returns:
            Execution order (list of step IDs)
        """
        # Build dependency graph
        graph = {s.step_id: s.depends_on or [] for s in steps}
        
        # Topological sort (Kahn's algorithm)
        in_degree = {s_id: 0 for s_id in graph}
        for deps in graph.values():
            for dep in deps:
                in_degree[dep] = in_degree.get(dep, 0) + 1
        
        # Start with nodes with no dependencies
        queue = [s_id for s_id, degree in in_degree.items() if degree == 0]
        order = []
        
        while queue:
            current = queue.pop(0)
            order.append(current)
            
            # Reduce in-degree for dependent nodes
            for s_id, deps in graph.items():
                if current in deps:
                    in_degree[s_id] -= 1
                    if in_degree[s_id] == 0:
                        queue.append(s_id)
        
        if len(order) != len(steps):
            raise ValueError("Circular dependency detected in tool plan")
        
        return order
    
    def _prepare_input(
        self,
        step: ToolStep,
        results: Dict[str, Any]
    ) -> str:
        """
        Prepare input for a step, incorporating dependency results.
        
        Replaces references like {{step_1.result}} with actual values.
        """
        tool_input = step.input
        
        # If step has dependencies, inject their results
        if step.depends_on:
            for dep_id in step.depends_on:
                if dep_id in results:
                    dep_result = results[dep_id]
                    
                    # Extract relevant result field
                    if isinstance(dep_result, dict):
                        result_value = dep_result.get("result") or dep_result.get("stdout") or str(dep_result)
                    else:
                        result_value = str(dep_result)
                    
                    # Replace references in input
                    placeholder = f"{{{{{dep_id}.result}}}}"
                    tool_input = tool_input.replace(placeholder, result_value)
        
        return tool_input
    
    def _execute_tool(self, tool_name: str, tool_input: str) -> Dict[str, Any]:
        """
        Execute a single tool.
        
        Args:
            tool_name: Name of tool to execute
            tool_input: Input string for tool
            
        Returns:
            Tool result dict
        """
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool_func = self.tools[tool_name]
        result = tool_func(tool_input)
        
        if not isinstance(result, dict):
            result = {"result": result, "status": "ok"}
        
        return result


def parse_tool_plan_from_text(text: str) -> List[ToolStep]:
    """
    Parse a tool execution plan from LLM-generated text.
    
    Expected format:
    Step 1: tool=python, input="print(2+2)", depends_on=[]
    Step 2: tool=math, input="sqrt({{step_1.result}})", depends_on=[step_1]
    
    Returns:
        List of ToolSteps
    """
    import re
    
    steps = []
    lines = text.strip().split('\n')
    
    for line in lines:
        # Match pattern: Step X: tool=Y, input="Z", depends_on=[...]
        match = re.search(
            r'Step\s+(\S+):\s+tool=(\w+),\s+input="([^"]+)"(?:,\s+depends_on=\[([^\]]*)\])?',
            line
        )
        
        if match:
            step_id = f"step_{match.group(1)}"
            tool = match.group(2)
            tool_input = match.group(3)
            depends_str = match.group(4)
            
            depends_on = []
            if depends_str:
                depends_on = [
                    f"step_{dep.strip()}"
                    for dep in depends_str.split(',')
                    if dep.strip()
                ]
            
            steps.append(ToolStep(
                step_id=step_id,
                tool=tool,
                input=tool_input,
                depends_on=depends_on if depends_on else None
            ))
    
    return steps


# Example usage
if __name__ == "__main__":
    # Example tool registry
    def python_tool(code):
        import subprocess
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=5
        )
        return {
            "status": "ok" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    
    def math_tool(expr):
        import sympy as sp
        result = sp.sympify(expr)
        return {"status": "ok", "result": str(result)}
    
    # Create composer
    composer = ToolComposer({
        "python": python_tool,
        "math": math_tool
    })
    
    # Define multi-step plan
    plan = [
        ToolStep(
            step_id="step_1",
            tool="python",
            input="print(2 ** 8)"
        ),
        ToolStep(
            step_id="step_2",
            tool="math",
            input="sqrt({{step_1.result}})",
            depends_on=["step_1"]
        )
    ]
    
    # Execute
    results = composer.execute_plan(plan)
    print("Results:", results)
