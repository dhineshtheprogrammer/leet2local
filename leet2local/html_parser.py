from __future__ import annotations

import re

from bs4 import BeautifulSoup
from markdownify import markdownify


def html_to_markdown(html: str) -> str:
    """Convert LeetCode HTML problem content to clean Markdown."""
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Remove style/script tags
    for tag in soup.find_all(["style", "script"]):
        tag.decompose()

    # Unwrap <p> tags inside <pre> to avoid double-wrapping
    for pre in soup.find_all("pre"):
        for p in pre.find_all("p"):
            p.unwrap()

    # Convert <sup> to ^ notation (e.g. 10^9)
    for sup in soup.find_all("sup"):
        sup.replace_with(f"^{sup.get_text()}")

    # Convert <sub> to _ notation
    for sub in soup.find_all("sub"):
        sub.replace_with(f"_{sub.get_text()}")

    # Replace &nbsp; with regular space
    cleaned_html = str(soup).replace(" ", " ")

    md = markdownify(
        cleaned_html,
        heading_style="ATX",
        bullets="-",
        code_language="",
        strip=["img"],
    )

    # Collapse 3+ consecutive blank lines into 2
    md = re.sub(r"\n{3,}", "\n\n", md)

    # Remove trailing whitespace on each line
    md = "\n".join(line.rstrip() for line in md.splitlines())

    return md.strip()
