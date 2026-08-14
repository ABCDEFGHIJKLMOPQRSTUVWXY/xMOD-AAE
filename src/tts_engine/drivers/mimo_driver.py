from __future__ import annotations

import base64
import os
import sys
import time

import httpx

from tts_engine.audio_converter import wav_to_mp3
from tts_engine.drivers.base import TTSDriver

_API_URL = "https://api.xiaomimimo.com/v1/chat/completions"
_MODEL_BUILTIN = "mimo-v2.5-tts"
_MODEL_VOICEDESIGN = "mimo-v2.5-tts-voicedesign"

# 内置精品音色。官方文档目前仅公开示例音色 `Chloe`，
# 完整中文音色列表需向小米官方确认后补全。
# TODO: 向官方确认完整内置音色列表后替换为全量数据。
_MIMO_VOICES: list[dict] = [
    {
        "name": "Chloe",
        "gender": "Female",
        "locale": "zh-CN",
        "age_group": "YoungAdult",
        "description": "MiMo 内置音色 - Chloe",
    },
]


class MiMoTTSDriver(TTSDriver):
    """Driver for the Xiaomi MiMo TTS API.

    Supports two modes:
    - built-in voice: ``mimo-v2.5-tts`` with a named voice.
    - voicedesign: ``mimo-v2.5-tts-voicedesign`` with a natural-language
      voice description (``voice_params["voice_description"]``).

    The API returns WAV audio which is converted to MP3 via ffmpeg before
    being cached. If ffmpeg is unavailable the WAV is kept (see
    :mod:`tts_engine.audio_converter`).
    """

    id = "mimo"
    display_name = "MiMo TTS"
    output_format = "wav"
    requires_api_key = True

    def get_voices(self) -> list[dict]:
        return list(_MIMO_VOICES)

    def get_default_narrator_voice(self) -> str:
        return "Chloe"

    def is_available(self) -> bool:
        if self._get_settings is None:
            return False
        return bool(self._get_settings("mimo_api_key", "").strip())

    def synthesize(
        self,
        text: str,
        voice: str,
        output_path: str,
        voice_params: dict | None = None,
        retries: int = 3,
    ) -> bool:
        if not self.is_available():
            print(
                "[MiMo] API key not configured, cannot synthesize",
                file=sys.stderr,
            )
            return False

        wav_bytes: bytes | None = None
        for attempt in range(retries):
            try:
                wav_bytes = self._request_audio(text, voice, voice_params)
                break
            except Exception as e:
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    print(
                        f"[MiMo] synthesis failed (attempt {attempt + 1}/{retries}): {e}. "
                        f"Retrying in {wait}s...",
                        file=sys.stderr,
                    )
                    time.sleep(wait)
                else:
                    print(
                        f"[MiMo] synthesis failed after {retries} attempts: {e}",
                        file=sys.stderr,
                    )
                    return False

        tmp_wav = output_path + ".tmp.wav"
        try:
            with open(tmp_wav, "wb") as f:
                f.write(wav_bytes)
        except OSError as e:
            print(f"[MiMo] failed to write temp wav: {e}", file=sys.stderr)
            return False

        ffmpeg = ""
        if self._get_settings is not None:
            ffmpeg = self._get_settings("ffmpeg_path", "")

        if wav_to_mp3(tmp_wav, output_path, ffmpeg):
            try:
                os.remove(tmp_wav)
            except OSError:
                pass
            return True

        # ffmpeg 不可用时降级保留 WAV，缓存按实际落地扩展名处理。
        wav_path = os.path.splitext(output_path)[0] + ".wav"
        try:
            os.replace(tmp_wav, wav_path)
            return True
        except OSError as e:
            print(f"[MiMo] failed to keep wav fallback: {e}", file=sys.stderr)
            try:
                os.remove(tmp_wav)
            except OSError:
                pass
            return False

    def _request_audio(
        self,
        text: str,
        voice: str,
        voice_params: dict | None,
    ) -> bytes:
        assert self._get_settings is not None
        api_key = self._get_settings("mimo_api_key", "").strip()
        if not api_key:
            raise RuntimeError("MiMo API key not configured")

        voice_description = str((voice_params or {}).get("voice_description", "") or "").strip()
        if voice_description:
            model = _MODEL_VOICEDESIGN
            messages = [
                {"role": "user", "content": voice_description},
                {"role": "assistant", "content": text},
            ]
            audio = {"format": "wav", "optimize_text_preview": True}
        else:
            model = _MODEL_BUILTIN
            messages = [
                {"role": "user", "content": "请朗读以下文本"},
                {"role": "assistant", "content": text},
            ]
            audio = {"format": "wav", "voice": voice}

        payload = {"model": model, "messages": messages, "audio": audio}
        resp = httpx.post(
            _API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(60.0),
        )
        resp.raise_for_status()
        data = resp.json()

        choices = data.get("choices") or [{}]
        message = choices[0].get("message") or {}
        audio = message.get("audio") or {}
        b64 = audio.get("data") or audio.get("base64") or ""
        if not b64:
            raise RuntimeError("MiMo response missing audio data")
        return base64.b64decode(b64)
