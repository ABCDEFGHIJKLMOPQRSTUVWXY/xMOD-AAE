from __future__ import annotations

import json
import sqlite3
import sys
from typing import TYPE_CHECKING

from secret_store import clear_secret, get_secret, is_secret_key, set_secret

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

    def _ensure_column(self, table: str, column: str, ddl: str):
        """Add a column if it does not exist yet (idempotent migration)."""
        conn = self._connect()
        existing = [
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        ]
        if column not in existing:
            conn.execute(ddl)

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

        # ── 幂等迁移：多引擎支持 ──────────────────────────────────
        # 旧库可能已存在这些表，ALTER TABLE 需按列名守卫避免重复添加。
        self._ensure_column(
            "voice_map", "driver",
            "ALTER TABLE voice_map ADD COLUMN driver TEXT DEFAULT 'edge-tts'",
        )
        self._ensure_column(
            "characters", "driver",
            "ALTER TABLE characters ADD COLUMN driver TEXT DEFAULT 'edge-tts'",
        )
        self._ensure_column(
            "voice_map", "voice_params",
            "ALTER TABLE voice_map ADD COLUMN voice_params TEXT DEFAULT '{}'",
        )
        self._ensure_column(
            "characters", "voice_params",
            "ALTER TABLE characters ADD COLUMN voice_params TEXT DEFAULT '{}'",
        )
        conn.commit()

    def close(self):
        """Close the underlying SQLite connection, if open."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def save_characters(self, book_id: str, profiles: list[CharacterProfile]):
        conn = self._connect()
        try:
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
        except Exception:
            conn.rollback()
            raise

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
                try:
                    d["voice_params"] = json.loads(d.get("voice_params", "{}") or "{}")
                except json.JSONDecodeError:
                    d["voice_params"] = {}
                result.append(d)
            return result
        except Exception as exc:
            print(f"[CharacterStore] get_characters error: {exc}", file=sys.stderr)
            return []

    def update_character_voice(
        self,
        book_id: str,
        speaker_name: str,
        voice_id: str,
        driver: str = "edge-tts",
        voice_params: dict | None = None,
    ):
        try:
            conn = self._connect()
            conn.execute(
                """UPDATE characters
                   SET voice_id = ?, driver = ?, voice_params = ?
                   WHERE book_id = ? AND name = ?""",
                (
                    voice_id,
                    driver,
                    json.dumps(voice_params or {}, ensure_ascii=False),
                    book_id,
                    speaker_name,
                ),
            )
            conn.execute(
                """INSERT OR REPLACE INTO voice_map
                   (book_id, speaker_name, voice_id, driver, voice_params)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    book_id,
                    speaker_name,
                    voice_id,
                    driver,
                    json.dumps(voice_params or {}, ensure_ascii=False),
                ),
            )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            print(f"[CharacterStore] update_character_voice error: {exc}", file=sys.stderr)

    @staticmethod
    def _parse_voice_params(value: str) -> dict:
        try:
            return json.loads(value or "{}")
        except json.JSONDecodeError:
            return {}

    def get_voice_map(self, book_id: str) -> dict[str, dict]:
        """Return the voice map for a book.

        Returns:
            ``{speaker: {"voice_id": str, "driver": str, "voice_params": dict}}``.
            A ``_narrator_`` entry is always present (falling back to settings
            / edge-tts defaults when missing).
        """
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT speaker_name, voice_id, driver, voice_params "
                "FROM voice_map WHERE book_id = ?",
                (book_id,),
            ).fetchall()
            result: dict[str, dict] = {}
            for row in rows:
                result[row["speaker_name"]] = {
                    "voice_id": row["voice_id"],
                    "driver": row["driver"] or "edge-tts",
                    "voice_params": self._parse_voice_params(row["voice_params"]),
                }
            if "_narrator_" not in result:
                narrator = conn.execute(
                    "SELECT value FROM settings WHERE key = ?", ("narrator_voice",)
                ).fetchone()
                narrator_driver = conn.execute(
                    "SELECT value FROM settings WHERE key = ?", ("narrator_driver",)
                ).fetchone()
                narrator_params = conn.execute(
                    "SELECT value FROM settings WHERE key = ?", ("narrator_voice_params",)
                ).fetchone()
                result["_narrator_"] = {
                    "voice_id": (
                        narrator["value"] if narrator and narrator["value"]
                        else "zh-CN-XiaoxiaoNeural"
                    ),
                    "driver": (
                        narrator_driver["value"] if narrator_driver and narrator_driver["value"]
                        else "edge-tts"
                    ),
                    "voice_params": self._parse_voice_params(
                        narrator_params["value"] if narrator_params else "{}"
                    ),
                }
            return result
        except Exception as exc:
            print(f"[CharacterStore] get_voice_map error: {exc}", file=sys.stderr)
            return {
                "_narrator_": {
                    "voice_id": "zh-CN-XiaoxiaoNeural",
                    "driver": "edge-tts",
                    "voice_params": {},
                }
            }

    def save_voice_map(self, book_id: str, voice_map: dict[str, dict | str]):
        """Persist a voice map.

        Args:
            voice_map: ``{speaker: {"voice_id", "driver", "voice_params"}}``.
                A bare ``speaker -> voice_id`` mapping is also accepted for
                backward compatibility.
        """
        try:
            conn = self._connect()
            conn.execute("DELETE FROM voice_map WHERE book_id = ?", (book_id,))
            for speaker_name, entry in voice_map.items():
                if isinstance(entry, dict):
                    voice_id = entry.get("voice_id", "")
                    driver = entry.get("driver", "edge-tts")
                    voice_params = entry.get("voice_params")
                else:
                    voice_id = entry
                    driver = "edge-tts"
                    voice_params = None
                conn.execute(
                    "INSERT INTO voice_map (book_id, speaker_name, voice_id, driver, voice_params) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        book_id,
                        speaker_name,
                        voice_id,
                        driver,
                        json.dumps(voice_params or {}, ensure_ascii=False),
                    ),
                )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            print(f"[CharacterStore] save_voice_map error: {exc}", file=sys.stderr)

    def get_setting(self, key: str, default: str = "") -> str:
        if is_secret_key(key):
            value = get_secret(key, "")
            if value:
                return value
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
        if is_secret_key(key):
            set_secret(key, value)
            try:
                conn = self._connect()
                conn.execute("DELETE FROM settings WHERE key = ?", (key,))
                conn.commit()
            except Exception as exc:
                conn.rollback()
                print(f"[CharacterStore] set_setting error: {exc}", file=sys.stderr)
            return
        try:
            conn = self._connect()
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            print(f"[CharacterStore] set_setting error: {exc}", file=sys.stderr)

    def get_all_settings(self) -> dict[str, str]:
        try:
            conn = self._connect()
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            result = {row["key"]: row["value"] for row in rows}
            for key in ("mimo_api_key", "llm_api_key"):
                if is_secret_key(key):
                    secret = get_secret(key, "")
                    if secret:
                        result[key] = secret
            return result
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
            conn.rollback()
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
            conn.rollback()
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
