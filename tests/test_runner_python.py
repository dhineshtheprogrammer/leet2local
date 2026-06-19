from leet2local.runners.python_runner import PythonRunner
from leet2local.models import TestCase


SOLUTION_TWO_SUM = """\
from typing import List

class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        seen = {}
        for i, n in enumerate(nums):
            if target - n in seen:
                return [seen[target - n], i]
            seen[n] = i
        return []
"""

SOLUTION_WRONG = """\
from typing import List

class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        return [0, 0]  # always wrong
"""

TEST_CASES = [
    TestCase(
        input={"nums": [2, 7, 11, 15], "target": 9},
        expected_output=[0, 1],
        input_raw="[2,7,11,15]\n9",
        expected_raw="[0,1]",
    ),
    TestCase(
        input={"nums": [3, 2, 4], "target": 6},
        expected_output=[1, 2],
        input_raw="[3,2,4]\n6",
        expected_raw="[1,2]",
    ),
]


def test_python_runner_pass(tmp_path):
    sol = tmp_path / "solution.py"
    sol.write_text(SOLUTION_TWO_SUM, encoding="utf-8")
    runner = PythonRunner(tmp_path)
    results = runner.run(sol, TEST_CASES)
    assert all(r.passed for r in results), [r for r in results if not r.passed]


def test_python_runner_fail(tmp_path):
    sol = tmp_path / "solution.py"
    sol.write_text(SOLUTION_WRONG, encoding="utf-8")
    runner = PythonRunner(tmp_path)
    results = runner.run(sol, TEST_CASES)
    assert not any(r.passed for r in results)
    assert all(not r.passed for r in results)
