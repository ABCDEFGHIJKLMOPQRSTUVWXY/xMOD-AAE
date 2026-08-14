from __future__ import annotations

import json

from typing import TYPE_CHECKING

from .voice_design import build_voice_description

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


def _fallback_voice(available_voices: list[dict]) -> str:
    if available_voices:
        return str(available_voices[0].get("name", "zh-CN-XiaoxiaoNeural"))
    return "zh-CN-XiaoxiaoNeural"


def assign_voice(
    profile: CharacterProfile,
    available_voices: list[dict],
    used_voices: set[str],
    driver_id: str = "edge-tts",
) -> tuple[str, str, dict | None]:
    """Pick a voice for a character profile.

    Returns:
        ``(driver_id, voice_id, voice_params)``. For the MiMo driver a
        natural-language voice description is auto-generated from the profile
        and returned as ``{"voice_description": ...}`` (voicedesign mode);
        for other drivers ``voice_params`` is ``None``.
    """
    chinese_voices = [v for v in available_voices if str(v.get("locale", "")).startswith("zh-")]

    if not chinese_voices:
        voice_id = _fallback_voice(available_voices)
    else:
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
            voice_id = str(candidates[0].get("name", _fallback_voice(available_voices)))
        else:
            unused_chinese = [v for v in chinese_voices if v.get("name") not in used_voices]
            if unused_chinese:
                voice_id = str(unused_chinese[0].get("name", _fallback_voice(available_voices)))
            else:
                voice_id = _fallback_voice(available_voices)

    voice_params: dict | None = None
    if driver_id == "mimo":
        description = build_voice_description(profile)
        if description:
            voice_params = {"voice_description": description}

    return driver_id, voice_id, voice_params


def assign_narrator_voice(
    settings: dict,
    available_voices: list[dict],
    driver_id: str = "edge-tts",
) -> tuple[str, str, dict | None]:
    """Pick the narrator voice from settings.

    Returns:
        ``(driver_id, voice_id, voice_params)``.
    """
    narrator = settings.get("narrator_voice", "")
    if not (narrator and any(v.get("name") == narrator for v in available_voices)):
        narrator = _fallback_voice(available_voices)

    voice_params: dict | None = None
    if driver_id == "mimo":
        try:
            params = json.loads(settings.get("narrator_voice_params", "{}") or "{}")
        except (json.JSONDecodeError, TypeError):
            params = {}
        if params.get("voice_description"):
            voice_params = params

    return driver_id, narrator, voice_params
