from __future__ import annotations

_CHINESE_VOICES: list[dict] = [
    {
        "name": "zh-CN-XiaoxiaoNeural",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "Child/YoungAdult",
        "description": "普通话 - 晓晓 (活泼、温暖)",
    },
    {
        "name": "zh-CN-XiaoyiNeural",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "Child/YoungAdult",
        "description": "普通话 - 晓伊 (天真、可爱)",
    },
    {
        "name": "zh-CN-YunjianNeural",
        "gender": "Male",
        "locale": "zh-CN",
        "age_group": "Adult",
        "description": "普通话 - 云健 (稳重、成熟)",
    },
    {
        "name": "zh-CN-YunxiNeural",
        "gender": "Male",
        "locale": "zh-CN",
        "age_group": "Adult",
        "description": "普通话 - 云希 (阳光、青春)",
    },
    {
        "name": "zh-CN-YunxiaNeural",
        "gender": "Male",
        "locale": "zh-CN",
        "age_group": "Child",
        "description": "普通话 - 云夏 (童声)",
    },
    {
        "name": "zh-CN-YunyangNeural",
        "gender": "Male",
        "locale": "zh-CN",
        "age_group": "Adult",
        "description": "普通话 - 云扬 (播音腔、大气)",
    },
    {
        "name": "zh-CN-liaoning-XiaobeiNeural",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "YoungAdult",
        "description": "辽宁话 - 小北 (东北味儿)",
    },
    {
        "name": "zh-CN-shaanxi-XiaoniNeural",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "YoungAdult",
        "description": "陕西话 - 小妮 (西北味儿)",
    },
    {
        "name": "zh-CN-XiaochenNeural",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "YoungAdult",
        "description": "普通话 - 晓辰",
    },
    {
        "name": "zh-CN-XiaohanNeural",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "YoungAdult",
        "description": "普通话 - 晓涵",
    },
    {
        "name": "zh-CN-XiaomengNeural",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "YoungAdult",
        "description": "普通话 - 晓梦",
    },
    {
        "name": "zh-CN-XiaomoNeural",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "YoungAdult",
        "description": "普通话 - 晓墨",
    },
    {
        "name": "zh-CN-XiaoqiuNeural",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "YoungAdult",
        "description": "普通话 - 晓秋",
    },
    {
        "name": "zh-CN-XiaoruiNeural",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "YoungAdult",
        "description": "普通话 - 晓睿",
    },
    {
        "name": "zh-CN-XiaoshuangNeural",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "YoungAdult",
        "description": "普通话 - 晓双",
    },
    {
        "name": "zh-CN-XiaoxuanNeural",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "YoungAdult",
        "description": "普通话 - 晓萱",
    },
    {
        "name": "zh-CN-XiaoyanNeural",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "YoungAdult",
        "description": "普通话 - 晓颜",
    },
    {
        "name": "zh-CN-XiaozhenNeural",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "YoungAdult",
        "description": "普通话 - 晓甄",
    },
    {
        "name": "zh-CN-YunfengNeural",
        "gender": "Male",
        "locale": "zh-CN",
        "age_group": "Adult",
        "description": "普通话 - 云枫 (稳重、低沉)",
    },
    {
        "name": "zh-CN-YunhaoNeural",
        "gender": "Male",
        "locale": "zh-CN",
        "age_group": "Adult",
        "description": "普通话 - 云皓",
    },
    {
        "name": "zh-CN-YunyeNeural",
        "gender": "Male",
        "locale": "zh-CN",
        "age_group": "Adult",
        "description": "普通话 - 云野",
    },
    {
        "name": "zh-CN-YunzeNeural",
        "gender": "Male",
        "locale": "zh-CN",
        "age_group": "Adult",
        "description": "普通话 - 云泽",
    },
    {
        "name": "zh-HK-HiuGaaiNeural",
        "gender": "Female",
        "locale": "zh-HK",
        "age_group": "YoungAdult",
        "description": "粤语 - 晓佳",
    },
    {
        "name": "zh-HK-HiuMaanNeural",
        "gender": "Female",
        "locale": "zh-HK",
        "age_group": "YoungAdult",
        "description": "粤语 - 晓曼",
    },
    {
        "name": "zh-HK-WanLungNeural",
        "gender": "Male",
        "locale": "zh-HK",
        "age_group": "YoungAdult",
        "description": "粤语 - 云龙",
    },
    {
        "name": "zh-TW-HsiaoChenNeural",
        "gender": "Female",
        "locale": "zh-TW",
        "age_group": "YoungAdult",
        "description": "台湾国语 - 晓臻",
    },
    {
        "name": "zh-TW-HsiaoYuNeural",
        "gender": "Female",
        "locale": "zh-TW",
        "age_group": "YoungAdult",
        "description": "台湾国语 - 晓雨",
    },
    {
        "name": "zh-TW-YunJheNeural",
        "gender": "Male",
        "locale": "zh-TW",
        "age_group": "YoungAdult",
        "description": "台湾国语 - 云哲",
    },
]


def get_voices() -> list[dict]:
    """Return list of available Chinese edge-tts voices with metadata.

    Each dict: {name, gender, locale, age_group, description}
    """
    return list(_CHINESE_VOICES)


def get_default_narrator_voice() -> str:
    """Return the default narrator voice ID."""
    return "zh-CN-XiaoxiaoNeural"


def get_voice_by_name(name: str) -> dict | None:
    """Find a voice by its name/ID."""
    for voice in _CHINESE_VOICES:
        if voice["name"] == name:
            return voice
    return None
