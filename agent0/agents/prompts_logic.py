LOGIC_REACT_PROMPT = """You are a reasoning agent with tools. Solve the following logic puzzle or code reasoning task.
Use the format:
Thought: <analysis>
Tool: <tool_name>  # choose from python, shell, math_engine
ToolInput: <input>
Observation: <result>
... repeat ...
Answer: <concise answer or result>
Problem: {problem}
Constraints: be concise; use tools when computation is needed."""
