"""Binary sensor for the MiSTer FPGA integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from mister_fpga import RA_SUPPORTED_SYSTEMS

from .const import DOMAIN
from .entity import MisterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        MisterConnectivitySensor(coordinator, entry),
        MisterGameRunningSensor(coordinator, entry),
        MisterBgmActiveSensor(coordinator, entry),
        MisterIndexingSensor(coordinator, entry),
    ]
    ra_data = getattr(coordinator, "ra_data", None)
    if ra_data is not None and ra_data.installed:
        entities.append(MisterRAGameSupportedSensor(coordinator, entry))
    async_add_entities(entities)


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


class MisterRAGameSupportedSensor(MisterEntity, BinarySensorEntity):
    """On when the running game is on a RetroAchievements-supported core."""

    _attr_translation_key = "ra_game_supported"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:trophy-check"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_ra_game_supported"

    @property
    def available(self) -> bool:
        ra_data = getattr(self.coordinator, "ra_data", None)
        return bool(ra_data is not None and ra_data.installed)

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data
        if not (data and data.is_running_game):
            return False
        return data.core in RA_SUPPORTED_SYSTEMS
