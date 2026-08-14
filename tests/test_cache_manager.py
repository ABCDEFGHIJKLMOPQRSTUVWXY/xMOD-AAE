# -*- coding: utf-8 -*-
import os
import re
import time

from tts_engine.cache_manager import CacheManager


def _fake_synthesize_success(text: str, voice: str, output_path: str,
                             voice_params: dict | None = None) -> bool:
    with open(output_path, "wb") as f:
        f.write(b"\xff\xfb\x90\x00" * 100)
    return True


def _fake_synthesize_failure(text: str, voice: str, output_path: str,
                             voice_params: dict | None = None) -> bool:
    return False


class TestCacheManager:
    def test_get_cache_key_deterministic(self, tmp_cache):
        key1 = tmp_cache.get_cache_key("hello", "voice1", 1.0)
        key2 = tmp_cache.get_cache_key("hello", "voice1", 1.0)
        assert key1 == key2

    def test_get_cache_key_different_text(self, tmp_cache):
        key1 = tmp_cache.get_cache_key("hello", "voice1", 1.0)
        key2 = tmp_cache.get_cache_key("world", "voice1", 1.0)
        assert key1 != key2

    def test_get_cache_key_different_voice(self, tmp_cache):
        key1 = tmp_cache.get_cache_key("hello", "voice1", 1.0)
        key2 = tmp_cache.get_cache_key("hello", "voice2", 1.0)
        assert key1 != key2

    def test_get_cache_key_length(self, tmp_cache):
        key = tmp_cache.get_cache_key("hello", "voice1", 1.0)
        assert len(key) == 32
        assert re.fullmatch(r"[a-f0-9]{32}", key)

    def test_get_cached_path_extension(self, tmp_cache):
        path = tmp_cache.get_cached_path("hello", "voice1", 1.0)
        assert path.endswith(".mp3")

    def test_exists_false_no_file(self, tmp_cache):
        assert tmp_cache.exists("hello", "voice1", 1.0) is False

    def test_exists_true_after_synthesis(self, tmp_cache):
        path = tmp_cache.get_or_synthesize(
            "hello", "voice1", 1.0, _fake_synthesize_success
        )
        assert path is not None
        assert tmp_cache.exists("hello", "voice1", 1.0) is True

    def test_get_or_synthesize_returns_path(self, tmp_cache):
        path = tmp_cache.get_or_synthesize(
            "hello", "voice1", 1.0, _fake_synthesize_success
        )
        assert path is not None
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

    def test_get_or_synthesize_returns_none(self, tmp_cache):
        path = tmp_cache.get_or_synthesize(
            "hello", "voice1", 1.0, _fake_synthesize_failure
        )
        assert path is None

    def test_get_or_synthesize_cache_hit_skips_synth(self, tmp_cache):
        call_count = [0]

        def counting_synth(text: str, voice: str, output_path: str,
                           voice_params: dict | None = None) -> bool:
            call_count[0] += 1
            with open(output_path, "wb") as f:
                f.write(b"\xff\xfb\x90\x00" * 100)
            return True

        tmp_cache.get_or_synthesize("hello", "voice1", 1.0, counting_synth)
        assert call_count[0] == 1

        tmp_cache.get_or_synthesize("hello", "voice1", 1.0, counting_synth)
        assert call_count[0] == 1

    def test_clear_cache_removes_all(self, tmp_cache):
        tmp_cache.get_or_synthesize("a", "v", 1.0, _fake_synthesize_success)
        tmp_cache.get_or_synthesize("b", "v", 1.0, _fake_synthesize_success)
        assert tmp_cache.get_cache_size_mb() > 0

        tmp_cache.clear_cache()
        assert tmp_cache.get_cache_size_mb() == 0.0

    def test_get_cache_size_mb_positive(self, tmp_cache):
        tmp_cache.get_or_synthesize("hello", "voice1", 1.0, _fake_synthesize_success)
        size = tmp_cache.get_cache_size_mb()
        assert size > 0.0

    def test_enforce_size_limit_evicts_oldest(self, tmp_cache):
        file_old = os.path.join(tmp_cache.cache_dir, "old.mp3")
        file_new = os.path.join(tmp_cache.cache_dir, "new.mp3")
        chunk = b"\x00" * 1024

        with open(file_old, "wb") as f:
            f.write(chunk * 600)
        time.sleep(0.2)

        with open(file_new, "wb") as f:
            f.write(chunk * 600)
        time.sleep(0.2)

        assert os.path.exists(file_old)
        assert os.path.exists(file_new)
        assert tmp_cache.get_cache_size_mb() > 1.0

        tmp_cache.enforce_size_limit()

        assert not os.path.exists(file_old)
        assert os.path.exists(file_new)
        assert tmp_cache.get_cache_size_mb() <= 1.0

    def test_empty_cache_size_mb_zero(self, tmp_cache):
        assert tmp_cache.get_cache_size_mb() == 0.0


