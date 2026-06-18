from __future__ import annotations

import json
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..config import load_config
from ..models import TestCase, TestResult
from .base import Runner, require_runtime

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def _infer_method_name(solution_code: str) -> str:
    import re
    # Skip commented lines; ignore __init__ (from commented helper classes like ListNode)
    for line in solution_code.splitlines():
        if line.strip().startswith("#"):
            continue
        match = re.search(r"def (\w+)\(self", line)
        if match and match.group(1) != "__init__":
            return match.group(1)
    return "solve"


def _parse_param_types(solution_code: str, method_name: str) -> dict[str, str]:
    """Return {param_name: type_hint_str} for the solution method's parameters."""
    import re
    pattern = rf"def {re.escape(method_name)}\(self\s*,([^)]*)\)"
    match = re.search(pattern, solution_code, re.DOTALL)
    if not match:
        return {}
    types: dict[str, str] = {}
    for part in match.group(1).split(","):
        part = part.strip()
        if ":" in part:
            name, hint = part.split(":", 1)
            types[name.strip()] = hint.split("=")[0].strip()
    return types


def _build_call_args(test_cases: list[TestCase], param_types: dict[str, str]) -> str:
    if not test_cases:
        return ""
    sample = test_cases[0]
    args: list[str] = []
    for k in sample.input:
        hint = param_types.get(k, "")
        if "ListNode" in hint:
            args.append(f'_list_to_linked(_tc["input"]["{k}"])')
        elif "TreeNode" in hint:
            args.append(f'_list_to_tree(_tc["input"]["{k}"])')
        else:
            args.append(f'_tc["input"]["{k}"]')
    return ", ".join(args)


class PythonRunner(Runner):
    def run(self, solution_path: Path, test_cases: list[TestCase]) -> list[TestResult]:
        config = load_config()
        require_runtime(config.runtime.python_cmd)

        solution_code = solution_path.read_text(encoding="utf-8")
        method_name = _infer_method_name(solution_code)
        param_types = _parse_param_types(solution_code, method_name)
        call_args = _build_call_args(test_cases, param_types)

        tc_data = [
            {"input": tc.input, "expected": tc.expected_output}
            for tc in test_cases
        ]

        env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))
        template = env.get_template("test_runner.py.j2")
        harness_code = template.render(
            solution_code=solution_code,
            test_cases_json=json.dumps(tc_data),
            method_name=method_name,
            call_args=call_args,
        )

        with tempfile.NamedTemporaryFile(
            suffix=".py", mode="w", encoding="utf-8", delete=False
        ) as f:
            f.write(harness_code)
            harness_path = Path(f.name)

        try:
            stdout, stderr, _ = self._run_subprocess(
                [config.runtime.python_cmd, str(harness_path)],
                timeout=config.runtime.runner_timeout,
            )
        finally:
            harness_path.unlink(missing_ok=True)

        results = self._parse_harness_output(stdout, len(test_cases), test_cases)

        # Surface any stderr that isn't captured in LEET_ lines
        if stderr and not any(r.error for r in results):
            for i, r in enumerate(results):
                if not r.passed and not r.error:
                    results[i] = TestResult(index=r.index, passed=False, error=stderr.strip())

        return results
