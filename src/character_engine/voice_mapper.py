from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_analyzer import CharacterProfile


_AGE_MAP: dict[str, str | None] = {
    "少年": None,
    "青年": "YoungAdult",
    "中年": "Adult",
    "老年": "Senior",
    "未知": None,
}

_GENDER_MAP: dict[str, str] = {
    "男": "Male",
    "女": "Female",
    "未知": "",
}


def assign_voice(
    profile: CharacterProfile,
    available_voices: list[dict],
    used_voices: set[str],
) -> str:
    chinese_voices = [v for v in available_voices if str(v.get("locale", "")).startswith("zh-")]

    if not chinese_voices:
        return "zh-CN-XiaoxiaoNeural"

    target_gender: str | None = _GENDER_MAP.get(profile.gender)
    target_age: str | None = _AGE_MAP.get(profile.age_group)

    candidates = list(chinese_voices)

    if target_gender:
        gender_matches = [v for v in candidates if v.get("gender") == target_gender]
        if gender_matches:
            candidates = gender_matches

    if target_age:
        age_matches = [v for v in candidates if v.get("age_group") == target_age]
        if age_matches:
            candidates = age_matches

    unused = [v for v in candidates if v.get("name") not in used_voices]
    if unused:
        candidates = unused

    if candidates:
        return str(candidates[0].get("name", "zh-CN-XiaoxiaoNeural"))

    unused_chinese = [v for v in chinese_voices if v.get("name") not in used_voices]
    if unused_chinese:
        return str(unused_chinese[0].get("name", "zh-CN-XiaoxiaoNeural"))

    return "zh-CN-XiaoxiaoNeural"


def assign_narrator_voice(settings: dict, available_voices: list[dict]) -> str:
    narrator = settings.get("narrator_voice", "")
    if narrator and any(v.get("name") == narrator for v in available_voices):
        return narrator
    return "zh-CN-XiaoxiaoNeural"
