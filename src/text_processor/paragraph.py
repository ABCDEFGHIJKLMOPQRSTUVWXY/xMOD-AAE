from __future__ import annotations

import re


_SPLIT_RE = re.compile(r"\n\s*\n")


def split(chapter_text: str) -> list[str]:
    paragraphs = _SPLIT_RE.split(chapter_text)
    result: list[str] = []
    for p in paragraphs:
        stripped = p.strip()
        if len(stripped) >= 5:
            result.append(stripped)
    return result
