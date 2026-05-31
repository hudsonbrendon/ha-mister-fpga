"""Binary sensor for the MiSTer FPGA integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MisterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            MisterConnectivitySensor(coordinator, entry),
            MisterGameRunningSensor(coordinator, entry),
            MisterBgmActiveSensor(coordinator, entry),
            MisterIndexingSensor(coordinator, entry),
        ]
    )


class MisterConnectivitySensor(MisterEntity, BinarySensorEntity):
    """Reports whether the MiSTer is reachable."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "online"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_online"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data and self.coordinator.data.online)


class MisterGameRunningSensor(MisterEntity, BinarySensorEntity):
    _attr_translation_key = "game_running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_game_running"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data and self.coordinator.data.is_running_game)


class MisterBgmActiveSensor(MisterEntity, BinarySensorEntity):
    _attr_translation_key = "background_music_active"
    _attr_icon = "mdi:music-circle"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_background_music_active"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.music.get("running"))


class MisterIndexingSensor(MisterEntity, BinarySensorEntity):
    _attr_translation_key = "indexing"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:database-search"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_indexing"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.indexing)
