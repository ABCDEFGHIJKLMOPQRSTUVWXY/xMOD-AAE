# -*- coding: utf-8 -*-
import os
import shutil
import sys
import wave

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tts_engine.audio_converter import wav_to_mp3


def _write_silent_wav(path: str, seconds: float = 0.1) -> None:
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        frames = b"\x00\x00" * int(16000 * seconds)
        f.writeframes(frames)


def test_wav_to_mp3_missing_ffmpeg(tmp_path):
    wav = str(tmp_path / "in.wav")
    mp3 = str(tmp_path / "out.mp3")
    _write_silent_wav(wav)
    assert wav_to_mp3(wav, mp3, "ffmpeg-definitely-not-installed-xyz") is False
    assert not os.path.exists(mp3)


def test_wav_to_mp3_empty_ffmpeg_path_tries_path(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not available on this machine")
    wav = str(tmp_path / "in.wav")
    mp3 = str(tmp_path / "out.mp3")
    _write_silent_wav(wav)
    assert wav_to_mp3(wav, mp3, "") is True
    assert os.path.exists(mp3)
    assert os.path.getsize(mp3) > 0


def test_wav_to_mp3_converts_when_ffmpeg_available(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not available on this machine")
    wav = str(tmp_path / "in.wav")
    mp3 = str(tmp_path / "out.mp3")
    _write_silent_wav(wav)
    assert wav_to_mp3(wav, mp3, shutil.which("ffmpeg")) is True
    assert os.path.exists(mp3)
    assert os.path.getsize(mp3) > 0
