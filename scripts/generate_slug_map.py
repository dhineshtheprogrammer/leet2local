"""
Run once to generate leet2local/data/slug_map.json.
Usage: python scripts/generate_slug_map.py
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx

OUT_PATH = Path(__file__).parent.parent / "leet2local" / "data" / "slug_map.json"

REST_URL = "https://leetcode.com/api/problems/all/"


def main() -> None:
    print("Fetching all LeetCode question slugs via public REST API...")
    with httpx.Client(
        headers={
            "Referer": "https://leetcode.com",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        },
        timeout=60,
    ) as client:
        resp = client.get(REST_URL)
        resp.raise_for_status()
        data = resp.json()

    slug_map: dict[str, str] = {}
    for item in data.get("stat_status_pairs", []):
        num = str(item["stat"]["frontend_question_id"])
        slug = item["stat"]["question__title_slug"]
        if slug:
            slug_map[num] = slug

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(slug_map, indent=2), encoding="utf-8")
    print(f"Wrote {len(slug_map)} entries to {OUT_PATH}")


if __name__ == "__main__":
    main()
