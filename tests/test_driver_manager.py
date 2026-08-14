# -*- coding: utf-8 -*-
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tts_engine.drivers.base import TTSDriver
from tts_engine.drivers.manager import DEFAULT_DRIVER_ID, DriverManager
from character_engine.character_store import CharacterStore


class FakeDriver(TTSDriver):
    id = "fake"
    display_name = "Fake Driver"
    output_format = "mp3"
    requires_api_key = False

    def __init__(self, voices=None, get_settings=None):
        super().__init__(get_settings=get_settings)
        self._voices = voices or [{"name": "fake-1", "locale": "zh-CN"}]
        self.synthesize_calls = []

    def get_voices(self):
        return list(self._voices)

    def get_default_narrator_voice(self):
        return self._voices[0]["name"]

    def synthesize(self, text, voice, output_path, voice_params=None, retries=3):
        self.synthesize_calls.append((text, voice, voice_params))
        with open(output_path, "wb") as f:
            f.write(b"data")
        return True


class FakeStore:
    def __init__(self):
        self.data: dict[str, str] = {}

    def get_setting(self, key, default=""):
        return self.data.get(key, default)

    def set_setting(self, key, value):
        self.data[key] = value


class TestDriverManager:
    def test_register_and_query(self):
        mgr = DriverManager()
        mgr.register(FakeDriver())
        assert mgr.get_driver("fake") is not None
        assert mgr.get_driver("missing") is None
        assert [d.id for d in mgr.list_drivers()] == ["fake"]

    def test_get_current_driver_defaults_to_edge(self):
        mgr = DriverManager()
        mgr.register(FakeDriver())
        edge = FakeDriver()
        edge.id = "edge-tts"
        mgr.register(edge)
        assert mgr.get_current_driver().id == "edge-tts"

    def test_get_current_driver_reads_settings(self):
        store = FakeStore()
        store.data["tts_driver"] = "fake"
        mgr = DriverManager(get_settings=store.get_setting, set_settings=store.set_setting)
        mgr.register(FakeDriver())
        mgr.register(FakeDriver(voices=[{"name": "e", "locale": "zh-CN"}]))
        assert mgr.get_current_driver().id == "fake"

    def test_set_current_driver_persists_to_settings(self):
        store = FakeStore()
        mgr = DriverManager(get_settings=store.get_setting, set_settings=store.set_setting)
        mgr.register(FakeDriver())
        mgr.register(FakeDriver(voices=[{"name": "e", "locale": "zh-CN"}]))
        assert mgr.set_current_driver("fake") is True
        assert store.data["tts_driver"] == "fake"
        assert mgr.get_current_driver().id == "fake"

    def test_set_current_driver_rejects_unknown(self):
        mgr = DriverManager()
        mgr.register(FakeDriver())
        assert mgr.set_current_driver("nope") is False

    def test_driver_synthesize_receives_voice_params(self, tmp_path):
        driver = FakeDriver()
        mgr = DriverManager(get_settings=lambda k, d="": "fake")
        mgr.register(driver)
        mgr.set_current_driver("fake")
        params = {"voice_description": "test"}
        output = str(tmp_path / "out.mp3")
        ok = driver.synthesize("你好", "fake-1", output, voice_params=params)
        assert ok
        assert os.path.exists(output)
        assert driver.synthesize_calls[-1][2] == params


def _create_old_schema(db_path: str):
    """Create a store.db matching the pre-migration schema (no driver columns)."""
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            filepath TEXT NOT NULL,
            position TEXT DEFAULT '0,0',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT NOT NULL,
            name TEXT NOT NULL,
            gender TEXT DEFAULT '未知',
            age_group TEXT DEFAULT '未知',
            personality TEXT DEFAULT '[]',
            role_type TEXT DEFAULT '未知',
            speaking_style TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            voice_id TEXT DEFAULT '',
            profile_json TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE voice_map (
            book_id TEXT NOT NULL,
            speaker_name TEXT NOT NULL,
            voice_id TEXT NOT NULL,
            PRIMARY KEY (book_id, speaker_name)
        );
        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        );
        INSERT INTO books (id, title, filepath) VALUES ('b1', '旧书', '/tmp/b1.txt');
        INSERT INTO voice_map (book_id, speaker_name, voice_id)
            VALUES ('b1', '张三', 'zh-CN-YunxiNeural');
    """)
    conn.commit()
    conn.close()


class TestLegacyDataCompatibility:
    def test_migration_adds_driver_default_and_old_rows_stay_edge(self, tmp_path):
        db_path = str(tmp_path / "store.db")
        _create_old_schema(db_path)

        store = CharacterStore(db_path)
        store.init_db()

        voice_map = store.get_voice_map("b1")
        assert "张三" in voice_map
        entry = voice_map["张三"]
        assert entry["voice_id"] == "zh-CN-YunxiNeural"
        assert entry["driver"] == "edge-tts"
        assert entry["voice_params"] == {}
        store.close()

    def test_init_db_is_idempotent(self, tmp_path):
        db_path = str(tmp_path / "store.db")
        store = CharacterStore(db_path)
        store.init_db()
        store.init_db()
        store.close()

        conn = sqlite3.connect(db_path)
        voice_map_cols = [r[1] for r in conn.execute("PRAGMA table_info(voice_map)").fetchall()]
        char_cols = [r[1] for r in conn.execute("PRAGMA table_info(characters)").fetchall()]
        conn.close()
        assert "driver" in voice_map_cols
        assert "voice_params" in voice_map_cols
        assert "driver" in char_cols
        assert "voice_params" in char_cols

    def test_default_driver_constant_is_edge_tts(self):
        assert DEFAULT_DRIVER_ID == "edge-tts"