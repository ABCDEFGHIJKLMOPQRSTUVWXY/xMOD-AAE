from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable


class TTSDriver(ABC):
    """Abstract interface for a TTS backend engine.

    A driver wraps a concrete TTS engine (edge-tts, MiMo TTS, ...) behind a
    uniform interface so that the rest of the application can switch engines
    without knowing the implementation details.
    """

    id: str = ""
    display_name: str = ""
    output_format: str = "mp3"
    requires_api_key: bool = False

    def __init__(
        self,
        get_settings: Callable[[str, str], str] | None = None,
    ) -> None:
        """Initialize the driver.

        Args:
            get_settings: Optional callable ``(key, default) -> str`` used to
                read runtime settings (e.g. API keys, ffmpeg path). May be None
                for engines that never need settings.
        """
        self._get_settings = get_settings

    @abstractmethod
    def get_voices(self) -> list[dict]:
        """Return available voices with metadata.

        Each dict: {name, gender, locale, age_group, description}
        """

    @abstractmethod
    def get_default_narrator_voice(self) -> str:
        """Return the default narrator voice ID."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice: str,
        output_path: str,
        voice_params: dict | None = None,
        retries: int = 3,
    ) -> bool:
        """Synthesize text to an audio file at output_path.

        Args:
            text: Text to synthesize.
            voice: Voice ID to use.
            output_path: Where to write the final audio file.
            voice_params: Engine-specific synthesis parameters
                (e.g. {"voice_description": "..."} for MiMo voicedesign).
            retries: Number of attempts on failure.

        Returns:
            True if the file was written successfully.
        """

    def is_available(self) -> bool:
        """Whether the engine is usable right now (e.g. API key configured).

        Defaults to True; drivers requiring an API key override this.
        """
        return True
