from __future__ import annotations

import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from importlib.resources import files as _res_files
from pathlib import Path

from ..models import TestCase, TestResult


def _load_template(name: str) -> str:
    return (_res_files("leet2local.templates") / name).read_text(encoding="utf-8")


def _format_input(tc: TestCase) -> str:
    parts = [f"{k}={v!r}" for k, v in tc.input.items()]
    return ", ".join(parts)


INSTALL_HINTS = {
    "python": "Install Python from https://python.org",
    "node": "Install Node.js from https://nodejs.org",
    "g++": "Install GCC/G++: https://gcc.gnu.org or via your package manager",
    "java": "Install JDK from https://adoptium.net",
    "javac": "Install JDK from https://adoptium.net",
}


def check_runtime_available(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def require_runtime(cmd: str) -> None:
    if not check_runtime_available(cmd):
        hint = INSTALL_HINTS.get(cmd, f"Install '{cmd}' and ensure it is on your PATH.")
        raise RuntimeError(f"Runtime not found: [bold]{cmd}[/bold]\n{hint}")


class Runner(ABC):
    def __init__(self, problem_dir: Path):
        self.problem_dir = problem_dir

    @abstractmethod
    def run(self, solution_path: Path, test_cases: list[TestCase]) -> list[TestResult]:
        ...

    def _parse_harness_output(
        self, stdout: str, n: int, test_cases: list[TestCase] | None = None
    ) -> list[TestResult]:
        results: list[TestResult] = []
        lines_by_index: dict[int, str] = {}

        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith(("LEET_PASS", "LEET_FAIL", "LEET_ERROR")):
                parts = line.split(" ", 2)
                if len(parts) >= 2:
                    idx = int(parts[1])
                    lines_by_index[idx] = line

        for i in range(n):
            raw = lines_by_index.get(i, f"LEET_ERROR {i} No output produced")
            parts = raw.split(" ", 2)
            kind = parts[0]
            rest = parts[2] if len(parts) > 2 else ""

            input_repr = _format_input(test_cases[i]) if test_cases and i < len(test_cases) else ""

            if kind in ("LEET_PASS", "LEET_FAIL"):
                got, expected = None, None
                for seg in rest.split(" "):
                    if seg.startswith("got="):
                        got = seg[4:]
                    elif seg.startswith("expected="):
                        expected = seg[9:]
                results.append(TestResult(
                    index=i,
                    passed=(kind == "LEET_PASS"),
                    got=got,
                    expected=expected,
                    input_repr=input_repr,
                ))
            else:
                results.append(TestResult(index=i, passed=False, error=rest, input_repr=input_repr))

        return results

    def _run_subprocess(
        self, cmd: list[str], timeout: int = 10, cwd: Path | None = None
    ) -> tuple[str, str, int]:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(cwd or self.problem_dir),
            )
            return proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired:
            return "", "Execution timed out", 1

    def _make_temp_dir(self) -> tempfile.TemporaryDirectory:
        return tempfile.TemporaryDirectory(prefix="leet2local_")
