from PyQt6.QtCore import QThread, pyqtSignal
import os
import time


class ChunkQueue(QThread):
    chunk_ready = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chunks: list = []
        self._start_index: int = 0
        self._speed: float = 1.0
        self._cancelled: bool = False
        self._cache_manager = None
        self._driver_manager = None
        self._default_driver_id: str = "edge-tts"
        self._preload_count: int = 5

    def configure(self, chunks: list, start_index: int, speed: float,
                  cache_manager, driver_manager, default_driver_id: str = "edge-tts",
                  preload_count: int = 5):
        self._chunks = chunks
        self._start_index = start_index
        self._speed = speed
        self._cache_manager = cache_manager
        self._driver_manager = driver_manager
        self._default_driver_id = default_driver_id
        self._preload_count = preload_count
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        end = min(self._start_index + 1 + self._preload_count, len(self._chunks))
        for i in range(self._start_index, end):
            if self._cancelled:
                break

            chunk = self._chunks[i]
            if chunk.ready_event.is_set():
                self.chunk_ready.emit(i)
                continue

            driver = self._resolve_driver(chunk)
            if driver is None:
                chunk.ready_event.set()
                self.chunk_ready.emit(i)
                continue

            path = self._cache_manager.get_or_synthesize(
                chunk.text, chunk.voice_id, self._speed,
                driver.synthesize,
                driver_id=driver.id,
                voice_params=chunk.voice_params,
            )

            if path and not self._cancelled:
                chunk.mp3_path = path
                try:
                    chunk.duration_ms = self._read_duration(path) * 1000
                except Exception:
                    chunk.duration_ms = 0.0
                chunk.ready_event.set()
                self.chunk_ready.emit(i)

            if not self._cancelled:
                time.sleep(0.15)

    def _resolve_driver(self, chunk):
        """Pick the driver for a chunk: the one stored on the chunk (from the
        book's voice_map) falls back to the current/default driver."""
        if self._driver_manager is None:
            return None
        driver_id = getattr(chunk, "driver_id", "") or self._default_driver_id
        driver = self._driver_manager.get_driver(driver_id)
        if driver is None:
            driver = self._driver_manager.get_current_driver()
        return driver

    @staticmethod
    def _read_duration(path: str) -> float:
        """Read audio duration in seconds, dispatching by file extension."""
        ext = os.path.splitext(path)[1].lower()
        if ext == ".wav":
            from mutagen.wave import WAVE
            return float(WAVE(path).info.length)
        from mutagen.mp3 import MP3
        return float(MP3(path).info.length)
