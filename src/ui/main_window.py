import os
import sys
import uuid
import shutil
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QMenuBar, QMenu, QMessageBox,
    QFileDialog, QStatusBar, QWidget, QVBoxLayout, QLabel
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from character_engine.character_store import CharacterStore
from tts_engine.cache_manager import CacheManager
from tts_engine.edge_tts_client import synthesize_sync
from tts_engine.voice_registry import get_voices, get_default_narrator_voice
from player.playback_controller import PlaybackController
from ui.bookshelf import BookshelfWidget
from ui.reader_view import ReaderView
from ui.character_panel import CharacterPanel
from ui.control_bar import ControlBar
from ui.settings_dialog import SettingsDialog
from ui.chapter_list import ChapterListWidget


def get_app_data_dir() -> str:
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    path = os.path.join(appdata, "xMOD-AAE")
    os.makedirs(path, exist_ok=True)
    return path


def get_books_dir() -> str:
    path = os.path.join(get_app_data_dir(), "books")
    os.makedirs(path, exist_ok=True)
    return path


def get_cache_dir() -> str:
    path = os.path.join(get_app_data_dir(), "cache")
    os.makedirs(path, exist_ok=True)
    return path


def get_db_path() -> str:
    return os.path.join(get_app_data_dir(), "store.db")


