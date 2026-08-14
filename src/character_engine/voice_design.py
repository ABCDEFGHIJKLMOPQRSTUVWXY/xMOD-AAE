from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_analyzer import CharacterProfile


def build_voice_description(profile) -> str:
    """Build a natural-language Chinese voice description from a character
    profile (pure template composition, no LLM call).

    The result feeds MiMo's ``mimo-v2.5-tts-voicedesign`` model. Returns an
    empty string when the profile carries no usable information.
    """
    gender = str(profile.gender or "").strip()
    age = str(profile.age_group or "").strip()
    personality = list(getattr(profile, "personality", None) or [])[:2]
    style = str(getattr(profile, "speaking_style", "") or "").strip()
    summary = str(getattr(profile, "summary", "") or "").strip()

    parts: list[str] = []

    unknown_gender = gender in ("", "未知")
    unknown_age = age in ("", "未知")
    if not unknown_age and not unknown_gender:
        parts.append(f"一位{age}的{gender}性")
    elif not unknown_gender:
        parts.append(f"一位{gender}性")
    elif not unknown_age:
        parts.append(f"一位{age}的人")

    if style:
        parts.append(style)
    if personality:
        parts.append("、".join(tag for tag in personality if tag))

    description = "，".join(parts).strip()
    if description and summary:
        description = f"{description}。{summary}"

    return description
