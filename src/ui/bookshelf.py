from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
from config import get_app_data_dir, get_db_path
from character_engine.character_store import CharacterStore


class BookshelfWidget(QWidget):
    book_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = CharacterStore(get_db_path())
        self._store.init_db()

        layout = QVBoxLayout(self)

        title = QLabel("书架")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        hint = QLabel("导入一个txt文件来开始阅读\n支持：Chinese/UTF-8编码的文本文件\n菜单：文件 → 导入书籍")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: gray; padding: 20px;")
        layout.addWidget(hint)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_double_clicked)
        self._list.setAlternatingRowColors(True)
        layout.addWidget(self._list)

        self.refresh()

    def refresh(self) -> None:
        self._list.clear()
        books = self._store.get_books()
        for book in books:
            item = QListWidgetItem(book["title"])
            item.setData(Qt.ItemDataRole.UserRole, book["id"])
            item.setToolTip(f"文件：{book['filepath']}\nID：{book['id']}")
            self._list.addItem(item)

    def _on_double_clicked(self, item: QListWidgetItem) -> None:
        book_id = item.data(Qt.ItemDataRole.UserRole)
        if book_id:
            self.book_selected.emit(book_id)
