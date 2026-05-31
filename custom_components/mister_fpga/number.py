"""Number entities for INI-backed MiSTer video settings."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, INI_VIDEO_KEYS
from .entity import MisterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MisterIniNumber(coordinator, entry, key) for key in INI_VIDEO_KEYS
    )


class MisterIniNumber(MisterEntity, NumberEntity):
    """A 0-100 MiSTer.ini value (e.g. video_brightness)."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator, entry, ini_key: str) -> None:
        super().__init__(coordinator, entry)
        self._ini_key = ini_key
        self._attr_translation_key = ini_key
        self._attr_unique_id = f"{entry.entry_id}_{ini_key}"

    @property
    def native_value(self) -> float | None:
        raw = self.coordinator.ini_values.get(self._ini_key)
        try:
            return float(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.async_set_ini_values(
            self.coordinator.active_ini_id, {self._ini_key: str(int(value))}
        )
        self.coordinator.ini_values[self._ini_key] = str(int(value))
        self.async_write_ha_state()
