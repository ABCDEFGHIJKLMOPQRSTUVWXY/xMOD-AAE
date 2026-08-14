import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QComboBox, QGroupBox, QTextEdit,
    QHBoxLayout,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont


class CharacterPanel(QWidget):
    voice_changed = pyqtSignal(str, str, str, object)  # (speaker, driver, voice_id, voice_params)

    def __init__(self, available_voices: list[dict], current_driver_id: str = "edge-tts",
                 parent=None):
        super().__init__(parent)
        self._available_voices: list[dict] = available_voices
        self._current_driver_id: str = current_driver_id
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
        voice_layout.addWidget(self._voice_combo, 1)
        detail_layout.addLayout(voice_layout)

        self._desc_group = QGroupBox("音色描述 (MiMo voicedesign)")
        desc_layout = QVBoxLayout(self._desc_group)
        self._desc_edit = QTextEdit()
        self._desc_edit.setMaximumHeight(80)
        self._desc_edit.setPlaceholderText(
            "自然语言描述音色，例如：一位温柔成熟的女性，说话缓慢而沉稳。"
            "留空则使用内置音色。"
        )
        desc_layout.addWidget(self._desc_edit)
        detail_layout.addWidget(self._desc_group)

        self._detail_group.setLayout(detail_layout)
        self._detail_group.hide()
        layout.addWidget(self._detail_group)

        layout.addStretch()

        self._voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        self._desc_edit.textChanged.connect(self._on_description_changed)

    def set_driver(self, driver_id: str, available_voices: list[dict]) -> None:
        """Update the active TTS driver and its available voices."""
        self._current_driver_id = driver_id
        self._available_voices = available_voices

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

        current_voice = char.get("voice_id", "")

        self._voice_combo.blockSignals(True)
        self._voice_combo.clear()
        for voice in self._available_voices:
            name = voice.get("name", "")
            desc = voice.get("description", name)
            self._voice_combo.addItem(desc, name)
            if name == current_voice:
                self._voice_combo.setCurrentIndex(self._voice_combo.count() - 1)
        self._voice_combo.blockSignals(False)

        voice_params = char.get("voice_params") or {}
        try:
            if isinstance(voice_params, str):
                voice_params = json.loads(voice_params or "{}")
        except json.JSONDecodeError:
            voice_params = {}

        self._desc_group.setVisible(self._current_driver_id == "mimo")
        self._desc_edit.blockSignals(True)
        self._desc_edit.setPlainText(voice_params.get("voice_description", ""))
        self._desc_edit.blockSignals(False)

    def _on_voice_changed(self) -> None:
        self._emit_voice_change()

    def _on_description_changed(self) -> None:
        self._emit_voice_change()

    def _emit_voice_change(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._characters):
            return
        speaker_name = self._characters[row].get("name", "")
        if not speaker_name:
            return
        voice_id = self._voice_combo.currentData()
        if not voice_id:
            return

        voice_params = None
        if self._current_driver_id == "mimo":
            desc = self._desc_edit.toPlainText().strip()
            if desc:
                voice_params = {"voice_description": desc}

        self.voice_changed.emit(speaker_name, self._current_driver_id, voice_id, voice_params)
