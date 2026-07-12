from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QSlider
from PyQt6.QtCore import pyqtSignal, Qt


class ControlBar(QWidget):
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    speed_changed = pyqtSignal(float)
    volume_changed = pyqtSignal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self._btn_prev = QPushButton("\u23ee")
        self._btn_prev.setToolTip("上一句")
        self._btn_prev.setFixedWidth(36)
        self._btn_prev.clicked.connect(self.prev_clicked.emit)

        self._btn_play = QPushButton("\u25b6")
        self._btn_play.setToolTip("播放")
        self._btn_play.setFixedWidth(36)
        self._btn_play.clicked.connect(self._on_play_pause)

        self._btn_stop = QPushButton("\u23f9")
        self._btn_stop.setToolTip("停止")
        self._btn_stop.setFixedWidth(36)
        self._btn_stop.clicked.connect(self.stop_clicked.emit)

        self._btn_next = QPushButton("\u23ed")
        self._btn_next.setToolTip("下一句")
        self._btn_next.setFixedWidth(36)
        self._btn_next.clicked.connect(self.next_clicked.emit)

        layout.addWidget(self._btn_prev)
        layout.addWidget(self._btn_play)
        layout.addWidget(self._btn_stop)
        layout.addWidget(self._btn_next)

        layout.addSpacing(16)

        layout.addWidget(QLabel("速度:"))
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(50, 200)
        self._speed_slider.setValue(100)
        self._speed_slider.setFixedWidth(100)
        self._speed_slider.setToolTip("播放速度 (0.5x - 2.0x) \u2014 仅停止时可调整")
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        layout.addWidget(self._speed_slider)
        self._speed_label = QLabel("1.0x")
        self._speed_label.setFixedWidth(36)
        layout.addWidget(self._speed_label)

        layout.addSpacing(16)

        layout.addWidget(QLabel("音量:"))
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(80)
        self._volume_slider.setFixedWidth(100)
        self._volume_slider.valueChanged.connect(self._on_volume_changed)
        layout.addWidget(self._volume_slider)

        layout.addStretch()

        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet("color: gray;")
        layout.addWidget(self._status_label)

        self._is_playing = False
        self._is_paused = False

    def _on_play_pause(self) -> None:
        if self._is_playing and not self._is_paused:
            self.pause_clicked.emit()
        else:
            self.play_clicked.emit()

    def _on_speed_changed(self, value: int) -> None:
        speed = value / 100.0
        self._speed_label.setText(f"{speed:.1f}x")
        self.speed_changed.emit(speed)

    def _on_volume_changed(self, value: int) -> None:
        vol = value / 100.0
        self.volume_changed.emit(vol)

    def set_state(self, is_playing: bool, is_paused: bool) -> None:
        self._is_playing = is_playing
        self._is_paused = is_paused

        if is_playing and not is_paused:
            self._btn_play.setText("\u23f8")
            self._btn_play.setToolTip("暂停")
            self._speed_slider.setEnabled(False)
        elif is_playing and is_paused:
            self._btn_play.setText("\u25b6")
            self._btn_play.setToolTip("继续")
            self._speed_slider.setEnabled(False)
        else:
            self._btn_play.setText("\u25b6")
            self._btn_play.setToolTip("播放")
            self._speed_slider.setEnabled(True)

    def set_progress(self, chunk_index: int, total_chunks: int) -> None:
        self._status_label.setText(f"第 {chunk_index + 1} 句 / {total_chunks} 句")
