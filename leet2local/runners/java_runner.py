from __future__ import annotations

import re
from pathlib import Path

from jinja2 import BaseLoader, Environment

from ..config import load_config
from ..models import TestCase, TestResult
from .base import Runner, _load_template, require_runtime


def _java_literal(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, list):
        if not value:
            return "new int[]{}"
        inner = ", ".join(_java_literal(v) for v in value)
        return f"new int[]{{{inner}}}"
    return str(value)


def _infer_method_name(solution_code: str) -> str:
    match = re.search(r"public\s+\w+\s+(\w+)\s*\(", solution_code)
    if match and match.group(1) not in {"Solution"}:
        return match.group(1)
    return "solve"


def _build_harness_body(test_cases: list[TestCase], method_name: str) -> str:
    lines: list[str] = []
    for i, tc in enumerate(test_cases):
        args: list[str] = []
        for j, (_, value) in enumerate(tc.input.items()):
            var_name = f"_arg{i}_{j}"
            literal = _java_literal(value)
            # Use Object/int[] types; Java type inference is limited
            if isinstance(value, list):
                lines.append(f"        int[] {var_name} = {literal};")
            elif isinstance(value, bool):
                lines.append(f"        boolean {var_name} = {literal};")
            elif isinstance(value, int):
                lines.append(f"        int {var_name} = {literal};")
            elif isinstance(value, str):
                lines.append(f"        String {var_name} = {literal};")
            else:
                lines.append(f"        Object {var_name} = {literal};")
            args.append(var_name)

        call = f"_sol.{method_name}({', '.join(args)})"
        lines.append(f"        Object _result{i} = {call};")
        expected_lit = _java_literal(tc.expected_output)
        lines.append(f"        Object _expected{i} = {expected_lit};")
        lines.append(
            f"        if (toJson(_result{i}).equals(toJson(_expected{i}))) {{"
        )
        lines.append(f'            System.out.println("LEET_PASS {i}");')
        lines.append("        } else {")
        lines.append(
            f'            System.out.println("LEET_FAIL {i} got=" + toJson(_result{i}) '
            f'+ " expected=" + toJson(_expected{i}));'
        )
        lines.append("        }")

    return "\n".join(lines)


def _make_inner_class(solution_code: str) -> str:
    """Wrap the Solution class as a static inner class of LeetRunner."""
    # Replace top-level 'class Solution' with 'static class Solution'
    modified = re.sub(
        r"\bclass\s+Solution\b",
        "static class Solution",
        solution_code,
        count=1,
    )
    # Indent all lines by 4 spaces
    return "\n".join("    " + line for line in modified.splitlines())


class JavaRunner(Runner):
    def run(self, solution_path: Path, test_cases: list[TestCase]) -> list[TestResult]:
        config = load_config()
        require_runtime(config.runtime.javac_cmd)
        require_runtime(config.runtime.java_cmd)

        solution_code = solution_path.read_text(encoding="utf-8")
        method_name = _infer_method_name(solution_code)
        harness_body = _build_harness_body(test_cases, method_name)
        inner_class = _make_inner_class(solution_code)

        env = Environment(loader=BaseLoader())
        template = env.from_string(_load_template("test_runner.java.j2"))
        harness_code = template.render(
            solution_code_inner=inner_class,
            harness_body=harness_body,
        )

        with self._make_temp_dir() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "LeetRunner.java"
            src.write_text(harness_code, encoding="utf-8")

            _, compile_err, rc = self._run_subprocess(
                [config.runtime.javac_cmd, "LeetRunner.java"],
                timeout=30,
                cwd=tmp_path,
            )
            if rc != 0:
                return [
                    TestResult(index=i, passed=False, error=f"Compile error: {compile_err.strip()}")
                    for i in range(len(test_cases))
                ]

            stdout, _, _ = self._run_subprocess(
                [config.runtime.java_cmd, "-cp", str(tmp_path), "LeetRunner"],
                timeout=config.runtime.runner_timeout,
                cwd=tmp_path,
            )

        return self._parse_harness_output(stdout, len(test_cases))
