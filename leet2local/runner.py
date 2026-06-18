from __future__ import annotations

import json
from pathlib import Path

from .config import load_config
from .fetcher import find_problem_dir, load_meta
from .models import TestCase, TestResult
from .runners.base import Runner


def _load_test_cases(problem_dir: Path) -> list[TestCase]:
    tc_file = problem_dir / "test_cases.json"
    if not tc_file.exists():
        return []
    raw = json.loads(tc_file.read_text(encoding="utf-8"))
    return [
        TestCase(
            input=tc["input"],
            expected_output=tc["expected"],
            input_raw=tc.get("input_raw", ""),
            expected_raw=tc.get("expected_raw", ""),
        )
        for tc in raw
    ]


def _get_runner(lang: str, problem_dir: Path) -> Runner:
    if lang == "python":
        from .runners.python_runner import PythonRunner
        return PythonRunner(problem_dir)
    if lang == "javascript":
        from .runners.javascript_runner import JavaScriptRunner
        return JavaScriptRunner(problem_dir)
    if lang == "cpp":
        from .runners.cpp_runner import CppRunner
        return CppRunner(problem_dir)
    if lang == "java":
        from .runners.java_runner import JavaRunner
        return JavaRunner(problem_dir)
    raise ValueError(f"Unsupported language: {lang!r}")


def _find_solution_file(problem_dir: Path, lang: str) -> Path:
    ext_map = {"python": ".py", "javascript": ".js", "cpp": ".cpp", "java": ".java"}
    ext = ext_map.get(lang, ".py")
    candidate = problem_dir / f"solution{ext}"
    if candidate.exists():
        return candidate
    # Fallback: find any solution.<ext> file
    matches = list(problem_dir.glob("solution.*"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"No solution file found in {problem_dir}")


def run_local(number: int) -> list[TestResult]:
    """Run a problem's solution locally against its sample test cases."""
    problem_dir = find_problem_dir(number)
    meta = load_meta(number)

    test_cases = _load_test_cases(problem_dir)
    if not test_cases:
        raise RuntimeError(
            f"No test cases found for problem #{number}. "
            "Try running [bold]lc fetch[/bold] again."
        )

    solution_path = _find_solution_file(problem_dir, meta.lang)
    runner = _get_runner(meta.lang, problem_dir)
    return runner.run(solution_path, test_cases)
