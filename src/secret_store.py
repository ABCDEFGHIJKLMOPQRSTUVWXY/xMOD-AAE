# -*- coding: utf-8 -*-
"""Store LLM/TTS API secrets outside the shared settings table.

Prefers the OS credential store via :mod:`keyring` (e.g. Windows Credential
Manager). If ``keyring`` is unavailable or fails, secrets fall back to a
per-user ``secrets.json`` file in the app data dir so the app never breaks.

The two API keys are the only values routed here; all other settings stay in
the plain settings table.
"""
from __future__ import annotations

import json
import os

from config import get_app_data_dir

try:
    import keyring
except Exception:  # pragma: no cover - keyring is optional
    keyring = None

_SERVICE = "xMOD-AAE"
_SECRET_KEYS = ("mimo_api_key", "llm_api_key")
_SECRET_FILE = "secrets.json"


def is_secret_key(key: str) -> bool:
    """True if ``key`` is one of the API keys routed through the secret store."""
    return key in _SECRET_KEYS


def _secret_path() -> str:
    return os.path.join(get_app_data_dir(), _SECRET_FILE)


def get_secret(key: str, default: str = "") -> str:
    if keyring is not None:
        try:
            value = keyring.get_password(_SERVICE, key)
            if value:
                return value
        except Exception:
            pass
    try:
        with open(_secret_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return str(data.get(key, default))
    except (OSError, json.JSONDecodeError):
        return default


def set_secret(key: str, value: str) -> None:
    value = value or ""
    if keyring is not None:
        try:
            keyring.set_password(_SERVICE, key, value)
            return
        except Exception:
            pass
    path = _secret_path()
    data: dict = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = {}
    data[key] = value
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def clear_secret(key: str) -> None:
    if keyring is not None:
        try:
            keyring.delete_password(_SERVICE, key)
        except Exception:
            pass
    path = _secret_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = {}
    data.pop(key, None)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
