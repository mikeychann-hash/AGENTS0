import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent0.agents.student import StudentAgent
from agent0.rewards.calculator import RewardCalculator, RewardWeights
from agent0.tasks.schema import TaskSpec, Trajectory
from agent0.tools import math_engine, python_runner
from agent0.tools.sandbox import limit_resources


def test_number_extraction_basic():
    agent = StudentAgent({"backend": "dummy"})
    assert agent._extract_number("The answer is 42") == "42"
    assert agent._extract_number("x = 3.14") == "3.14"
    assert agent._extract_number("negative -5") == "-5"


def test_sandbox_is_noop():
    with limit_resources():
        pass  # should not raise in local mode


def test_python_runner_executes_locally(tmp_path):
    result = python_runner.run_python("print('hello')", timeout=5, workdir=str(tmp_path))
    assert result["status"] == "ok"
    assert "hello" in result["stdout"]


def test_math_engine_safe():
    result = math_engine.solve_expression("2 + 2")
    assert result["status"] == "ok"
    assert "4" in result["result"]


def test_reward_includes_correctness():
    weights = RewardWeights()
    calc = RewardCalculator(weights)
    task = TaskSpec(task_id="t1", domain="math", prompt="1+1")
    traj = Trajectory(
        task=task,
        messages=[],
        tool_calls=[],
        result="2",
        success=True,
        reward={},
        metrics={},
    )
    reward = calc.compute(traj, success_prob=0.5, novelty_sig="math:1")
    assert "correctness" in reward
    assert reward["correctness"] > 0


def test_verifier_accepts_numeric_equivalence():
    from agent0.tasks.verifier import verify
    from agent0.tasks.schema import VerifierSpec

    task = TaskSpec(
        task_id="t2",
        domain="math",
        prompt="",
        verifier=VerifierSpec(kind="expected_number", spec={"answer": "6.0"}),
    )
    result = verify(task, "6")
    assert result["status"] == "pass"
