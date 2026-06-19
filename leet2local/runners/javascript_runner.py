from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from jinja2 import BaseLoader, Environment

from ..config import load_config
from ..models import TestCase, TestResult
from .base import Runner, _load_template, require_runtime


def _infer_method_name(solution_code: str) -> str:
    match = re.search(r"var (\w+)\s*=\s*function|function (\w+)\s*\(", solution_code)
    if match:
        return match.group(1) or match.group(2)
    return "solve"


def _build_call_args(test_cases: list[TestCase]) -> str:
    if not test_cases:
        return ""
    sample = test_cases[0]
    return ", ".join(f'_tc.input["{k}"]' for k in sample.input)


class JavaScriptRunner(Runner):
    def run(self, solution_path: Path, test_cases: list[TestCase]) -> list[TestResult]:
        config = load_config()
        require_runtime(config.runtime.node_cmd)

        solution_code = solution_path.read_text(encoding="utf-8")
        method_name = _infer_method_name(solution_code)
        call_args = _build_call_args(test_cases)

        tc_data = [
            {"input": tc.input, "expected": tc.expected_output}
            for tc in test_cases
        ]

        env = Environment(loader=BaseLoader())
        template = env.from_string(_load_template("test_runner.js.j2"))
        harness_code = template.render(
            solution_code=solution_code,
            test_cases_json=json.dumps(tc_data),
            method_name=method_name,
            call_args=call_args,
        )

        with tempfile.NamedTemporaryFile(
            suffix=".js", mode="w", encoding="utf-8", delete=False
        ) as f:
            f.write(harness_code)
            harness_path = Path(f.name)

        try:
            stdout, stderr, _ = self._run_subprocess(
                [config.runtime.node_cmd, str(harness_path)],
                timeout=config.runtime.runner_timeout,
            )
        finally:
            harness_path.unlink(missing_ok=True)

        return self._parse_harness_output(stdout, len(test_cases))
