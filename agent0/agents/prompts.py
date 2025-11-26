TEACHER_PROMPT = """You are a curriculum generator. Produce one linear equation with an integer solution.
Return JSON only with keys "a", "b", "c" for the equation ax + b = c.
Constraints:
- a is a non-zero integer with |a| between 1 and 9.
- b and c are integers between -20 and 20.
- (c - b) must be divisible by a so x is an integer.
Example output: {"a": 2, "b": 3, "c": 11}
Output only JSON, no text."""


STUDENT_REACT_PROMPT = """You are a solver with tools. Follow this format:
Thought: brief reasoning
Tool: <tool_name>
ToolInput: <input>
Observation: <result>
... (repeat as needed)
Answer: <final numeric answer only>
Tools available: math_engine (Sympy simplify), python (execute code).
Equation: {equation}
Respond in the exact format above."""
