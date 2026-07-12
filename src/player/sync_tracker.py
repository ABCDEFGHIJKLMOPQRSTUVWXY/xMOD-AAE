from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from tts_engine.segment_builder import ChunkInfo


class SyncTracker(QObject):
    highlight_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chunks: list = []
        self._current_index: int = -1
        self._position_ms: float = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

    def start_tracking(self, chunks: list, start_index: int = 0):
        self._chunks = chunks
        self._current_index = start_index
        self._position_ms = 0.0
        self._timer.start()
        if start_index < len(chunks):
            chunk = chunks[start_index]
            self.highlight_changed.emit(chunk.char_start, chunk.char_end)

    def advance_chunk(self, new_index: int):
        if 0 <= new_index < len(self._chunks):
            self._current_index = new_index
            self._position_ms = 0.0
            chunk = self._chunks[new_index]
            self.highlight_changed.emit(chunk.char_start, chunk.char_end)

    def stop(self):
        self._timer.stop()
        self._position_ms = 0.0

    def _tick(self):
        if self._current_index < 0 or self._current_index >= len(self._chunks):
            return
        self._position_ms += 50
