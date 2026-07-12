from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor, QFont
from tts_engine.segment_builder import ChunkInfo


class ReaderView(QPlainTextEdit):
    chunk_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Microsoft YaHei", 12))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setStyleSheet("""
            QPlainTextEdit {
                padding: 12px;
                line-height: 1.8;
                background-color: #faf9f6;
            }
        """)

        self._chunks: list[ChunkInfo] = []
        self._current_chunk_index: int = -1

    def set_text(self, text: str) -> None:
        self.clear()
        self._chunks = []
        self._current_chunk_index = -1
        self.setPlainText(text)

    def set_chunks(self, chunks: list[ChunkInfo]) -> None:
        self._chunks = chunks

    def highlight_chunk(self, char_start: int, char_end: int) -> None:
        doc = self.document()
        self._clear_highlights()

        plain_len = len(self.toPlainText())
        if char_start < 0 or char_end > plain_len:
            return

        current_fmt = QTextCharFormat()
        current_fmt.setBackground(QColor(255, 255, 0, 100))
        current_fmt.setFontWeight(700)

        cursor = QTextCursor(doc)
        cursor.setPosition(char_start)
        cursor.setPosition(char_end, QTextCursor.MoveMode.KeepAnchor)
        sel = QTextEdit.ExtraSelection()
        sel.format = current_fmt
        sel.cursor = cursor

        self._current_chunk_index = self._find_chunk_at_pos(char_start)
        self.setExtraSelections([sel])

    def _clear_highlights(self) -> None:
        self.setExtraSelections([])

    def mousePressEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        pos = cursor.position()

        if self._chunks:
            chunk_idx = self._find_chunk_at_pos(pos)
            if chunk_idx >= 0:
                self.chunk_clicked.emit(chunk_idx)

        super().mousePressEvent(event)

    def _find_chunk_at_pos(self, char_pos: int) -> int:
        if not self._chunks:
            return -1

        lo, hi = 0, len(self._chunks) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            chunk = self._chunks[mid]
            if chunk.char_start <= char_pos < chunk.char_end:
                return mid
            elif char_pos < chunk.char_start:
                hi = mid - 1
            else:
                lo = mid + 1

        return -1
