from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class DialogueSegment:
    text: str
    speaker: str | None = None
    start: int = 0
    end: int = 0
    is_dialogue: bool = False


_COLON_SPEAKER_RE = re.compile(r"([\u4e00-\u9fff\w]{1,6})[：:]")

_QUOTE_PAIRS: list[tuple[str, str]] = [
    ("\u300c", "\u300d"),
    ("\u300e", "\u300f"),
    ("\u201c", "\u201d"),
    ("\u2018", "\u2019"),
    ("\uff02", "\uff02"),
    ("\u0022", "\u0022"),
]


def _find_quotes(text: str) -> list[tuple[int, int]]:
    results: list[tuple[int, int]] = []
    stack: list[tuple[str, int]] = []
    i = 0
    while i < len(text):
        ch = text[i]
        for open_char, close_char in _QUOTE_PAIRS:
            if open_char == close_char:
                if ch == open_char:
                    if stack and stack[-1][0] == open_char:
                        start_pos = stack.pop()[1]
                        if start_pos + 1 < i and (i - start_pos - 1) >= 3:
                            results.append((start_pos + 1, i))
                    else:
                        stack.append((open_char, i))
                    break
            else:
                if ch == open_char:
                    stack.append((close_char, i))
                    break
                elif ch == close_char and stack and stack[-1][0] == close_char:
                    start_pos = stack.pop()[1]
                    if start_pos + 1 < i and (i - start_pos - 1) >= 3:
                        results.append((start_pos + 1, i))
                    break
        i += 1
    results.sort(key=lambda x: x[0])
    return results


def _find_colon_spans(text: str) -> list[tuple[int, int]]:
    results: list[tuple[int, int]] = []
    for m in _COLON_SPEAKER_RE.finditer(text):
        results.append((m.start(), m.end()))
    return results


def _find_colon_dialogue_spans(text: str) -> list[tuple[int, int]]:
    colon_matches = _find_colon_spans(text)
    if not colon_matches:
        return []

    result: list[tuple[int, int]] = []
    for i, (_start, colon_end) in enumerate(colon_matches):
        content_start = colon_end
        if i + 1 < len(colon_matches):
            end = colon_matches[i + 1][0]
        else:
            end = len(text)
        content = text[content_start:end]
        if content.strip():
            result.append((content_start, end))

    return result


def _merge_segments(
    paragraph: str,
    span_positions: list[tuple[int, int]],
) -> list[DialogueSegment]:
    segments: list[DialogueSegment] = []
    cursor = 0

    for start, end in sorted(span_positions, key=lambda x: x[0]):
        if start > cursor:
            narration = paragraph[cursor:start]
            if narration:
                segments.append(DialogueSegment(
                    text=narration,
                    start=cursor,
                    end=start,
                    is_dialogue=False,
                ))
        quote_content = paragraph[start:end]
        if quote_content:
            segments.append(DialogueSegment(
                text=quote_content,
                start=start,
                end=end,
                is_dialogue=True,
            ))
        cursor = end

    if cursor < len(paragraph):
        segments.append(DialogueSegment(
            text=paragraph[cursor:],
            start=cursor,
            end=len(paragraph),
        ))

    return segments


def _validate_segments(
    paragraph: str,
    segments: list[DialogueSegment],
) -> list[DialogueSegment]:
    if not segments:
        return [DialogueSegment(paragraph, start=0, end=len(paragraph))]

    cursor = 0
    for seg in segments:
        found = paragraph.find(seg.text, cursor)
        if cursor != found:
            return [DialogueSegment(paragraph, start=0, end=len(paragraph))]
        cursor += len(seg.text)

    if cursor != len(paragraph):
        return [DialogueSegment(paragraph, start=0, end=len(paragraph))]

    return segments


def _resolve_overlaps(
    quotes: list[tuple[int, int]],
    colons: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    colons_set = set(colons)
    all_spans: list[tuple[int, int, bool]] = []
    for q in quotes:
        all_spans.append((*q, True))
    for c in colons:
        all_spans.append((*c, False))
    all_spans.sort(key=lambda x: (x[0], x[1]))

    resolved: list[tuple[int, int]] = []
    for start, end, is_quote in all_spans:
        if not resolved:
            resolved.append((start, end))
            continue

        last_start, last_end = resolved[-1]
        if start >= last_end:
            resolved.append((start, end))
            continue

        if is_quote:
            if start > last_start:
                resolved[-1] = (last_start, start)
                resolved.append((start, end))
            else:
                resolved[-1] = (start, max(last_end, end))
        else:
            if end <= last_end:
                continue
            if start > last_start:
                resolved.append((last_end, end))
            else:
                resolved[-1] = (last_start, end)

    return [(s, e) for s, e in resolved if s < e and (e - s) >= 2]


def extract_spans(paragraph: str) -> list[DialogueSegment]:
    quotes = _find_quotes(paragraph)
    colon_dialogues = _find_colon_dialogue_spans(paragraph)

    resolved_spans = _resolve_overlaps(quotes, colon_dialogues)
    segments = _merge_segments(paragraph, resolved_spans)
    return _validate_segments(paragraph, segments)


def extract(paragraph: str) -> list[DialogueSegment]:
    """Backward-compatible wrapper for extract_spans."""
    return extract_spans(paragraph)
