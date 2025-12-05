"""
Multi-turn dialogue support for Agent0.

Enables extended interaction sequences between agents
and within agent reasoning chains.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent0.models.factory import create_model
from agent0.tasks.schema import TaskSpec, Trajectory

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A single message in a conversation."""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: List[Dict] = field(default_factory=list)
    tool_result: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """A multi-turn conversation."""
    id: str
    messages: List[Message] = field(default_factory=list)
    max_turns: int = 10
    current_turn: int = 0

    def add_message(self, role: str, content: str, **kwargs) -> None:
        """Add a message to the conversation."""
        self.messages.append(Message(role=role, content=content, **kwargs))
        if role in ("user", "assistant"):
            self.current_turn += 1

    def get_context(self, max_tokens: int = 4096) -> str:
        """Get conversation context as formatted string."""
        context_parts = []

        for msg in self.messages:
            if msg.role == "system":
                context_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                context_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                context_parts.append(f"Assistant: {msg.content}")
            elif msg.role == "tool":
                context_parts.append(f"Tool Result: {msg.content}")

        return "\n\n".join(context_parts)

    def is_complete(self) -> bool:
        """Check if conversation has reached max turns."""
        return self.current_turn >= self.max_turns

    def get_last_assistant_message(self) -> Optional[str]:
        """Get the last assistant message."""
        for msg in reversed(self.messages):
            if msg.role == "assistant":
                return msg.content
        return None


