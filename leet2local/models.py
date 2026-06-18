from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TestCase(BaseModel):
    input: dict[str, Any]
    expected_output: Any
    input_raw: str
    expected_raw: str


class CodeSnippet(BaseModel):
    lang: str
    langSlug: str
    code: str


class ProblemMeta(BaseModel):
    question_id: str
    slug: str
    frontend_id: int
    lang: str


class Problem(BaseModel):
    frontend_id: int
    slug: str
    title: str
    difficulty: Literal["Easy", "Medium", "Hard"]
    content_html: str
    content_md: str = ""
    code_snippets: list[CodeSnippet]
    sample_test_cases: list[TestCase] = Field(default_factory=list)
    question_id: str


class TestResult(BaseModel):
    index: int
    passed: bool
    got: Any = None
    expected: Any = None
    input_repr: str = ""
    error: str | None = None

    @property
    def status(self) -> str:
        if self.error:
            return "ERROR"
        return "PASS" if self.passed else "FAIL"


class SubmissionResult(BaseModel):
    status_code: int
    status_display: str
    runtime: str | None = None
    runtime_percentile: float | None = None
    memory: str | None = None
    memory_percentile: float | None = None
    total_correct: int | None = None
    total_testcases: int | None = None
    last_testcase: str | None = None
    expected_output: str | None = None
    code_output: str | None = None
    compile_error: str | None = None

    @property
    def accepted(self) -> bool:
        return self.status_display == "Accepted"
