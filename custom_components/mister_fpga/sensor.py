"""Sensors for the MiSTer FPGA integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import MisterStatus
from .const import DOMAIN
from .coordinator import MisterDataUpdateCoordinator
from .entity import MisterEntity


@dataclass(frozen=True, kw_only=True)
class MisterSensorEntityDescription(SensorEntityDescription):
    value_fn: (
        Callable[[MisterStatus], str | int | float | None] | None
    ) = None
    coordinator_fn: (
        Callable[[MisterDataUpdateCoordinator], str | int | float | None] | None
    ) = None


def _disk_usage(status: MisterStatus) -> float | None:
    if not status.disk_total:
        return None
    return round(status.disk_used / status.disk_total * 100, 1)


def _disk_free_gib(status: MisterStatus) -> float | None:
    return round(status.disk_free / (1024 ** 3), 1) if status.disk_free else None


SENSORS: tuple[MisterSensorEntityDescription, ...] = (
    MisterSensorEntityDescription(
        key="core",
        translation_key="core",
        icon="mdi:chip",
        value_fn=lambda s: s.core,
    ),
    MisterSensorEntityDescription(
        key="system",
        translation_key="system",
        icon="mdi:gamepad-variant",
        value_fn=lambda s: s.system_name or s.system,
    ),
    MisterSensorEntityDescription(
        key="game",
        translation_key="game",
        icon="mdi:disc",
        value_fn=lambda s: s.game_name,
    ),
    MisterSensorEntityDescription(
        key="remote_version",
        translation_key="remote_version",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.version,
    ),
    MisterSensorEntityDescription(
        key="hostname",
        translation_key="hostname",
        icon="mdi:server-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.hostname,
    ),
    MisterSensorEntityDescription(
        key="ip_address",
        translation_key="ip_address",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.ip,
    ),
    MisterSensorEntityDescription(
        key="dns_name",
        translation_key="dns_name",
        icon="mdi:dns",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.dns,
    ),
    MisterSensorEntityDescription(
        key="disk_free",
        translation_key="disk_free",
        icon="mdi:micro-sd",
        native_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_disk_free_gib,
    ),
    MisterSensorEntityDescription(
        key="disk_usage",
        translation_key="disk_usage",
        icon="mdi:harddisk",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_disk_usage,
    ),
    MisterSensorEntityDescription(
        key="last_updated",
        translation_key="last_updated",
        icon="mdi:update",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.updated,
    ),
    MisterSensorEntityDescription(
        key="mac_address",
        translation_key="mac_address",
        icon="mdi:network-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        coordinator_fn=lambda c: c.mac_address,
    ),
    MisterSensorEntityDescription(
        key="music_track",
        translation_key="music_track",
        icon="mdi:music-note",
        coordinator_fn=lambda c: c.music.get("track") or None,
    ),
    MisterSensorEntityDescription(
        key="music_playlist",
        translation_key="music_playlist",
        icon="mdi:playlist-music",
        coordinator_fn=lambda c: c.music.get("playlist") or None,
    ),
    MisterSensorEntityDescription(
        key="peers",
        translation_key="peers",
        icon="mdi:lan",
        entity_category=EntityCategory.DIAGNOSTIC,
        coordinator_fn=lambda c: len(c.peers),
    ),
    MisterSensorEntityDescription(
        key="screenshots",
        translation_key="screenshots",
        icon="mdi:image-multiple",
        entity_category=EntityCategory.DIAGNOSTIC,
        coordinator_fn=lambda c: c.screenshots_count,
    ),
    MisterSensorEntityDescription(
        key="menu_position",
        translation_key="menu_position",
        icon="mdi:menu",
        coordinator_fn=lambda c: c.menu_path,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(MisterSensor(coordinator, entry, d) for d in SENSORS)


class MisterSensor(MisterEntity, SensorEntity):
    entity_description: MisterSensorEntityDescription

    def __init__(self, coordinator, entry, description) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self):
        desc = self.entity_description
        if desc.coordinator_fn is not None:
            return desc.coordinator_fn(self.coordinator)
        if self.coordinator.data is None:
            return None
        return desc.value_fn(self.coordinator.data)
