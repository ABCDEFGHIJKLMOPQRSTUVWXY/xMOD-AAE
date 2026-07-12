from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont


class ChapterListWidget(QWidget):
    chapter_clicked = pyqtSignal(int)
    chapter_double_clicked = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QLabel("章节目录")
        header.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_clicked)
        self._list.itemDoubleClicked.connect(self._on_double_clicked)
        layout.addWidget(self._list)

    def set_chapters(self, titles: list[str]) -> None:
        self._list.clear()
        for i, title in enumerate(titles):
            item = QListWidgetItem(f"{i + 1}. {title}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self._list.addItem(item)

    def set_current(self, index: int) -> None:
        self._list.setCurrentRow(index)

    def _on_clicked(self, item: QListWidgetItem) -> None:
        index = item.data(Qt.ItemDataRole.UserRole)
        if index is not None:
            self.chapter_clicked.emit(index)

    def _on_double_clicked(self, item: QListWidgetItem) -> None:
        index = item.data(Qt.ItemDataRole.UserRole)
        if index is not None:
            self.chapter_double_clicked.emit(index)
