"""Binary sensor for the MiSTer FPGA integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from mister_fpga import RA_SUPPORTED_SYSTEMS

from . import MisterConfigEntry
from .entity import MisterEntity

PARALLEL_UPDATES = 0

_RA_SUPPORTED_UPPER = {s.upper() for s in RA_SUPPORTED_SYSTEMS}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MisterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities = [
        MisterConnectivitySensor(coordinator, entry),
        MisterGameRunningSensor(coordinator, entry),
        MisterBgmActiveSensor(coordinator, entry),
        MisterIndexingSensor(coordinator, entry),
    ]
    if coordinator.ssh is not None:
        entities.append(MisterMainUnresponsiveSensor(coordinator, entry))
        entities.append(MisterSamActiveSensor(coordinator, entry))
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

    @property
    def extra_state_attributes(self) -> dict | None:
        idx = self.coordinator.index_status
        if idx is None:
            return None
        return {
            "total_steps": idx.total_steps,
            "current_step": idx.current_step,
            "description": idx.description,
        }


class MisterMainUnresponsiveSensor(MisterEntity, BinarySensorEntity):
    """On when Main_MiSTer stopped reading its command FIFO (SSH)."""

    _attr_translation_key = "main_unresponsive"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_main_unresponsive"

    @property
    def is_on(self) -> bool:
        return self.coordinator.main_unresponsive

    @property
    def extra_state_attributes(self) -> dict:
        return {"cmd_fifo_pending": self.coordinator.ssh_data.get("cmd_fifo_pending")}


class MisterSamActiveSensor(MisterEntity, BinarySensorEntity):
    """On while MiSTer Super Attract Mode is cycling games (SSH)."""

    _attr_translation_key = "sam_active"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:television-play"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_sam_active"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.ssh_data.get("sam_active"))


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
        if not (data and data.is_running_game and data.core):
            return False
        return data.core.upper() in _RA_SUPPORTED_UPPER
