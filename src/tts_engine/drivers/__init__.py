from __future__ import annotations

from typing import Callable

from tts_engine.drivers.base import TTSDriver
from tts_engine.drivers.manager import DEFAULT_DRIVER_ID, DriverManager
from tts_engine.drivers.edge_tts_driver import EdgeTTSDriver
from tts_engine.drivers.mimo_driver import MiMoTTSDriver

__all__ = [
    "TTSDriver",
    "DriverManager",
    "DEFAULT_DRIVER_ID",
    "EdgeTTSDriver",
    "MiMoTTSDriver",
    "create_driver_manager",
]


def create_driver_manager(
    get_settings: Callable[[str, str], str] | None = None,
    set_settings: Callable[[str, str], None] | None = None,
) -> DriverManager:
    """Build a DriverManager with all built-in drivers registered."""
    manager = DriverManager(
        get_settings=get_settings,
        set_settings=set_settings,
    )
    manager.register(EdgeTTSDriver(get_settings=get_settings))
    manager.register(MiMoTTSDriver(get_settings=get_settings))
    return manager
