# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from character_engine.voice_design import build_voice_description
from character_engine.llm_analyzer import CharacterProfile


def test_rich_profile_description():
    profile = CharacterProfile(
        name="张三",
        gender="男",
        age_group="中年",
        personality=["沉稳", "果断"],
        speaking_style="语速缓慢、语气低沉",
        summary="一位老练的将军",
    )
    desc = build_voice_description(profile)
    assert "中年" in desc
    assert "男" in desc
    assert "语速缓慢" in desc
    assert "沉稳" in desc
    assert "将军" in desc


def test_unknown_gender_age_omitted():
    profile = CharacterProfile(name="X", gender="未知", age_group="未知")
    desc = build_voice_description(profile)
    assert desc == ""


def test_unknown_but_style_present():
    profile = CharacterProfile(
        name="X", gender="未知", age_group="未知", speaking_style="活泼"
    )
    desc = build_voice_description(profile)
    assert "活泼" in desc
    assert "未知" not in desc


def test_empty_profile_returns_empty():
    profile = CharacterProfile(name="X")
    assert build_voice_description(profile) == ""
