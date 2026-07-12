from __future__ import annotations

import hashlib
import os
import threading
import time
from collections.abc import Callable


class CacheManager:
    def __init__(self, cache_dir: str, max_size_mb: int = 500):
        """Initialize cache manager.

        Args:
            cache_dir: Path to cache directory (e.g. %APPDATA%/xMOD-AAE/cache/)
            max_size_mb: Maximum cache size in MB
        """
        self.cache_dir = cache_dir
        self.max_size_mb = max_size_mb
        self._lock = threading.Lock()
        os.makedirs(cache_dir, exist_ok=True)

    def get_cache_key(self, text: str, voice: str, speed: float) -> str:
        """Generate cache key: md5(text|voice|speed)."""
        content = f"{text}|{voice}|{speed:.1f}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def get_cached_path(self, text: str, voice: str, speed: float) -> str:
        """Get the expected cache file path for given parameters."""
        key = self.get_cache_key(text, voice, speed)
        return os.path.join(self.cache_dir, f"{key}.mp3")

    def exists(self, text: str, voice: str, speed: float) -> bool:
        """Check if a cache entry exists."""
        path = self.get_cached_path(text, voice, speed)
        return os.path.exists(path) and os.path.getsize(path) > 0

    def get_or_synthesize(
        self,
        text: str,
        voice: str,
        speed: float,
        synthesize_fn: Callable[[str, str, str], bool],
    ) -> str | None:
        """Get cached mp3 path or synthesize if not cached.

        Args:
            text: Text to synthesize
            voice: Voice ID
            speed: Playback speed (NOTE: for MVP, speed does not affect TTS pitch;
                   it only affects pygame playback rate. But the cache key still includes
                   speed in case future versions bake speed into TTS.)
            synthesize_fn: Callable(text, voice, output_path) -> bool

        Returns:
            Path to mp3 file, or None if synthesis failed.
        """
        path = self.get_cached_path(text, voice, speed)

        with self._lock:
            if self.exists(text, voice, speed):
                return path

        time.sleep(0.1)

        success = synthesize_fn(text, voice, path)

        if success:
            return path
        return None

    def clear_cache(self):
        """Delete all cached files."""
        with self._lock:
            for entry in os.listdir(self.cache_dir):
                if entry.endswith(".mp3"):
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
                if entry.endswith(".mp3"):
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
                if entry.endswith(".mp3"):
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
