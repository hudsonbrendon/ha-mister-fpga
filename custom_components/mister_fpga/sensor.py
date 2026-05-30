"""Sensors for the MiSTer FPGA integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import MisterStatus
from .const import DOMAIN
from .entity import MisterEntity


@dataclass(frozen=True, kw_only=True)
class MisterSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[MisterStatus], str | None]


SENSORS: tuple[MisterSensorEntityDescription, ...] = (
    MisterSensorEntityDescription(
        key="core", translation_key="core", icon="mdi:chip",
        value_fn=lambda s: s.core,
    ),
    MisterSensorEntityDescription(
        key="system", translation_key="system", icon="mdi:gamepad-variant",
        value_fn=lambda s: s.system_name or s.system,
    ),
    MisterSensorEntityDescription(
        key="game", translation_key="game", icon="mdi:disc",
        value_fn=lambda s: s.game_name,
    ),
    MisterSensorEntityDescription(
        key="version", translation_key="version", icon="mdi:information-outline",
        value_fn=lambda s: s.version,
    ),
    MisterSensorEntityDescription(
        key="hostname", translation_key="hostname", icon="mdi:server-network",
        value_fn=lambda s: s.hostname,
    ),
    MisterSensorEntityDescription(
        key="ip_address", translation_key="ip_address", icon="mdi:ip-network",
        value_fn=lambda s: s.ip,
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
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
