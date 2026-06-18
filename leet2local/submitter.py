from __future__ import annotations

import time

import httpx

from .auth import get_auth_headers
from .config import load_config
from .fetcher import find_problem_dir, load_meta
from .models import SubmissionResult
from .rate_limiter import RateLimitError, graphql_retry

LANG_SLUG_MAP = {
    "python": "python3",
    "javascript": "javascript",
    "cpp": "cpp",
    "java": "java",
}

# LeetCode REST endpoints (not GraphQL) for submission
_SUBMIT_URL = "https://leetcode.com/problems/{slug}/submit/"
_CHECK_URL = "https://leetcode.com/submissions/detail/{submission_id}/check/"


def submit_remote(number: int) -> SubmissionResult:
    """Submit the local solution for problem `number` to LeetCode."""
    config = load_config()
    problem_dir = find_problem_dir(number)
    meta = load_meta(number)

    ext_map = {"python": ".py", "javascript": ".js", "cpp": ".cpp", "java": ".java"}
    solution_path = problem_dir / f"solution{ext_map.get(meta.lang, '.py')}"
    if not solution_path.exists():
        raise FileNotFoundError(f"Solution file not found: {solution_path}")

    code = solution_path.read_text(encoding="utf-8")
    lang_slug = LANG_SLUG_MAP.get(meta.lang, "python3")

    headers = get_auth_headers()
    # Submission requires the Referer to point at the specific problem page
    headers["Referer"] = f"https://leetcode.com/problems/{meta.slug}/"

    with httpx.Client(headers=headers, timeout=config.api.request_timeout) as client:
        submission_id = _post_submission(client, meta.slug, meta.question_id, lang_slug, code)
        result = _poll_submission(client, submission_id)

    return result


@graphql_retry
def _post_submission(
    client: httpx.Client,
    slug: str,
    question_id: str,
    lang_slug: str,
    code: str,
) -> int:
    """POST to the REST submit endpoint, return submission_id."""
    url = _SUBMIT_URL.format(slug=slug)
    resp = client.post(
        url,
        json={
            "lang": lang_slug,
            "question_id": question_id,
            "typed_code": code,
        },
    )
    if resp.status_code == 429:
        raise RateLimitError("Rate limited by LeetCode")
    resp.raise_for_status()
    data = resp.json()
    submission_id = data.get("submission_id")
    if not submission_id:
        raise RuntimeError(f"Unexpected submission response: {data}")
    return int(submission_id)


def _poll_submission(
    client: httpx.Client,
    submission_id: int,
    max_attempts: int = 30,
) -> SubmissionResult:
    """Poll the check endpoint until the submission finishes."""
    url = _CHECK_URL.format(submission_id=submission_id)
    for _ in range(max_attempts):
        time.sleep(2)
        try:
            resp = client.get(url)
            if resp.status_code == 429:
                time.sleep(5)
                continue
            resp.raise_for_status()
            d = resp.json()

            state = d.get("state", "")
            if state in ("PENDING", "STARTED"):
                continue

            status_code = d.get("status_code", 0)
            return SubmissionResult(
                status_code=status_code,
                status_display=d.get("status_msg", "Unknown"),
                runtime=d.get("status_runtime"),
                runtime_percentile=d.get("runtime_percentile"),
                memory=d.get("status_memory"),
                memory_percentile=d.get("memory_percentile"),
                total_correct=d.get("total_correct"),
                total_testcases=d.get("total_testcases"),
                last_testcase=d.get("input_formatted") or d.get("last_testcase"),
                expected_output=d.get("expected_output"),
                code_output=d.get("code_output"),
                compile_error=d.get("compile_error") or d.get("full_compile_error"),
            )
        except Exception:
            continue

    return SubmissionResult(status_code=0, status_display="Timeout")
