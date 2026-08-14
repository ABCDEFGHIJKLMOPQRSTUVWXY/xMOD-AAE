# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from character_engine.voice_mapper import assign_narrator_voice, assign_voice
from character_engine.llm_analyzer import CharacterProfile


EDGE_VOICES = [
    {"name": "zh-CN-XiaoxiaoNeural", "gender": "Female", "locale": "zh-CN", "age_group": "Child/YoungAdult"},
    {"name": "zh-CN-YunxiNeural", "gender": "Male", "locale": "zh-CN", "age_group": "Adult"},
    {"name": "zh-CN-YunjianNeural", "gender": "Male", "locale": "zh-CN", "age_group": "Adult"},
]

MIMO_VOICES = [
    {"name": "Chloe", "gender": "Female", "locale": "zh-CN", "age_group": "YoungAdult"},
]


def test_assign_voice_edge_returns_voice_id_with_no_params():
    profile = CharacterProfile(name="张三", gender="男", age_group="青年")
    driver, voice_id, voice_params = assign_voice(
        profile, EDGE_VOICES, set(), driver_id="edge-tts"
    )
    assert driver == "edge-tts"
    assert voice_id == "zh-CN-YunxiNeural"
    assert voice_params is None


def test_assign_voice_mimo_generates_voicedesign_params():
    profile = CharacterProfile(
        name="张三", gender="男", age_group="中年",
        personality=["沉稳"], speaking_style="低沉",
    )
    driver, voice_id, voice_params = assign_voice(
        profile, MIMO_VOICES, set(), driver_id="mimo"
    )
    assert driver == "mimo"
    assert voice_params is not None
    assert "沉稳" in voice_params["voice_description"]


def test_assign_voice_mimo_empty_profile_uses_builtin():
    profile = CharacterProfile(name="X", gender="未知", age_group="未知")
    driver, voice_id, voice_params = assign_voice(
        profile, MIMO_VOICES, set(), driver_id="mimo"
    )
    assert voice_id == "Chloe"
    assert voice_params is None


def test_assign_voice_avoids_used_voices():
    profile = CharacterProfile(name="李四", gender="男", age_group="青年")
    driver, voice_id, _ = assign_voice(
        profile, EDGE_VOICES, {"zh-CN-YunxiNeural"}, driver_id="edge-tts"
    )
    assert voice_id != "zh-CN-YunxiNeural"


def test_assign_narrator_voice_returns_three_elements():
    settings = {"narrator_voice": "zh-CN-XiaoxiaoNeural"}
    driver, voice_id, voice_params = assign_narrator_voice(settings, EDGE_VOICES)
    assert driver == "edge-tts"
    assert voice_id == "zh-CN-XiaoxiaoNeural"
    assert voice_params is None


def test_assign_narrator_voice_mimo_reads_params():
    settings = {
        "narrator_voice": "Chloe",
        "narrator_voice_params": '{"voice_description": "温柔的旁白"}',
    }
    driver, voice_id, voice_params = assign_narrator_voice(settings, MIMO_VOICES, driver_id="mimo")
    assert driver == "mimo"
    assert voice_id == "Chloe"
    assert voice_params == {"voice_description": "温柔的旁白"}
