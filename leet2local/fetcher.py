from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx

from .auth import get_auth_headers
from .config import load_config
from .html_parser import html_to_markdown
from .models import CodeSnippet, Problem, ProblemMeta, TestCase
from .queries import QUESTION_DATA, QUESTION_LIST
from .rate_limiter import RateLimitError, graphql_retry

_SLUG_MAP_PATH = Path(__file__).parent / "data" / "slug_map.json"
_GRAPHQL_URL = "https://leetcode.com/graphql"

LANG_SLUG_MAP = {
    "python": "python3",
    "javascript": "javascript",
    "cpp": "cpp",
    "java": "java",
}

LANG_EXT_MAP = {
    "python": ".py",
    "javascript": ".js",
    "cpp": ".cpp",
    "java": ".java",
}


def _gql_headers() -> dict[str, str]:
    """Return headers for GraphQL; try auth headers, fall back to public."""
    try:
        return get_auth_headers()
    except Exception:
        return {
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }


@graphql_retry
def _graphql(client: httpx.Client, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    resp = client.post(
        _GRAPHQL_URL,
        json={"query": query, "variables": variables},
    )
    if resp.status_code == 429:
        raise RateLimitError("Rate limited by LeetCode API")
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors']}")
    return data


def resolve_slug(number: int, client: httpx.Client) -> str:
    """Map a problem number to its titleSlug."""
    # 1. Try GraphQL (works when authenticated)
    try:
        data = _graphql(
            client,
            QUESTION_LIST,
            {"filters": {"frontendQuestionId": str(number)}},
        )
        questions = data["data"]["questionList"]["questions"]
        if questions:
            return questions[0]["titleSlug"]
    except Exception:
        pass

    # 2. Try public REST API (no auth required, but may be slow)
    slug = _resolve_via_rest(number, client)
    if slug:
        return slug

    # 3. Fallback: bundled slug map
    if _SLUG_MAP_PATH.exists():
        with _SLUG_MAP_PATH.open() as f:
            slug_map: dict[str, str] = json.load(f)
        slug = slug_map.get(str(number))
        if slug:
            return slug

    raise RuntimeError(
        f"Could not resolve slug for problem #{number}. "
        "Try running [bold]lc login[/bold] to enable authenticated API access."
    )


def _resolve_via_rest(number: int, client: httpx.Client) -> str | None:
    """Use LeetCode's public REST endpoint to look up a slug by problem number."""
    try:
        resp = client.get(
            "https://leetcode.com/api/problems/all/",
            headers={
                "Referer": "https://leetcode.com",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return None
        for item in resp.json().get("stat_status_pairs", []):
            if item["stat"]["frontend_question_id"] == number:
                return item["stat"]["question__title_slug"]
    except Exception:
        pass
    return None


def _parse_test_cases(
    example_testcases: str,
    meta_raw: str,
    content_md: str,
) -> list[TestCase]:
    """Build structured TestCase list from raw API fields."""
    if not example_testcases:
        return []

    try:
        meta = json.loads(meta_raw)
        params = meta.get("params", [])
    except (json.JSONDecodeError, TypeError):
        params = []

    raw_inputs = example_testcases.split("\n")
    n_params = len(params) if params else 1
    input_groups: list[list[str]] = []

    i = 0
    while i < len(raw_inputs):
        group = raw_inputs[i : i + n_params]
        if any(g.strip() for g in group):
            input_groups.append(group)
        i += n_params

    # Extract expected outputs from markdown Output: lines
    expected_outputs = _extract_outputs_from_md(content_md)

    test_cases: list[TestCase] = []
    for idx, group in enumerate(input_groups):
        structured_input: dict[str, Any] = {}
        for j, raw_val in enumerate(group):
            name = params[j]["name"] if j < len(params) else f"arg{j}"
            try:
                structured_input[name] = json.loads(raw_val.strip())
            except json.JSONDecodeError:
                structured_input[name] = raw_val.strip()

        expected_raw = expected_outputs[idx] if idx < len(expected_outputs) else ""
        try:
            expected_output = json.loads(expected_raw) if expected_raw else None
        except json.JSONDecodeError:
            expected_output = expected_raw

        test_cases.append(
            TestCase(
                input=structured_input,
                expected_output=expected_output,
                input_raw="\n".join(g.strip() for g in group),
                expected_raw=expected_raw,
            )
        )

    return test_cases


def _extract_outputs_from_md(md: str) -> list[str]:
    """Extract Output: values from parsed Markdown examples."""
    outputs: list[str] = []
    for match in re.finditer(r"\*\*Output:\*\*\s*`?([^\n`]+)`?", md):
        outputs.append(match.group(1).strip())
    if not outputs:
        for match in re.finditer(r"Output:\s*([^\n]+)", md):
            outputs.append(match.group(1).strip())
    return outputs


def fetch_problem(number: int, lang: str) -> tuple[Problem, Path]:
    """Fetch a LeetCode problem and write it to disk. Returns (problem, dir_path)."""
    config = load_config()
    lang = lang or config.settings.default_language

    with httpx.Client(
        headers=_gql_headers(),
        timeout=config.api.request_timeout,
    ) as client:
        slug = resolve_slug(number, client)
        data = _graphql(client, QUESTION_DATA, {"titleSlug": slug})

    q = data["data"]["question"]
    content_html: str = q.get("content") or ""
    content_md = html_to_markdown(content_html)

    snippets = [CodeSnippet(**s) for s in (q.get("codeSnippets") or [])]

    test_cases = _parse_test_cases(
        q.get("exampleTestcases") or "",
        q.get("metaData") or "{}",
        content_md,
    )

    problem = Problem(
        frontend_id=int(q["questionFrontendId"]),
        slug=q["titleSlug"],
        title=q["title"],
        difficulty=q["difficulty"],
        content_html=content_html,
        content_md=content_md,
        code_snippets=snippets,
        sample_test_cases=test_cases,
        question_id=q["questionId"],
    )

    dir_path = create_problem_directory(problem, lang, config.settings.problems_dir)
    return problem, dir_path


def create_problem_directory(problem: Problem, lang: str, problems_dir: str) -> Path:
    """Write question.md, solution.<ext>, test_cases.json, and .meta.json."""
    ext = LANG_EXT_MAP.get(lang, ".py")
    lang_slug = LANG_SLUG_MAP.get(lang, "python3")

    base = Path(problems_dir) / f"{problem.frontend_id}-{problem.slug}"
    base.mkdir(parents=True, exist_ok=True)

    # question.md
    header = (
        f"# {problem.frontend_id}. {problem.title}\n\n"
        f"**Difficulty:** {problem.difficulty}\n\n"
        "---\n\n"
    )
    (base / "question.md").write_text(header + problem.content_md, encoding="utf-8")

    # solution.<ext>
    stub = _find_snippet(problem.code_snippets, lang_slug)
    solution_path = base / f"solution{ext}"
    if not solution_path.exists():
        solution_path.write_text(stub, encoding="utf-8")

    # test_cases.json
    tc_data = [
        {
            "input": tc.input,
            "expected": tc.expected_output,
            "input_raw": tc.input_raw,
            "expected_raw": tc.expected_raw,
        }
        for tc in problem.sample_test_cases
    ]
    (base / "test_cases.json").write_text(
        json.dumps(tc_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # .meta.json — stores metadata needed for submission
    meta = ProblemMeta(
        question_id=problem.question_id,
        slug=problem.slug,
        frontend_id=problem.frontend_id,
        lang=lang,
    )
    (base / ".meta.json").write_text(
        meta.model_dump_json(indent=2), encoding="utf-8"
    )

    return base


def _find_snippet(snippets: list[CodeSnippet], lang_slug: str) -> str:
    for s in snippets:
        if s.langSlug == lang_slug:
            return s.code
    # Fallback: first available snippet
    return snippets[0].code if snippets else "# No code snippet available\n"


def load_meta(number: int) -> ProblemMeta:
    """Load saved .meta.json for a problem number."""
    config = load_config()
    problems_dir = Path(config.settings.problems_dir)

    # Find the directory matching the number prefix
    matches = list(problems_dir.glob(f"{number}-*"))
    if not matches:
        raise FileNotFoundError(
            f"Problem #{number} not found locally. Run [bold]lc fetch {number}[/bold] first."
        )
    meta_file = matches[0] / ".meta.json"
    if not meta_file.exists():
        raise FileNotFoundError(f"Metadata file not found: {meta_file}")

    return ProblemMeta.model_validate_json(meta_file.read_text(encoding="utf-8"))


def find_problem_dir(number: int) -> Path:
    """Return the local directory for a fetched problem."""
    config = load_config()
    problems_dir = Path(config.settings.problems_dir)
    matches = list(problems_dir.glob(f"{number}-*"))
    if not matches:
        raise FileNotFoundError(
            f"Problem #{number} not found locally. Run [bold]lc fetch {number}[/bold] first."
        )
    return matches[0]
