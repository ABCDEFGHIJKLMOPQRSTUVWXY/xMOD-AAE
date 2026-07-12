import pygame
import pygame.mixer
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from player.audio_player import AudioPlayer
from player.chunk_queue import ChunkQueue
from tts_engine.segment_builder import ChunkInfo

# Custom event type for pygame music end (pygame.MUSIC_DONE removed in pygame 2.x)
_MUSIC_END_EVENT = pygame.USEREVENT + 1


class PlaybackController(QObject):
    chunk_changed = pyqtSignal(int, int)
    state_changed = pyqtSignal(bool, bool)
    chapter_changed = pyqtSignal(int, int)
    progress_updated = pyqtSignal(int, int)
    playback_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.book_id: str = ""
        self.chapter_index: int = 0
        self.chunk_index: int = 0
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.speed: float = 1.0
        self.volume: float = 0.8
        self.chunks: list[ChunkInfo] = []
        self.voice_map: dict[str, str] = {}
        self._total_chapters: int = 0

        self._audio_player = AudioPlayer()
        self._chunk_queue = ChunkQueue()
        self._cache_manager = None
        self._synthesize_fn = None

        pygame.mixer.music.set_endevent(_MUSIC_END_EVENT)

        self._pygame_timer = QTimer(self)
        self._pygame_timer.timeout.connect(self._poll_pygame_events)
        self._pygame_timer.setInterval(100)

        self._chunk_queue.chunk_ready.connect(self._on_chunk_ready)

    def configure(self, cache_manager, synthesize_fn):
        self._cache_manager = cache_manager
        self._synthesize_fn = synthesize_fn

    def load_chapter(self, chapter_index: int, chapter_text: str,
                     voice_map: dict[str, str], paragraph_dialogue_segments: list,
                     total_chapters: int = 1):
        self.stop()
        self.chapter_index = chapter_index
        self.voice_map = voice_map
        self._total_chapters = total_chapters
        self.chunks = []

        from tts_engine.segment_builder import build
        char_offset = 0
        for para_segments in paragraph_dialogue_segments:
            para_chunks = build(para_segments, voice_map, char_offset)
            self.chunks.extend(para_chunks)
            if para_chunks:
                char_offset = para_chunks[-1].char_end

        self.chunk_index = 0
        self.chapter_changed.emit(chapter_index, total_chapters)

    def play(self):
        if not self.chunks:
            return

        if self.is_paused:
            self._audio_player.unpause()
            self.is_paused = False
            self.is_playing = True
            self._pygame_timer.start()
            self.state_changed.emit(True, False)
            return

        self.is_playing = True
        self.is_paused = False

        self._start_playback(self.chunk_index)

    def pause(self):
        if self.is_playing and not self.is_paused:
            self._audio_player.pause()
            self.is_paused = True
            self._pygame_timer.stop()
            self.state_changed.emit(True, True)

    def stop(self):
        self._pygame_timer.stop()
        self._chunk_queue.cancel()
        self._audio_player.stop()
        self.is_playing = False
        self.is_paused = False
        self.state_changed.emit(False, False)

    def next_chunk(self):
        if self.chunk_index + 1 < len(self.chunks):
            self.stop()
            self.chunk_index += 1
            self._start_playback(self.chunk_index)

    def prev_chunk(self):
        if self.chunk_index > 0:
            self.stop()
            self.chunk_index -= 1
            self._start_playback(self.chunk_index)

    def seek_to_chunk(self, chunk_index: int):
        if 0 <= chunk_index < len(self.chunks):
            self.stop()
            self.chunk_index = chunk_index
            self._start_playback(chunk_index)

    def set_speed(self, speed: float):
        if not self.is_playing:
            self.speed = speed

    def set_volume(self, volume: float):
        self.volume = volume
        self._audio_player.set_volume(volume)

    def _start_playback(self, chunk_index: int):
        self._audio_player.set_chunks(self.chunks)

        self._chunk_queue.configure(
            self.chunks, chunk_index, self.speed,
            self._cache_manager, self._synthesize_fn
        )
        self._chunk_queue.start()

        self._audio_player.play_chunk(chunk_index)
        self.chunk_index = chunk_index

        if chunk_index < len(self.chunks):
            chunk = self.chunks[chunk_index]
            self.chunk_changed.emit(chunk.char_start, chunk.char_end)
        self.progress_updated.emit(chunk_index, len(self.chunks))
        self.state_changed.emit(True, False)

        self._pygame_timer.start()

    def _poll_pygame_events(self):
        for event in pygame.event.get():
            if event.type == _MUSIC_END_EVENT:
                self._on_music_finished()

    def _on_music_finished(self):
        if not self.is_playing or self.is_paused:
            return

        next_index = self.chunk_index + 1
        if next_index >= len(self.chunks):
            self._on_playback_complete()
            return

        self._audio_player.play_chunk(next_index)
        self.chunk_index = next_index

        chunk = self.chunks[next_index]
        self.chunk_changed.emit(chunk.char_start, chunk.char_end)
        self.progress_updated.emit(next_index, len(self.chunks))

    def _on_playback_complete(self):
        self.stop()
        self.playback_finished.emit()

    def _on_chunk_ready(self, chunk_index: int):
        pass
