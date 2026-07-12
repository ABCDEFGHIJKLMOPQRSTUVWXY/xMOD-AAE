from PyQt6.QtCore import QThread, pyqtSignal
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
        self._synthesize_fn = None
        self._preload_count: int = 5

    def configure(self, chunks: list, start_index: int, speed: float,
                  cache_manager, synthesize_fn, preload_count: int = 5):
        self._chunks = chunks
        self._start_index = start_index
        self._speed = speed
        self._cache_manager = cache_manager
        self._synthesize_fn = synthesize_fn
        self._preload_count = preload_count
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        end = min(self._start_index + 1 + self._preload_count, len(self._chunks))
        for i in range(self._start_index + 1, end):
            if self._cancelled:
                break

            chunk = self._chunks[i]
            if chunk.ready_event.is_set():
                self.chunk_ready.emit(i)
                continue

            path = self._cache_manager.get_or_synthesize(
                chunk.text, chunk.voice_id, self._speed, self._synthesize_fn
            )

            if path and not self._cancelled:
                chunk.mp3_path = path
                try:
                    from mutagen.mp3 import MP3
                    audio = MP3(path)
                    chunk.duration_ms = audio.info.length * 1000
                except Exception:
                    chunk.duration_ms = 0.0
                chunk.ready_event.set()
                self.chunk_ready.emit(i)

            if not self._cancelled:
                time.sleep(0.15)
