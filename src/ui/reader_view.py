from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor, QFont
from tts_engine.segment_builder import ChunkInfo


class ReaderView(QPlainTextEdit):
    chunk_clicked = pyqtSignal(int)

    # ── 分段高亮配色 ──────────────────────────────────────────────
    DIALOGUE_BG = QColor(173, 216, 230, 45)   # 浅蓝：对话
    NARRATION_BG = QColor(245, 245, 245, 30)  # 浅灰：旁白
    PLAY_BG = QColor(255, 255, 0, 100)        # 黄底：当前播放

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
        self._segment_selections: list[QTextEdit.ExtraSelection] = []
        self._show_segments: bool = True

    # ── 文本加载 ──────────────────────────────────────────────────

    def set_text(self, text: str) -> None:
        self.clear()
        self._chunks = []
        self._current_chunk_index = -1
        self._segment_selections = []
        self.setPlainText(text)

    def set_chunks(self, chunks: list[ChunkInfo]) -> None:
        self._chunks = chunks

    # ── 结构化分段叠加 ───────────────────────────────────────────

    def set_segments(self, segments: list[tuple[int, int, bool]]) -> None:
        """接受全局偏移量的分段列表，构建背景色 ExtraSelections。

        Args:
            segments: [(char_start, char_end, is_dialogue), ...]
                      偏移量基于文本内容一致计算。
        """
        doc = self.document()
        self._segment_selections = []
        if not segments:
            return

        dialogue_fmt = QTextCharFormat()
        dialogue_fmt.setBackground(self.DIALOGUE_BG)

        narration_fmt = QTextCharFormat()
        narration_fmt.setBackground(self.NARRATION_BG)

        plain_len = len(self.toPlainText())

        for start, end, is_dialogue in segments:
            if start < 0 or end > plain_len or end <= start:
                continue
            cursor = QTextCursor(doc)
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            sel = QTextEdit.ExtraSelection()
            sel.format = dialogue_fmt if is_dialogue else narration_fmt
            sel.cursor = cursor
            self._segment_selections.append(sel)

        if self._show_segments:
            self.setExtraSelections(self._segment_selections)

    def set_show_segments(self, visible: bool) -> None:
        """切换分段叠加的显示/隐藏。"""
        self._show_segments = visible
        if visible and self._segment_selections:
            self.setExtraSelections(self._segment_selections)
        else:
            self.setExtraSelections([])

    # ── 播放高亮 ──────────────────────────────────────────────────

    def highlight_chunk(self, char_start: int, char_end: int) -> None:
        doc = self.document()

        plain_len = len(self.toPlainText())
        if char_start < 0 or char_end > plain_len:
            return

        # 基底：分段高亮（若启用）
        selections = list(self._segment_selections) if self._show_segments else []

        # 顶层：播放高亮
        play_fmt = QTextCharFormat()
        play_fmt.setBackground(self.PLAY_BG)
        play_fmt.setFontWeight(700)

        cursor = QTextCursor(doc)
        cursor.setPosition(char_start)
        cursor.setPosition(char_end, QTextCursor.MoveMode.KeepAnchor)
        play_sel = QTextEdit.ExtraSelection()
        play_sel.format = play_fmt
        play_sel.cursor = cursor
        selections.append(play_sel)

        self._current_chunk_index = self._find_chunk_at_pos(char_start)
        self.setExtraSelections(selections)

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
