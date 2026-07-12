from __future__ import annotations

import re


_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"第[一二三四五六七八九十百千万\d]+章\s*[^\n]*"),
    re.compile(r"第[一二三四五六七八九十百千万\d]+卷\s*[^\n]*"),
    re.compile(r"Chapter\s+\d+[^\n]*", re.IGNORECASE),
]


def split(text: str) -> list[tuple[str, str]]:
    for pattern in _PATTERNS:
        matches = list(pattern.finditer(text))
        if not matches:
            continue

        chapters: list[tuple[str, str]] = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            title = m.group().strip()
            content = text[start:end].strip()
            if content:
                chapters.append((title, content))

        if chapters:
            return chapters

    stripped = text.strip()
    if stripped:
        return [("全文", stripped)]
    return []
