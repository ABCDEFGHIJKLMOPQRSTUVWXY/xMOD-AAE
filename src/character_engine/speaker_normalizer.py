# -*- coding: utf-8 -*-
from __future__ import annotations

from text_processor.dialogue import DialogueSegment

_PRESERVED = {"未知", "旁白", ""}

_NON_NAME_DENYLIST = {
    "他", "她", "它", "他们", "她们", "它们", "你", "我",
    "您", "咱们", "我们", "你们",
}

_TITLE_TERMS = {
    "少年", "青年", "中年", "老年", "老者", "老人",
    "男人", "女人", "男子", "女子", "那人",
    "侍卫", "丫鬟", "小厮", "小姑娘", "小丫头",
    "公子", "少爷", "小姐", "姑娘", "大叔", "大爷", "大哥",
    "弟弟", "姐姐", "先生", "老丈", "小孩", "孩子",
    "路人", "众人", "仆从", "随从", "车夫", "掌柜", "伙计",
    "大夫", "和尚", "道士", "伙计",
}


def _classify(name: str) -> str:
    """Classify a speaker name into formal / generic / preserved.

    Returns one of: "formal", "generic", "preserved".
    """
    if name in _PRESERVED:
        return "preserved"
    if name in _NON_NAME_DENYLIST or name in _TITLE_TERMS or len(name) == 1:
        return "generic"
    return "formal"


def _most_frequent(names: list[str], counts: dict[str, int]) -> str:
    return max(names, key=lambda n: counts[n])


def normalize_speakers(segments) -> None:
    """In-place normalize generic speaker names to a canonical formal name.

    Accepts either a flat list of DialogueSegment or a nested list of
    paragraphs (each a list of DialogueSegment), mirroring aggregator.collect.
    With paragraph grouping, "same paragraph co-occurrence" of a formal name
    is preferred; otherwise the most frequent formal name overall is used.
    Preserved pseudo-characters (未知/旁白) and empty speakers are left as-is.
    """
    if segments and isinstance(segments[0], list):
        paragraphs: list[list[DialogueSegment]] = segments
        flat: list[DialogueSegment] = [seg for para in paragraphs for seg in para]
    else:
        paragraphs = None
        flat = list(segments)

    counts: dict[str, int] = {}
    for seg in flat:
        if seg.speaker:
            counts[seg.speaker] = counts.get(seg.speaker, 0) + 1

    formal_names = [n for n in counts if _classify(n) == "formal"]
    if not formal_names:
        return
    global_most = _most_frequent(formal_names, counts)

    cooccur: dict[str, dict[str, int]] = {}
    if paragraphs:
        for para in paragraphs:
            speakers = [seg.speaker for seg in para if seg.speaker]
            para_formals = [n for n in speakers if _classify(n) == "formal"]
            if not para_formals:
                continue
            para_most = _most_frequent(para_formals, counts)
            for n in set(speakers):
                if _classify(n) == "generic":
                    bucket = cooccur.setdefault(n, {})
                    bucket[para_most] = bucket.get(para_most, 0) + 1

    for seg in flat:
        name = seg.speaker
        if not name or _classify(name) != "generic":
            continue
        target: str | None = None
        if cooccur and name in cooccur and cooccur[name]:
            target = _most_frequent(cooccur[name], cooccur[name])
        else:
            target = global_most
        if target:
            seg.speaker = target
