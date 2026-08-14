from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field

from text_processor.dialogue import DialogueSegment


@dataclass
class ChunkInfo:
    text: str
    voice_id: str
    char_start: int
    char_end: int
    mp3_path: str = ""
    duration_ms: float = 0.0
    ready_event: object = field(default_factory=threading.Event)
    driver_id: str = ""
    voice_params: dict | None = None
    speaker: str = ""


_SPLIT_RE = re.compile(r"([，；。！？、：])")

_SPLIT_PUNCTUATION = {"，", "；", "。", "！", "？", "、", "："}


def _split_long_text(text: str, max_chars: int = 200, min_chars: int = 100) -> list[str]:
    """Split a long text into chunks at natural boundaries.

    Tries to split at punctuation marks to keep chunks between min_chars and max_chars.
    If a single sentence exceeds max_chars, splits at character boundaries.
    """
    if len(text) <= max_chars:
        return [text]

    tokens = _SPLIT_RE.split(text)
    chunks: list[str] = []
    current: list[str] = []

    for token in tokens:
        if token in _SPLIT_PUNCTUATION and current:
            potential = "".join(current) + token
            if len(potential) >= max_chars:
                current_text = "".join(current)
                if len(current_text) >= min_chars:
                    chunks.append(current_text)
                    current = [token]
                else:
                    chunks.append(potential)
                    current = []
            else:
                current.append(token)
        else:
            prospective = "".join(current) + token
            if len(prospective) > max_chars and current:
                chunks.append("".join(current))
                current = []
            current.append(token)

    if current:
        remaining = "".join(current)
        if remaining:
            if chunks and len(remaining) < min_chars:
                chunks[-1] = chunks[-1] + remaining
            else:
                chunks.append(remaining)

    final_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) > max_chars:
            for i in range(0, len(chunk), max_chars):
                final_chunks.append(chunk[i : i + max_chars])
        else:
            final_chunks.append(chunk)

    return final_chunks


def build(
    dialogue_segments: list[DialogueSegment],
    voice_map: dict[str, str],
    char_offset: int = 0,
) -> list[ChunkInfo]:
    """Build TTS-ready chunks from dialogue segments.

    Args:
        dialogue_segments: Ordered list from dialogue.extract() for ONE paragraph
        voice_map: Dict mapping speaker name → voice_id. Must include '_narrator_' key.
        char_offset: Starting character offset of this paragraph in the chapter

    Returns:
        Ordered list of ChunkInfo objects ready for TTS synthesis.
    """
    narrator_voice = voice_map["_narrator_"]

    spans: list[tuple[str, str, str, int, int]] = []
    pos = char_offset

    for seg in dialogue_segments:
        seg_len = len(seg.text)
        speaker = seg.speaker or "_narrator_"
        voice_id = voice_map.get(seg.speaker, narrator_voice) if seg.speaker else narrator_voice
        spans.append((seg.text, voice_id, speaker, pos, pos + seg_len))
        pos += seg_len

    if not spans:
        return []

    merged: list[tuple[str, str, str, int, int]] = []
    for text, voice_id, speaker, start, end in spans:
        if (merged and merged[-1][1] == voice_id and merged[-1][2] == speaker):
            prev_text, prev_voice, prev_speaker, prev_start, prev_end = merged[-1]
            merged[-1] = (prev_text + text, prev_voice, prev_speaker, prev_start, end)
        else:
            merged.append((text, voice_id, speaker, start, end))

    chunks: list[ChunkInfo] = []
    for text, voice_id, speaker, start, end in merged:
        if len(text) > 200:
            sub_texts = _split_long_text(text)
            sub_start = start
            for sub_text in sub_texts:
                sub_end = sub_start + len(sub_text)
                chunks.append(ChunkInfo(
                    text=sub_text,
                    voice_id=voice_id,
                    char_start=sub_start,
                    char_end=sub_end,
                    speaker=speaker,
                ))
                sub_start = sub_end
        else:
            chunks.append(ChunkInfo(
                text=text,
                voice_id=voice_id,
                char_start=start,
                char_end=end,
                speaker=speaker,
            ))

    return chunks
