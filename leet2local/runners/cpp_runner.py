from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..config import load_config
from ..models import TestCase, TestResult
from .base import Runner, require_runtime

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def _infer_method_name(solution_code: str) -> str:
    match = re.search(r"\b(\w+)\s*\([^)]*\)\s*\{", solution_code)
    if match and match.group(1) not in {"Solution", "if", "for", "while", "main"}:
        return match.group(1)
    return "solve"


def _cpp_literal(value: object) -> str:
    """Convert a Python value to a C++ literal expression."""
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
            return "{}"
        inner = ", ".join(_cpp_literal(v) for v in value)
        return "{" + inner + "}"
    return str(value)


def _infer_cpp_type(value: object) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "double"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list) and value:
        inner_type = _infer_cpp_type(value[0])
        return f"vector<{inner_type}>"
    return "auto"


def _build_harness_body(test_cases: list[TestCase], method_name: str) -> str:
    lines: list[str] = []
    for i, tc in enumerate(test_cases):
        args: list[str] = []
        for j, (param_name, value) in enumerate(tc.input.items()):
            cpp_type = _infer_cpp_type(value)
            var_name = f"_arg{i}_{j}"
            literal = _cpp_literal(value)
            lines.append(f"    {cpp_type} {var_name} = {literal};")
            args.append(var_name)

        expected_type = _infer_cpp_type(tc.expected_output)
        expected_lit = _cpp_literal(tc.expected_output)
        lines.append(f"    {expected_type} _expected{i} = {expected_lit};")
        call = f"_sol.{method_name}({', '.join(args)})"
        lines.append(f"    auto _result{i} = {call};")
        lines.append(f"    if (_result{i} == _expected{i}) {{")
        lines.append(f'        cout << "LEET_PASS {i}" << endl;')
        lines.append("    } else {")
        lines.append(
            f'        cout << "LEET_FAIL {i} got=" << dumpJson(_result{i}) '
            f'<< " expected=" << dumpJson(_expected{i}) << endl;'
        )
        lines.append("    }")

    return "\n".join(lines)


class CppRunner(Runner):
    def run(self, solution_path: Path, test_cases: list[TestCase]) -> list[TestResult]:
        config = load_config()
        require_runtime(config.runtime.cpp_compiler)

        solution_code = solution_path.read_text(encoding="utf-8")
        method_name = _infer_method_name(solution_code)
        harness_body = _build_harness_body(test_cases, method_name)

        env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))
        template = env.get_template("test_runner.cpp.j2")
        harness_code = template.render(
            solution_code=solution_code,
            harness_body=harness_body,
        )

        with self._make_temp_dir() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "runner.cpp"
            exe = tmp_path / "runner.exe"
            src.write_text(harness_code, encoding="utf-8")

            _, compile_err, rc = self._run_subprocess(
                [config.runtime.cpp_compiler, "-O2", "-std=c++17", "-o", str(exe), str(src)],
                timeout=30,
                cwd=tmp_path,
            )
            if rc != 0:
                return [
                    TestResult(index=i, passed=False, error=f"Compile error: {compile_err.strip()}")
                    for i in range(len(test_cases))
                ]

            stdout, stderr, _ = self._run_subprocess(
                [str(exe)],
                timeout=config.runtime.runner_timeout,
                cwd=tmp_path,
            )

        return self._parse_harness_output(stdout, len(test_cases))
