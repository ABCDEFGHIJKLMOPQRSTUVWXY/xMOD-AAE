from __future__ import annotations

from dataclasses import dataclass, field
from text_processor.dialogue import DialogueSegment


@dataclass
class SpeakerInfo:
    name: str
    total_lines: int = 0
    total_chars: int = 0
    sample_quotes: list[str] = field(default_factory=list)


def collect(dialogue_segments_per_paragraph: list[list[DialogueSegment]] | list[DialogueSegment]) -> dict[str, SpeakerInfo]:
    speakers: dict[str, SpeakerInfo] = {}

    all_segments: list[DialogueSegment] = []
    if dialogue_segments_per_paragraph and not isinstance(dialogue_segments_per_paragraph[0], list):
        all_segments = dialogue_segments_per_paragraph
    else:
        for para in dialogue_segments_per_paragraph:
            all_segments.extend(para)

    for seg in all_segments:
        if seg.speaker is not None:
            if seg.speaker not in speakers:
                speakers[seg.speaker] = SpeakerInfo(name=seg.speaker)
            info = speakers[seg.speaker]
            info.total_lines += 1
            info.total_chars += len(seg.text)
            if seg.text.strip():
                info.sample_quotes.append(seg.text)

    for info in speakers.values():
        seen: set[str] = set()
        unique: list[str] = []
        for q in info.sample_quotes:
            if q not in seen:
                seen.add(q)
                unique.append(q)
        unique.sort(key=len, reverse=True)
        info.sample_quotes = unique[:5]

    return speakers