class MultiTurnAgent:
    """
    Agent capable of multi-turn reasoning and dialogue.

    Extends the basic agent with:
    - Conversation history tracking
    - Reflection and self-correction
    - Tool result integration
    - Iterative refinement
    """

    REFLECTION_PROMPT = """
Based on the previous attempt:
{previous_response}

The result was: {result}

Please reflect on this and provide an improved response.
Consider:
1. What worked well?
2. What could be improved?
3. Are there alternative approaches?

Provide your refined solution:
"""

    CONTINUATION_PROMPT = """
Continue the reasoning from where you left off:
{context}

Previous conclusion: {last_response}

Now continue to the next step:
"""

    def __init__(
        self,
        model_config: Dict[str, Any],
        max_turns: int = 5,
        enable_reflection: bool = True,
        tool_config: Optional[Dict[str, Any]] = None,
    ):
        self.model_config = model_config
        self.model = create_model(model_config)
        self.max_turns = max_turns
        self.enable_reflection = enable_reflection
        self.tool_config = tool_config or {}

        # Active conversations
        self.conversations: Dict[str, Conversation] = {}

    def start_conversation(self, task_id: str, system_prompt: str = "") -> Conversation:
        """Start a new conversation."""
        conv = Conversation(id=task_id, max_turns=self.max_turns)

        if system_prompt:
            conv.add_message("system", system_prompt)

        self.conversations[task_id] = conv
        logger.info(f"Started conversation {task_id}")
        return conv

    def generate_response(
        self,
        conversation: Conversation,
        user_input: str,
        include_context: bool = True,
    ) -> str:
        """Generate a response in the conversation."""
        # Add user message
        conversation.add_message("user", user_input)

        # Build prompt with context
        if include_context:
            prompt = conversation.get_context()
            prompt += f"\n\nAssistant:"
        else:
            prompt = user_input

        # Generate response
        response = self.model.generate(
            prompt,
            max_tokens=self.model_config.get("max_tokens", 512),
            temperature=self.model_config.get("temperature", 0.7),
            top_p=self.model_config.get("top_p", 0.9),
        )

        # Add assistant message
        conversation.add_message("assistant", response.strip())

        return response.strip()

    def reflect_and_refine(
        self,
        conversation: Conversation,
        previous_response: str,
        result: str,
    ) -> str:
        """Reflect on a result and generate refined response."""
        if not self.enable_reflection:
            return previous_response

        reflection_prompt = self.REFLECTION_PROMPT.format(
            previous_response=previous_response,
            result=result,
        )

        refined = self.generate_response(conversation, reflection_prompt)
        logger.info(f"Reflection generated for {conversation.id}")

        return refined

    def multi_step_solve(
        self,
        task: TaskSpec,
        tool_executor: Optional[callable] = None,
    ) -> Trajectory:
        """
        Solve a task using multi-turn reasoning.

        Args:
            task: Task to solve
            tool_executor: Optional function to execute tool calls

        Returns:
            Trajectory with full conversation history
        """
        # Start conversation
        conv = self.start_conversation(task.task_id, system_prompt=self._get_system_prompt(task))

        all_tool_calls = []
        metrics = {"turns": 0, "tool_calls": 0, "reflections": 0}

        # Initial response
        initial_prompt = self._format_task_prompt(task)
        response = self.generate_response(conv, initial_prompt)
        metrics["turns"] += 1

        # Check for tool calls in response
        tool_calls = self._extract_tool_calls(response)

        # Multi-turn loop
        while not conv.is_complete() and tool_calls:
            all_tool_calls.extend(tool_calls)
            metrics["tool_calls"] += len(tool_calls)

            # Execute tools if executor provided
            if tool_executor:
                tool_results = []
                for call in tool_calls:
                    result = tool_executor(call)
                    tool_results.append(f"{call.get('tool', 'unknown')}: {result}")
                    conv.add_message("tool", str(result), tool_result=str(result))

                # Generate next response based on tool results
                continuation = f"Tool results:\n" + "\n".join(tool_results) + "\n\nContinue your solution:"
                response = self.generate_response(conv, continuation)
                metrics["turns"] += 1

            # Check for more tool calls
            tool_calls = self._extract_tool_calls(response)

            # Reflection step if enabled and we have a result
            if self.enable_reflection and not tool_calls and metrics["turns"] > 1:
                response = self.reflect_and_refine(conv, response, "preliminary result")
                metrics["reflections"] += 1

        # Extract final answer
        final_answer = self._extract_final_answer(response)

        return Trajectory(
            task=task,
            messages=[{"role": m.role, "content": m.content} for m in conv.messages],
            tool_calls=all_tool_calls,
            result=final_answer,
            success=bool(final_answer),
            reward={"total": 0.0},
            metrics=metrics,
        )

    def _get_system_prompt(self, task: TaskSpec) -> str:
        """Generate system prompt based on task domain."""
        base = "You are a helpful assistant that solves problems step by step."

        if task.domain == "math":
            return base + " For math problems, show your work and box your final answer."
        elif task.domain == "code":
            return base + " For coding problems, provide working code with explanations."
        elif task.domain == "logic":
            return base + " For logic problems, explain your reasoning clearly."

        return base

    def _format_task_prompt(self, task: TaskSpec) -> str:
        """Format task as initial prompt."""
        prompt = f"Problem: {task.prompt}"

        if task.constraints:
            prompt += f"\n\nConstraints:\n" + "\n".join(f"- {c}" for c in task.constraints)

        prompt += "\n\nProvide your solution step by step."
        return prompt

    def _extract_tool_calls(self, response: str) -> List[Dict]:
        """Extract tool calls from response."""
        import re

        tool_calls = []

        # Look for Action: pattern
        action_match = re.search(r'Action:\s*(\w+)\s*\n.*?Action Input:\s*(.+?)(?:\n|$)', response, re.DOTALL)
        if action_match:
            tool_calls.append({
                "tool": action_match.group(1).lower(),
                "input": action_match.group(2).strip(),
            })

        # Look for ```python blocks as code tool calls
        code_matches = re.findall(r'```python\n(.+?)```', response, re.DOTALL)
        for code in code_matches:
            tool_calls.append({
                "tool": "python",
                "input": code.strip(),
            })

        return tool_calls

    def _extract_final_answer(self, response: str) -> str:
        """Extract final answer from response."""
        import re

        # Look for boxed answer
        match = re.search(r'\\boxed\{([^}]+)\}', response)
        if match:
            return match.group(1).strip()

        # Look for "Answer:" or "Final answer:"
        match = re.search(r'(?:Final )?[Aa]nswer[:\s]+(.+?)(?:\n|$)', response)
        if match:
            return match.group(1).strip()

        # Look for last number
        numbers = re.findall(r'[+-]?\d+\.?\d*', response)
        if numbers:
            return numbers[-1]

        # Return last non-empty line
        lines = [l.strip() for l in response.split('\n') if l.strip()]
        return lines[-1] if lines else ""

    def get_conversation(self, task_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return self.conversations.get(task_id)

    def clear_conversation(self, task_id: str) -> None:
        """Clear a conversation."""
        if task_id in self.conversations:
            del self.conversations[task_id]


class TeacherStudentDialogue:
    """
    Facilitates multi-turn dialogue between teacher and student agents.

    Implements the symbiotic competition through iterative refinement:
    1. Teacher proposes task
    2. Student attempts solution
    3. Teacher provides feedback
    4. Student refines solution
    """

    def __init__(
        self,
        teacher_config: Dict[str, Any],
        student_config: Dict[str, Any],
        max_refinements: int = 3,
    ):
        self.teacher = MultiTurnAgent(teacher_config, max_turns=max_refinements * 2)
        self.student = MultiTurnAgent(student_config, max_turns=max_refinements * 2)
        self.max_refinements = max_refinements

    def run_dialogue(
        self,
        task: TaskSpec,
        verifier_fn: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Run a multi-turn dialogue between teacher and student.

        Args:
            task: Initial task
            verifier_fn: Optional function to verify solutions

        Returns:
            Dictionary with dialogue history and final result
        """
        dialogue_history = []
        final_result = None
        refinement_count = 0

        # Start conversations
        teacher_conv = self.teacher.start_conversation(
            f"teacher_{task.task_id}",
            system_prompt="You are a teacher agent that evaluates solutions and provides constructive feedback."
        )
        student_conv = self.student.start_conversation(
            f"student_{task.task_id}",
            system_prompt="You are a student agent that solves problems and learns from feedback."
        )

        # Initial student attempt
        student_response = self.student.generate_response(
            student_conv,
            f"Solve this problem: {task.prompt}"
        )
        dialogue_history.append({"agent": "student", "content": student_response})

        # Refinement loop
        while refinement_count < self.max_refinements:
            # Teacher evaluates
            teacher_feedback = self.teacher.generate_response(
                teacher_conv,
                f"Evaluate this solution to '{task.prompt}':\n\n{student_response}\n\nProvide specific feedback."
            )
            dialogue_history.append({"agent": "teacher", "content": teacher_feedback})

            # Check if solution is acceptable
            if verifier_fn:
                verification = verifier_fn(task, student_response)
                if verification.get("status") == "pass":
                    final_result = student_response
                    break

            # Check for approval in teacher feedback
            if any(word in teacher_feedback.lower() for word in ["correct", "excellent", "well done", "approved"]):
                final_result = student_response
                break

            # Student refines based on feedback
            student_response = self.student.generate_response(
                student_conv,
                f"Teacher feedback: {teacher_feedback}\n\nPlease refine your solution."
            )
            dialogue_history.append({"agent": "student", "content": student_response})

            refinement_count += 1

        if final_result is None:
            final_result = student_response  # Use last attempt

        return {
            "task": task.task_id,
            "final_result": final_result,
            "refinements": refinement_count,
            "dialogue_history": dialogue_history,
            "success": final_result is not None,
        }