class CharacterAnalysisWorker(QThread):
    finished = pyqtSignal(list, list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int, str)

    def __init__(
        self,
        analyzer,
        paragraph_batches: list,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._analyzer = analyzer
        self._paragraph_batches = paragraph_batches

    def run(self) -> None:
        try:
            segments_with_speakers = self._analyzer.identify_speakers(
                self._paragraph_batches,
                progress_callback=lambda cur, total, msg: self.progress.emit(cur, total, msg),
            )
            from character_engine.aggregator import collect
            speaker_infos = collect(segments_with_speakers)
            profiles = self._analyzer.analyze_characters(
                speaker_infos,
                progress_callback=lambda cur, total, msg: self.progress.emit(cur, total, msg),
            )
            self.finished.emit(profiles, segments_with_speakers)
        except Exception as e:
            import traceback
            traceback.print_exc(file=sys.stderr)
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("xMOD-AAE — 有声书阅读器")
        self.resize(1200, 800)

        self._store = CharacterStore(get_db_path())
        self._store.init_db()
        self._cache_manager = CacheManager(get_cache_dir())
        self._available_voices: list[dict] = get_voices()

        self._controller = PlaybackController()
        self._controller.configure(self._cache_manager, synthesize_sync)

        self._current_book_id: str = ""
        self._chapters: list[tuple[str, str]] = []
        self._current_chapter_index: int = 0
        self._chapter_texts: list[str] = []
        self._dialogue_segments_cache: dict[int, list] = {}
        self._voice_map: dict[str, str] = {"_narrator_": get_default_narrator_voice()}

        self._build_menu_bar()
        self._build_central_layout()
        self._build_status_bar()
        self._connect_signals()

        self._show_bookshelf()

    def _build_menu_bar(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")
        file_menu.addAction("导入书籍(&I)...", self._import_book)
        file_menu.addAction("返回书架(&B)", self._show_bookshelf)
        file_menu.addSeparator()
        file_menu.addAction("退出(&X)", self.close)

        char_menu = menubar.addMenu("角色(&C)")
        char_menu.addAction("分析角色(&A)", self._analyze_characters)

        settings_menu = menubar.addMenu("设置(&S)")
        settings_menu.addAction("偏好设置(&P)...", self._show_settings)

    def _build_central_layout(self) -> None:
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        self._chapter_list = ChapterListWidget()
        self._reader_view = ReaderView()
        self._character_panel = CharacterPanel(self._available_voices)

        self._splitter.addWidget(self._chapter_list)
        self._splitter.addWidget(self._reader_view)
        self._splitter.addWidget(self._character_panel)

        self._splitter.setSizes([180, 680, 280])

        self._bookshelf = BookshelfWidget()

        self._control_bar = ControlBar()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._splitter, 1)
        layout.addWidget(self._bookshelf, 1)
        layout.addWidget(self._control_bar)
        self.setCentralWidget(central)

        self._splitter.hide()

    def _build_status_bar(self) -> None:
        self._status_bar = self.statusBar()
        self._status_label = QLabel("就绪")
        self._status_bar.addWidget(self._status_label)

    def _connect_signals(self) -> None:
        self._bookshelf.book_selected.connect(self._open_book)

        self._chapter_list.chapter_clicked.connect(self._on_chapter_clicked)
        self._chapter_list.chapter_double_clicked.connect(self._on_chapter_double_clicked)

        self._character_panel.voice_changed.connect(self._on_character_voice_changed)

        self._controller.chunk_changed.connect(self._reader_view.highlight_chunk)
        self._controller.state_changed.connect(self._control_bar.set_state)
        self._controller.chapter_changed.connect(self._on_controller_chapter_changed)
        self._controller.progress_updated.connect(self._control_bar.set_progress)
        self._controller.playback_finished.connect(self._on_playback_finished)

        self._control_bar.play_clicked.connect(self._on_play)
        self._control_bar.pause_clicked.connect(self._on_pause)
        self._control_bar.stop_clicked.connect(self._on_stop)
        self._control_bar.prev_clicked.connect(self._controller.prev_chunk)
        self._control_bar.next_clicked.connect(self._controller.next_chunk)
        self._control_bar.speed_changed.connect(self._controller.set_speed)
        self._control_bar.volume_changed.connect(self._controller.set_volume)

    def _show_bookshelf(self) -> None:
        self._splitter.hide()
        self._bookshelf.show()
        self._control_bar.hide()
        self._status_label.setText("就绪")
        self._bookshelf.refresh()

    def _import_book(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "导入书籍", "", "文本文件 (*.txt);;所有文件 (*)"
        )
        if not path:
            return

        book_id = str(uuid.uuid4())
        title = os.path.splitext(os.path.basename(path))[0]
        dest = os.path.join(get_books_dir(), f"{book_id}.txt")

        try:
            shutil.copy2(path, dest)
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"无法复制文件：{e}")
            return

        if not self._store.add_book(book_id, title, dest):
            QMessageBox.critical(self, "导入失败", "书籍已存在")
            return

        self._status_label.setText(f"已导入：{title}")
        self._bookshelf.refresh()

    def _open_book(self, book_id: str) -> None:
        book = self._store.get_book(book_id)
        if not book:
            return

        self._current_book_id = book_id
        filepath = book["filepath"]

        if not os.path.exists(filepath):
            QMessageBox.critical(self, "错误", "书籍文件已丢失")
            return

        try:
            from text_processor.encoding import load
            text = load(filepath)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载文件：{e}")
            return

        from text_processor.chapter import split as split_chapters
        self._chapters = split_chapters(text)
        if not self._chapters:
            QMessageBox.warning(self, "提示", "无法识别章节结构，将作为单章处理")
            self._chapters = [("全文", text)]

        from text_processor.paragraph import split as split_paragraphs
        from text_processor.dialogue import extract_spans

        self._chapter_texts = []
        self._dialogue_segments_cache = {}

        for ch_idx, (title, content) in enumerate(self._chapters):
            self._chapter_texts.append(content)
            paragraphs = split_paragraphs(content)
            para_dialogue_segments = []
            for para in paragraphs:
                segs = extract_spans(para)
                para_dialogue_segments.append(segs)
            self._dialogue_segments_cache[ch_idx] = para_dialogue_segments

        db_voice_map = self._store.get_voice_map(book_id)
        if len(db_voice_map) <= 1:
            default_narrator = get_default_narrator_voice()
            self._voice_map = {"_narrator_": default_narrator}
        else:
            self._voice_map = db_voice_map

        self._bookshelf.hide()
        self._splitter.show()
        self._control_bar.show()

        chapter_titles = [t for t, _ in self._chapters]
        self._chapter_list.set_chapters(chapter_titles)

        ch_idx, _ = self._store.get_position(book_id)
        self._load_chapter(min(ch_idx, len(self._chapters) - 1) if self._chapters else 0)

        characters = self._store.get_characters(book_id)
        self._character_panel.set_characters(characters)

        self._status_label.setText(f"已打开：{book['title']}")

    def _load_chapter(self, chapter_index: int) -> None:
        if not self._chapters or chapter_index >= len(self._chapters):
            return

        self._current_chapter_index = chapter_index
        title, content = self._chapters[chapter_index]
        self._reader_view.set_text(content)
        self._chapter_list.set_current(chapter_index)

        self._store.update_position(self._current_book_id, chapter_index, 0)

    def _on_chapter_clicked(self, index: int) -> None:
        self._controller.stop()
        self._load_chapter(index)

    def _on_chapter_double_clicked(self, index: int) -> None:
        self._load_chapter(index)
        self._start_chapter_playback(index)

    def _on_controller_chapter_changed(self, chapter_index: int, total: int) -> None:
        pass

    def _start_chapter_playback(self, chapter_index: int) -> None:
        if chapter_index >= len(self._chapter_texts):
            return

        chapter_text = self._chapter_texts[chapter_index]
        para_segments = self._dialogue_segments_cache.get(chapter_index, [])

        self._controller.load_chapter(
            chapter_index, chapter_text, self._voice_map,
            para_segments, len(self._chapters)
        )
        self._controller.play()

    def _on_play(self) -> None:
        if not self._chapters:
            return
        if self._controller.is_paused:
            self._controller.play()
        else:
            self._start_chapter_playback(self._current_chapter_index)

    def _on_pause(self) -> None:
        if self._controller.is_playing and not self._controller.is_paused:
            self._controller.pause()

    def _on_stop(self) -> None:
        self._controller.stop()

    def _on_playback_finished(self) -> None:
        title = self._chapters[self._current_chapter_index][0]
        self._status_label.setText(f"播放完成 - {title}")

    def _analyze_characters(self) -> None:
        if not self._current_book_id:
            self._status_label.setText("请先打开一本书")
            return

        settings = self._store.get_all_settings()
        from character_engine.llm_analyzer import LLMAnalyzer
        analyzer = LLMAnalyzer(settings)

        batches = self._build_speaker_id_batches()

        if not batches:
            self._status_label.setText("未检测到对话内容")
            return

        self._status_label.setText("正在探测 LLM 服务...")
        self._analysis_worker = CharacterAnalysisWorker(
            analyzer, batches
        )
        self._analysis_worker.progress.connect(self._on_analysis_progress)
        self._analysis_worker.finished.connect(self._on_analysis_finished)
        self._analysis_worker.error.connect(self._on_analysis_error)
        self._analysis_worker.start()

    def _on_analysis_progress(self, current: int, total: int, message: str) -> None:
        if total > 0:
            self._status_label.setText(f"[{current}/{total}] {message}")
        else:
            self._status_label.setText(message)

    def _on_analysis_finished(self, profiles: list, segments_with_speakers: list) -> None:
        from character_engine.voice_mapper import assign_voice

        used_voices: set[str] = set()

        for profile in profiles:
            voice_id = assign_voice(profile, self._available_voices, used_voices)
            profile.voice_id = voice_id
            used_voices.add(voice_id)

        self._store.save_characters(self._current_book_id, profiles)

        narrator_voice = self._voice_map.get("_narrator_", get_default_narrator_voice())
        self._voice_map = {"_narrator_": narrator_voice}
        for profile in profiles:
            self._voice_map[profile.name] = profile.voice_id
        self._store.save_voice_map(self._current_book_id, self._voice_map)

        characters = self._store.get_characters(self._current_book_id)
        self._character_panel.set_characters(characters)

        self._status_label.setText(f"角色分析完成：{len(profiles)} 个角色")

    def _on_analysis_error(self, error: str) -> None:
        self._status_label.setText(f"角色分析失败：{error}")
        QMessageBox.warning(
            self, "分析失败",
            f"角色分析失败：\n\n{error}\n\n"
            "请确认：\n"
            "1. Ollama 已安装并运行中\n"
            "2. 已通过 'ollama pull qwen2.5:7b' 下载模型\n"
            "3. 或在 设置 → LLM 模型 中切换到云端 API"
        )

    def _build_speaker_id_batches(self, batch_size: int = 5) -> list[list[tuple[str, list]]]:
        batches: list[list[tuple[str, list]]] = []
        current_batch: list[tuple[str, list]] = []

        for ch_idx in range(len(self._chapters)):
            para_segments = self._dialogue_segments_cache.get(ch_idx, [])
            for segs in para_segments:
                dialogue_spans = [s for s in segs if s.is_dialogue]
                if not dialogue_spans:
                    continue
                para_text = "".join(s.text for s in segs)
                current_batch.append((para_text, dialogue_spans))
                if len(current_batch) >= batch_size:
                    batches.append(current_batch)
                    current_batch = []

        if current_batch:
            batches.append(current_batch)

        return batches

    def _on_character_voice_changed(self, speaker_name: str, voice_id: str) -> None:
        self._voice_map[speaker_name] = voice_id
        self._store.update_character_voice(self._current_book_id, speaker_name, voice_id)

        if self._controller.is_playing:
            self._controller.stop()
        if self._chapters:
            self._status_label.setText(f"已更新 {speaker_name} 的语音，下次播放时生效")

    def _show_settings(self) -> None:
        dialog = SettingsDialog(self._store, self._available_voices, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._status_label.setText("设置已保存")

    def closeEvent(self, event) -> None:
        self._controller.stop()
        if self._current_book_id:
            self._store.update_position(
                self._current_book_id,
                self._current_chapter_index,
                self._controller.chunk_index
            )
        super().closeEvent(event)
