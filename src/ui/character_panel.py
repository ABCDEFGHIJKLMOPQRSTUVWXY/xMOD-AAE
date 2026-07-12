from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QComboBox, QGroupBox, QTextEdit,
    QHBoxLayout,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont


class CharacterPanel(QWidget):
    voice_changed = pyqtSignal(str, str)
    reanalyze_requested = pyqtSignal()

    def __init__(self, available_voices: list[dict], parent=None):
        super().__init__(parent)
        self._available_voices: list[dict] = available_voices
        self._characters: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QLabel("角色列表")
        header.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        layout.addWidget(header)

        hint = QLabel("导入书籍后，使用\n菜单 → 角色 → 分析角色\n来检测小说中的角色")
        hint.setStyleSheet("color: gray; padding: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_character_selected)
        layout.addWidget(self._list)

        self._detail_group = QGroupBox("角色详情")
        detail_layout = QVBoxLayout(self._detail_group)

        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        self._detail_text.setMaximumHeight(120)
        detail_layout.addWidget(self._detail_text)

        voice_layout = QHBoxLayout()
        voice_layout.addWidget(QLabel("语音:"))
        self._voice_combo = QComboBox()
        self._voice_combo.currentTextChanged.connect(self._on_voice_changed)
        voice_layout.addWidget(self._voice_combo, 1)
        detail_layout.addLayout(voice_layout)

        self._detail_group.setLayout(detail_layout)
        self._detail_group.hide()
        layout.addWidget(self._detail_group)

        layout.addStretch()

    def set_characters(self, characters: list[dict]) -> None:
        self._characters = characters
        self._list.clear()

        if not characters:
            self._detail_group.hide()
            return

        for char in characters:
            name = char.get("name", "未知")
            gender = char.get("gender", "未知")
            role = char.get("role_type", "未知")
            text = f"{name}  [{gender}·{role}]"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, char)
            self._list.addItem(item)

    def _on_character_selected(self, index: int) -> None:
        if index < 0 or index >= len(self._characters):
            self._detail_group.hide()
            return

        char = self._characters[index]
        self._detail_group.show()

        lines = [
            f"姓名：{char.get('name', '未知')}",
            f"性别：{char.get('gender', '未知')}",
            f"年龄段：{char.get('age_group', '未知')}",
            f"角色类型：{char.get('role_type', '未知')}",
            f"说话风格：{char.get('speaking_style', '—')}",
            f"简介：{char.get('summary', '—')}",
        ]
        self._detail_text.setPlainText("\n".join(lines))

        self._voice_combo.blockSignals(True)
        self._voice_combo.clear()
        current_voice = char.get("voice_id", "")

        for voice in self._available_voices:
            name = voice.get("name", "")
            desc = voice.get("description", name)
            label = f"{desc}"
            self._voice_combo.addItem(label, name)
            if name == current_voice:
                self._voice_combo.setCurrentIndex(self._voice_combo.count() - 1)

        self._voice_combo.blockSignals(False)

    def _on_voice_changed(self, text: str) -> None:
        voice_id = self._voice_combo.currentData()
        current_row = self._list.currentRow()
        if current_row >= 0 and current_row < len(self._characters) and voice_id:
            speaker_name = self._characters[current_row].get("name", "")
            if speaker_name:
                self.voice_changed.emit(speaker_name, voice_id)
