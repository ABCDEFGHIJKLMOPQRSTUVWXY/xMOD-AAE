from __future__ import annotations

from tts_engine.voice_registry import (
    get_default_narrator_voice,
    get_voice_by_name,
    get_voices,
)
from tts_engine.edge_tts_client import synthesize, synthesize_sync
from tts_engine.cache_manager import CacheManager
from tts_engine.segment_builder import ChunkInfo, build

__all__ = [
    "get_voices",
    "get_default_narrator_voice",
    "get_voice_by_name",
    "synthesize",
    "synthesize_sync",
    "CacheManager",
    "ChunkInfo",
    "build",
]
