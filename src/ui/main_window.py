import os
import sys
import uuid
import shutil
import json
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QMenuBar, QMenu, QMessageBox,
    QFileDialog, QStatusBar, QWidget, QVBoxLayout, QLabel
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from config import get_app_data_dir, get_books_dir, get_cache_dir, get_db_path
from character_engine.character_store import CharacterStore
from tts_engine.cache_manager import CacheManager
from tts_engine.drivers import create_driver_manager
from tts_engine.voice_registry import get_default_narrator_voice
from player.playback_controller import PlaybackController
from ui.bookshelf import BookshelfWidget
from ui.reader_view import ReaderView
from ui.character_panel import CharacterPanel
from ui.control_bar import ControlBar
from ui.settings_dialog import SettingsDialog
from ui.chapter_list import ChapterListWidget


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
            from character_engine.speaker_normalizer import normalize_speakers
            normalize_speakers(segments_with_speakers)
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

        self._driver_manager = create_driver_manager(
            get_settings=self._store.get_setting,
            set_settings=self._store.set_setting,
        )
        self._current_driver = self._driver_manager.get_current_driver()

        self._cache_manager = CacheManager(get_cache_dir())
        self._available_voices: list[dict] = self._current_driver.get_voices()

        self._controller = PlaybackController()
        self._controller.configure(
            self._cache_manager, self._driver_manager, self._current_driver.id
        )

        self._current_book_id: str = ""
        self._chapters: list[tuple[str, str]] = []
        self._current_chapter_index: int = 0
        self._chapter_texts: list[str] = []
        self._dialogue_segments_cache: dict[int, list] = {}
        self._original_paragraphs_cache: dict[int, list[str]] = {}
        self._voice_map: dict[str, str] = {"_narrator_": get_default_narrator_voice()}
        self._voice_meta: dict[str, dict] = {
            "_narrator_": {"driver": self._current_driver.id, "voice_params": None}
        }

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

        view_menu = menubar.addMenu("视图(&V)")
        self._toggle_segments_action = view_menu.addAction("显示分段结构(&S)")
        self._toggle_segments_action.setCheckable(True)
        self._toggle_segments_action.setChecked(True)
        self._toggle_segments_action.triggered.connect(self._on_toggle_segments)

        settings_menu = menubar.addMenu("设置(&S)")
        settings_menu.addAction("偏好设置(&P)...", self._show_settings)

    def _build_central_layout(self) -> None:
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        self._chapter_list = ChapterListWidget()
        self._reader_view = ReaderView()
        self._character_panel = CharacterPanel(
            self._available_voices, current_driver_id=self._current_driver.id
        )

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

        import re
        from text_processor.dialogue import extract_spans

        _PARA_SPLIT_RE = re.compile(r"\n\s*\n")

        self._chapter_texts = []
        self._dialogue_segments_cache = {}
        self._original_paragraphs_cache = {}

        for ch_idx, (title, content) in enumerate(self._chapters):
            self._chapter_texts.append(content)
            raw_paragraphs = _PARA_SPLIT_RE.split(content)
            original_paras = []
            para_dialogue_segments = []
            for raw_p in raw_paragraphs:
                stripped = raw_p.strip()
                if len(stripped) >= 5:
                    original_paras.append(raw_p)
                    segs = extract_spans(stripped)
                    para_dialogue_segments.append(segs)
            self._original_paragraphs_cache[ch_idx] = original_paras
            self._dialogue_segments_cache[ch_idx] = para_dialogue_segments

        db_voice_map = self._store.get_voice_map(book_id)
        narrator_driver, narrator_voice, narrator_params = self._get_narrator_default()
        self._voice_map = {"_narrator_": narrator_voice}
        self._voice_meta = {
            "_narrator_": {"driver": narrator_driver, "voice_params": narrator_params}
        }
        for speaker, entry in db_voice_map.items():
            if speaker == "_narrator_":
                continue
            self._voice_map[speaker] = entry["voice_id"]
            self._voice_meta[speaker] = {
                "driver": entry["driver"],
                "voice_params": entry.get("voice_params") or None,
            }

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

        # ── 从结构化分段重建展示文本 + 全局偏移量 ──────────────
        para_segments = self._dialogue_segments_cache.get(chapter_index, [])
        display_text, global_segments = self._build_display_from_segments(para_segments)

        self._reader_view.set_text(display_text)
        self._reader_view.set_segments(global_segments)
        self._chapter_list.set_current(chapter_index)

        self._store.update_position(self._current_book_id, chapter_index, 0)

    @staticmethod
    def _build_display_from_segments(
        para_segments: list[list],
    ) -> tuple[str, list[tuple[int, int, bool]]]:
        """从对话分段列表重建展示文本和全局分段偏移量。

        将每段中所有 DialogueSegment.text 直接拼接，以保证偏移量与
        segment_builder.build() 使用的 char_offset 完全一致。
        段落之间用 \\n 连接，偏移量正确计入分隔符。
        """
        display_parts: list[str] = []
        global_segments: list[tuple[int, int, bool]] = []
        pos = 0

        for para_segs in para_segments:
            for seg in para_segs:
                global_segments.append((pos + seg.start, pos + seg.end, seg.is_dialogue))
            para_text = "".join(s.text for s in para_segs)
            display_parts.append(para_text)
            pos += len(para_text) + 1  # +1 为段落间的 \\n 分隔符

        display_text = "\n".join(display_parts) if display_parts else ""
        return display_text, global_segments

    def _get_narrator_default(self) -> tuple[str, str, dict | None]:
        """Resolve the default narrator voice from settings + current driver.

        Returns:
            ``(driver_id, voice_id, voice_params)``.
        """
        driver_id = self._store.get_setting("narrator_driver", "")
        driver = self._driver_manager.get_driver(driver_id)
        if driver is None:
            driver = self._current_driver
        voice = self._store.get_setting("narrator_voice", "")
        if not any(v.get("name") == voice for v in driver.get_voices()):
            voice = driver.get_default_narrator_voice()
        try:
            params = json.loads(self._store.get_setting("narrator_voice_params", "{}") or "{}")
        except json.JSONDecodeError:
            params = {}
        return driver.id, voice, params or None

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
            para_segments, len(self._chapters),
            voice_meta=self._voice_meta
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

        current_driver = self._driver_manager.get_current_driver()

        used_voices: set[str] = set()
        voice_meta: dict[str, dict] = {}

        for profile in profiles:
            driver, voice_id, voice_params = assign_voice(
                profile, current_driver.get_voices(), used_voices,
                driver_id=current_driver.id,
            )
            profile.voice_id = voice_id
            used_voices.add(voice_id)
            voice_meta[profile.name] = {
                "driver": driver, "voice_id": voice_id, "voice_params": voice_params,
            }

        self._store.save_characters(self._current_book_id, profiles)
        for name, meta in voice_meta.items():
            self._store.update_character_voice(
                self._current_book_id, name, meta["voice_id"],
                meta["driver"], meta["voice_params"],
            )

        narrator_driver, narrator_voice, narrator_params = self._get_narrator_default()
        current_narrator_meta = self._voice_meta.get("_narrator_") or {}
        if current_narrator_meta.get("driver"):
            narrator_driver = current_narrator_meta["driver"]
            narrator_voice = self._voice_map.get("_narrator_", narrator_voice)
            narrator_params = current_narrator_meta.get("voice_params") or narrator_params

        self._voice_map = {"_narrator_": narrator_voice}
        self._voice_meta = {
            "_narrator_": {"driver": narrator_driver, "voice_params": narrator_params}
        }
        for profile in profiles:
            self._voice_map[profile.name] = profile.voice_id
            self._voice_meta[profile.name] = voice_meta[profile.name]

        structured_map = {
            speaker: {
                "voice_id": voice_id,
                "driver": self._voice_meta[speaker]["driver"],
                "voice_params": self._voice_meta[speaker]["voice_params"],
            }
            for speaker, voice_id in self._voice_map.items()
        }
        self._store.save_voice_map(self._current_book_id, structured_map)

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

    def _build_speaker_id_batches(
        self, batch_size: int = 5, max_chars: int = 6000
    ) -> list[list[tuple[str, list, int]]]:
        """按段落数且累计字符数分批，避免单批过大导致云端超时。"""
        batches: list[list[tuple[str, list, int]]] = []
        current_batch: list[tuple[str, list, int]] = []
        current_chars = 0

        for ch_idx in range(len(self._chapters)):
            para_segments = self._dialogue_segments_cache.get(ch_idx, [])
            original_paras = self._original_paragraphs_cache.get(ch_idx, [])

            for segs, original_para in zip(para_segments, original_paras):
                dialogue_spans = [s for s in segs if s.is_dialogue]
                if not dialogue_spans:
                    continue
                stripped_text = "".join(s.text for s in segs)
                base_offset = original_para.find(stripped_text)
                if base_offset < 0:
                    base_offset = 0

                para_chars = len(original_para)
                if current_batch and (
                    len(current_batch) >= batch_size
                    or current_chars + para_chars > max_chars
                ):
                    batches.append(current_batch)
                    current_batch = []
                    current_chars = 0

                current_batch.append((original_para, dialogue_spans, base_offset))
                current_chars += para_chars

        if current_batch:
            batches.append(current_batch)

        return batches

    def _on_character_voice_changed(
        self,
        speaker_name: str,
        driver: str,
        voice_id: str,
        voice_params: dict | None = None,
    ) -> None:
        self._voice_map[speaker_name] = voice_id
        self._voice_meta[speaker_name] = {"driver": driver, "voice_params": voice_params}
        self._store.update_character_voice(
            self._current_book_id, speaker_name, voice_id, driver, voice_params
        )

        if self._controller.is_playing:
            self._controller.stop()
        if self._chapters:
            self._status_label.setText(f"已更新 {speaker_name} 的语音，下次播放时生效")

    def _show_settings(self) -> None:
        dialog = SettingsDialog(self._store, self._driver_manager, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._apply_driver_switch()
            self._status_label.setText("设置已保存")

    def _apply_driver_switch(self) -> None:
        """Apply a possibly-changed TTS engine after settings are saved."""
        new_driver = self._driver_manager.get_current_driver()
        self._current_driver = new_driver
        self._available_voices = new_driver.get_voices()
        self._character_panel.set_driver(new_driver.id, self._available_voices)
        self._controller.stop()
        self._controller.configure(
            self._cache_manager, self._driver_manager, new_driver.id
        )

    def _on_toggle_segments(self, checked: bool) -> None:
        """切换分段结构叠加的显示/隐藏。"""
        self._reader_view.set_show_segments(checked)
        state = "显示" if checked else "隐藏"
        self._status_label.setText(f"分段结构：{state}")

    def closeEvent(self, event) -> None:
        self._controller.stop()
        if self._current_book_id:
            self._store.update_position(
                self._current_book_id,
                self._current_chapter_index,
                self._controller.chunk_index
            )
        super().closeEvent(event)
