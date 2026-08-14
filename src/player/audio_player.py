import pygame
import pygame.mixer
import time


class AudioPlayer:
    def __init__(self):
        self._current_chunk_index = -1
        self._chunks: list = []
        self._paused = False
        self._stopped = True
        self._volume: float = 1.0

    def set_chunks(self, chunks: list):
        self._chunks = chunks

    def play_chunk(self, chunk_index: int) -> bool:
        if chunk_index < 0 or chunk_index >= len(self._chunks):
            return False

        chunk = self._chunks[chunk_index]

        if not chunk.ready_event.wait(timeout=5.0):
            return False

        if not chunk.mp3_path:
            return False

        try:
            pygame.mixer.music.load(chunk.mp3_path)
            pygame.mixer.music.play()
            self._current_chunk_index = chunk_index
            self._stopped = False
            self._paused = False
            return True
        except pygame.error:
            return False

    def pause(self):
        if not self._stopped and not self._paused:
            pygame.mixer.music.pause()
            self._paused = True

    def unpause(self):
        if self._paused:
            pygame.mixer.music.unpause()
            self._paused = False

    def stop(self):
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        self._stopped = True
        self._paused = False
        self._current_chunk_index = -1

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self._volume)

    @property
    def current_chunk_index(self) -> int:
        return self._current_chunk_index

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def is_stopped(self) -> bool:
        return self._stopped
