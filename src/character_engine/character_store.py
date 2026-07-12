from __future__ import annotations

import json
import sqlite3
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_analyzer import CharacterProfile


class CharacterStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def init_db(self):
        conn = self._connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                filepath TEXT NOT NULL,
                position TEXT DEFAULT '0,0',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS characters (
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
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS voice_map (
                book_id TEXT NOT NULL,
                speaker_name TEXT NOT NULL,
                voice_id TEXT NOT NULL,
                PRIMARY KEY (book_id, speaker_name),
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT DEFAULT ''
            );
        """)

    def save_characters(self, book_id: str, profiles: list[CharacterProfile]):
        conn = self._connect()
        conn.execute("DELETE FROM characters WHERE book_id = ?", (book_id,))
        for profile in profiles:
            conn.execute(
                """INSERT INTO characters
                   (book_id, name, gender, age_group, personality, role_type,
                    speaking_style, summary, voice_id, profile_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    book_id,
                    profile.name,
                    profile.gender,
                    profile.age_group,
                    json.dumps(profile.personality, ensure_ascii=False),
                    profile.role_type,
                    profile.speaking_style,
                    profile.summary,
                    profile.voice_id,
                    json.dumps(
                        {
                            "name": profile.name,
                            "gender": profile.gender,
                            "age_group": profile.age_group,
                            "personality": profile.personality,
                            "role_type": profile.role_type,
                            "speaking_style": profile.speaking_style,
                            "summary": profile.summary,
                            "voice_id": profile.voice_id,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
        conn.commit()

    def get_characters(self, book_id: str) -> list[dict]:
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT * FROM characters WHERE book_id = ? ORDER BY id",
                (book_id,),
            ).fetchall()
            result: list[dict] = []
            for row in rows:
                d = dict(row)
                try:
                    d["personality"] = json.loads(d.get("personality", "[]") or "[]")
                except json.JSONDecodeError:
                    d["personality"] = []
                result.append(d)
            return result
        except Exception as exc:
            print(f"[CharacterStore] get_characters error: {exc}", file=sys.stderr)
            return []

    def update_character_voice(self, book_id: str, speaker_name: str, voice_id: str):
        try:
            conn = self._connect()
            conn.execute(
                "UPDATE characters SET voice_id = ? WHERE book_id = ? AND name = ?",
                (voice_id, book_id, speaker_name),
            )
            conn.execute(
                """INSERT OR REPLACE INTO voice_map (book_id, speaker_name, voice_id)
                   VALUES (?, ?, ?)""",
                (book_id, speaker_name, voice_id),
            )
            conn.commit()
        except Exception as exc:
            print(f"[CharacterStore] update_character_voice error: {exc}", file=sys.stderr)

    def get_voice_map(self, book_id: str) -> dict[str, str]:
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT speaker_name, voice_id FROM voice_map WHERE book_id = ?",
                (book_id,),
            ).fetchall()
            result: dict[str, str] = {}
            for row in rows:
                result[row["speaker_name"]] = row["voice_id"]
            if "_narrator_" not in result:
                narrator = conn.execute(
                    "SELECT value FROM settings WHERE key = ?", ("narrator_voice",)
                ).fetchone()
                result["_narrator_"] = (
                    narrator["value"] if narrator else "zh-CN-XiaoxiaoNeural"
                )
            return result
        except Exception as exc:
            print(f"[CharacterStore] get_voice_map error: {exc}", file=sys.stderr)
            return {"_narrator_": "zh-CN-XiaoxiaoNeural"}

    def save_voice_map(self, book_id: str, voice_map: dict[str, str]):
        try:
            conn = self._connect()
            conn.execute("DELETE FROM voice_map WHERE book_id = ?", (book_id,))
            for speaker_name, voice_id in voice_map.items():
                conn.execute(
                    "INSERT INTO voice_map (book_id, speaker_name, voice_id) VALUES (?, ?, ?)",
                    (book_id, speaker_name, voice_id),
                )
            conn.commit()
        except Exception as exc:
            print(f"[CharacterStore] save_voice_map error: {exc}", file=sys.stderr)

    def get_setting(self, key: str, default: str = "") -> str:
        try:
            conn = self._connect()
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else default
        except Exception as exc:
            print(f"[CharacterStore] get_setting error: {exc}", file=sys.stderr)
            return default

    def set_setting(self, key: str, value: str):
        try:
            conn = self._connect()
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()
        except Exception as exc:
            print(f"[CharacterStore] set_setting error: {exc}", file=sys.stderr)

    def get_all_settings(self) -> dict[str, str]:
        try:
            conn = self._connect()
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            return {row["key"]: row["value"] for row in rows}
        except Exception as exc:
            print(f"[CharacterStore] get_all_settings error: {exc}", file=sys.stderr)
            return {}

    def add_book(self, book_id: str, title: str, filepath: str) -> bool:
        try:
            conn = self._connect()
            existing = conn.execute(
                "SELECT id FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            if existing:
                return False
            conn.execute(
                "INSERT INTO books (id, title, filepath) VALUES (?, ?, ?)",
                (book_id, title, filepath),
            )
            conn.commit()
            return True
        except Exception as exc:
            print(f"[CharacterStore] add_book error: {exc}", file=sys.stderr)
            return False

    def get_books(self) -> list[dict]:
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT * FROM books ORDER BY created_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]
        except Exception as exc:
            print(f"[CharacterStore] get_books error: {exc}", file=sys.stderr)
            return []

    def get_book(self, book_id: str) -> dict | None:
        try:
            conn = self._connect()
            row = conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            return dict(row) if row else None
        except Exception as exc:
            print(f"[CharacterStore] get_book error: {exc}", file=sys.stderr)
            return None

    def delete_book(self, book_id: str):
        try:
            conn = self._connect()
            conn.execute("DELETE FROM voice_map WHERE book_id = ?", (book_id,))
            conn.execute("DELETE FROM characters WHERE book_id = ?", (book_id,))
            conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            conn.commit()
        except Exception as exc:
            print(f"[CharacterStore] delete_book error: {exc}", file=sys.stderr)

    def update_position(self, book_id: str, chapter: int, chunk: int):
        try:
            conn = self._connect()
            conn.execute(
                "UPDATE books SET position = ? WHERE id = ?",
                (f"{chapter},{chunk}", book_id),
            )
            conn.commit()
        except Exception as exc:
            print(f"[CharacterStore] update_position error: {exc}", file=sys.stderr)

    def get_position(self, book_id: str) -> tuple[int, int]:
        try:
            conn = self._connect()
            row = conn.execute(
                "SELECT position FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            if row and row["position"]:
                parts = row["position"].split(",")
                return (int(parts[0]), int(parts[1])) if len(parts) == 2 else (0, 0)
            return (0, 0)
        except Exception as exc:
            print(f"[CharacterStore] get_position error: {exc}", file=sys.stderr)
            return (0, 0)
