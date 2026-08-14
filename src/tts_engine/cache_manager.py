from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections.abc import Callable


class CacheManager:
    def __init__(self, cache_dir: str, max_size_mb: int = 500, file_ext: str = "mp3"):
        """Initialize cache manager.

        Args:
            cache_dir: Path to cache directory (e.g. %APPDATA%/xMOD-AAE/cache/)
            max_size_mb: Maximum cache size in MB
            file_ext: Default audio extension for cached files (e.g. "mp3").
        """
        self.cache_dir = cache_dir
        self.max_size_mb = max_size_mb
        self.file_ext = str(file_ext).lstrip(".")
        self._lock = threading.Lock()
        os.makedirs(cache_dir, exist_ok=True)

    def get_cache_key(
        self,
        text: str,
        voice: str,
        speed: float,
        driver_id: str = "edge-tts",
        voice_params: dict | None = None,
    ) -> str:
        """Generate cache key: md5(driver_id|voice|json(voice_params)|text|speed).

        The driver id and voice_params are part of the key so that switching
        engines (or editing a voicedesign description) never reuses stale audio.
        """
        params_json = json.dumps(voice_params or {}, ensure_ascii=False, sort_keys=True)
        content = f"{driver_id}|{voice}|{params_json}|{text}|{speed:.1f}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def get_cached_path(
        self,
        text: str,
        voice: str,
        speed: float,
        driver_id: str = "edge-tts",
        voice_params: dict | None = None,
    ) -> str:
        """Get the expected cache file path for given parameters."""
        key = self.get_cache_key(text, voice, speed, driver_id, voice_params)
        return os.path.join(self.cache_dir, f"{key}.{self.file_ext}")

    def _candidate_paths(
        self,
        text: str,
        voice: str,
        speed: float,
        driver_id: str = "edge-tts",
        voice_params: dict | None = None,
    ) -> list[str]:
        """Return the expected path plus the .wav fallback sibling.

        When ffmpeg is unavailable a driver may store the synthesized WAV next
        to the mp3 path (same key, ".wav" extension). Both are considered when
        checking for a cache hit so playback and duration parsing keep working.
        """
        path = self.get_cached_path(text, voice, speed, driver_id, voice_params)
        candidates = [path]
        base, _ext = os.path.splitext(path)
        if self.file_ext != "wav":
            candidates.append(base + ".wav")
        return candidates

    def exists(
        self,
        text: str,
        voice: str,
        speed: float,
        driver_id: str = "edge-tts",
        voice_params: dict | None = None,
    ) -> bool:
        """Check if a cache entry exists."""
        for path in self._candidate_paths(text, voice, speed, driver_id, voice_params):
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return True
        return False

    def get_or_synthesize(
        self,
        text: str,
        voice: str,
        speed: float,
        synthesize_fn: Callable[[str, str, str, dict | None], bool],
        driver_id: str = "edge-tts",
        voice_params: dict | None = None,
    ) -> str | None:
        """Get cached audio path or synthesize if not cached.

        Args:
            text: Text to synthesize
            voice: Voice ID
            speed: Playback speed (NOTE: for MVP, speed does not affect TTS pitch;
                   it only affects pygame playback rate. But the cache key still
                   includes speed in case future versions bake speed into TTS.)
            synthesize_fn: Callable(text, voice, output_path, voice_params) -> bool
            driver_id: Engine driver id (part of the cache key)
            voice_params: Engine-specific synthesis parameters (part of the key)

        Returns:
            Path to the cached audio file, or None if synthesis failed.
        """
        candidates = self._candidate_paths(text, voice, speed, driver_id, voice_params)

        with self._lock:
            for path in candidates:
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    return path

        time.sleep(0.1)

        path = candidates[0]
        success = synthesize_fn(text, voice, path, voice_params)

        if not success:
            return None

        for candidate in candidates:
            if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
                return candidate
        return None

    def clear_cache(self):
        """Delete all cached files."""
        with self._lock:
            for entry in os.listdir(self.cache_dir):
                if self._is_cache_file(entry):
                    full_path = os.path.join(self.cache_dir, entry)
                    try:
                        os.remove(full_path)
                    except OSError:
                        pass

    def get_cache_size_mb(self) -> float:
        """Get current cache size in MB."""
        total = 0
        with self._lock:
            for entry in os.listdir(self.cache_dir):
                if self._is_cache_file(entry):
                    full_path = os.path.join(self.cache_dir, entry)
                    try:
                        total += os.path.getsize(full_path)
                    except OSError:
                        pass
        return total / (1024 * 1024)

    def enforce_size_limit(self):
        """Delete oldest cache files if cache exceeds max_size_mb."""
        with self._lock:
            entries = []
            for entry in os.listdir(self.cache_dir):
                if self._is_cache_file(entry):
                    full_path = os.path.join(self.cache_dir, entry)
                    try:
                        atime = os.path.getatime(full_path)
                        size = os.path.getsize(full_path)
                        entries.append((atime, size, full_path))
                    except OSError:
                        pass

            entries.sort(key=lambda x: x[0])

            total_size = sum(e[1] for e in entries)
            target_size = self.max_size_mb * 1024 * 1024

            for _, size, full_path in entries:
                if total_size <= target_size:
                    break
                try:
                    os.remove(full_path)
                    total_size -= size
                except OSError:
                    pass

    def _is_cache_file(self, entry: str) -> bool:
        """True for files belonging to this cache (either configured ext or the
        .wav fallback sibling)."""
        if not os.path.isfile(os.path.join(self.cache_dir, entry)):
            return False
        return entry.endswith(f".{self.file_ext}") or entry.endswith(".wav")
