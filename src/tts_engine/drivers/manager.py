from __future__ import annotations

from typing import Callable

from tts_engine.drivers.base import TTSDriver

DEFAULT_DRIVER_ID = "edge-tts"
_SETTINGS_KEY = "tts_driver"


class DriverManager:
    """Registry of TTS drivers.

    The current driver id is persisted in the settings table under the
    ``tts_driver`` key (default ``edge-tts``).
    """

    def __init__(
        self,
        get_settings: Callable[[str, str], str] | None = None,
        set_settings: Callable[[str, str], None] | None = None,
    ) -> None:
        """Initialize the manager.

        Args:
            get_settings: Optional callable ``(key, default) -> str`` reading a
                setting value. Used to resolve the current driver id.
            set_settings: Optional callable ``(key, value) -> None`` persisting
                a setting. Used by :meth:`set_current_driver`.
        """
        self._drivers: dict[str, TTSDriver] = {}
        self._get_settings = get_settings
        self._set_settings = set_settings

    def register(self, driver: TTSDriver) -> None:
        """Register a driver under ``driver.id``. Later registrations replace
        earlier ones with the same id."""
        self._drivers[driver.id] = driver

    def list_drivers(self) -> list[TTSDriver]:
        return list(self._drivers.values())

    def get_driver(self, driver_id: str) -> TTSDriver | None:
        return self._drivers.get(driver_id)

    def get_current_driver(self) -> TTSDriver | None:
        stored = DEFAULT_DRIVER_ID
        if self._get_settings is not None:
            stored = self._get_settings(_SETTINGS_KEY, DEFAULT_DRIVER_ID) or DEFAULT_DRIVER_ID
        if stored in self._drivers:
            return self._drivers[stored]
        if DEFAULT_DRIVER_ID in self._drivers:
            return self._drivers[DEFAULT_DRIVER_ID]
        return next(iter(self._drivers.values()), None)

    def set_current_driver(self, driver_id: str) -> bool:
        """Switch the current driver and persist it to settings.

        Returns:
            True if the driver exists and the switch was persisted.
        """
        if driver_id not in self._drivers:
            return False
        if self._set_settings is not None:
            self._set_settings(_SETTINGS_KEY, driver_id)
        return True
