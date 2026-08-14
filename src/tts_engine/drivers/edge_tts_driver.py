from __future__ import annotations

from tts_engine.drivers.base import TTSDriver
from tts_engine.edge_tts_client import synthesize_sync
from tts_engine.voice_registry import (
    get_default_narrator_voice,
    get_voices,
)


class EdgeTTSDriver(TTSDriver):
    """Driver wrapping the existing edge-tts engine."""

    id = "edge-tts"
    display_name = "Edge TTS"
    output_format = "mp3"
    requires_api_key = False

    def get_voices(self) -> list[dict]:
        return get_voices()

    def get_default_narrator_voice(self) -> str:
        return get_default_narrator_voice()

    def synthesize(
        self,
        text: str,
        voice: str,
        output_path: str,
        voice_params: dict | None = None,
        retries: int = 3,
    ) -> bool:
        return synthesize_sync(text, voice, output_path, retries)