def _fake_synth_wav_sibling(text: str, voice: str, output_path: str,
                            voice_params: dict | None = None) -> bool:
    """Simulate a driver that keeps a WAV when ffmpeg conversion fails."""
    wav_path = os.path.splitext(output_path)[0] + ".wav"
    with open(wav_path, "wb") as f:
        f.write(b"RIFF" + b"\x00" * 200)
    return True


class TestCacheManagerDriverAware:
    def test_wav_extension_parametrization(self, tmp_path):
        cache = CacheManager(str(tmp_path), file_ext="wav")
        path = cache.get_cached_path("hello", "v1", 1.0)
        assert path.endswith(".wav")

        result = cache.get_or_synthesize(
            "hello", "v1", 1.0, _fake_synthesize_success
        )
        assert result is not None
        assert result.endswith(".wav")
        assert cache.exists("hello", "v1", 1.0)

    def test_key_isolation_by_driver(self, tmp_cache):
        key_edge = tmp_cache.get_cache_key("hello", "v1", 1.0, driver_id="edge-tts")
        key_mimo = tmp_cache.get_cache_key("hello", "v1", 1.0, driver_id="mimo")
        assert key_edge != key_mimo

    def test_key_isolation_by_voice_params(self, tmp_cache):
        key_a = tmp_cache.get_cache_key(
            "hello", "v1", 1.0, driver_id="mimo", voice_params={"voice_description": "A"}
        )
        key_b = tmp_cache.get_cache_key(
            "hello", "v1", 1.0, driver_id="mimo", voice_params={"voice_description": "B"}
        )
        assert key_a != key_b

    def test_key_ignores_param_order(self, tmp_cache):
        key_a = tmp_cache.get_cache_key(
            "hello", "v1", 1.0, voice_params={"a": 1, "b": 2}
        )
        key_b = tmp_cache.get_cache_key(
            "hello", "v1", 1.0, voice_params={"b": 2, "a": 1}
        )
        assert key_a == key_b

    def test_wav_fallback_sibling_is_served(self, tmp_cache):
        path = tmp_cache.get_or_synthesize(
            "hello", "v1", 1.0, _fake_synth_wav_sibling, driver_id="mimo"
        )
        assert path is not None
        assert path.endswith(".wav")
        assert os.path.exists(path)
        assert tmp_cache.exists("hello", "v1", 1.0, driver_id="mimo")

    def test_wav_fallback_and_mp3_cache_are_isolated(self, tmp_cache):
        tmp_cache.get_or_synthesize(
            "hello", "v1", 1.0, _fake_synth_wav_sibling, driver_id="mimo"
        )
        mp3_path = tmp_cache.get_cached_path("hello", "v1", 1.0, driver_id="edge-tts")
        assert not os.path.exists(mp3_path)
        assert tmp_cache.exists("hello", "v1", 1.0, driver_id="edge-tts") is False

    def test_clear_cache_removes_wav_fallback(self, tmp_cache):
        tmp_cache.get_or_synthesize(
            "hello", "v1", 1.0, _fake_synth_wav_sibling, driver_id="mimo"
        )
        assert tmp_cache.get_cache_size_mb() > 0.0
        tmp_cache.clear_cache()
        assert tmp_cache.get_cache_size_mb() == 0.0
